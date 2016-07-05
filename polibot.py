import numpy as np
import pdb, time, datetime
from collections import deque
import glob, os

from token_vectorizer import TokenVectorizer
from connect_to_db import ConnectToDB
from markov_chain import MarkovChain
from topic_modeling import TopicModeling
from gensim import similarities

import string
import spacy
import pickle

class PoliBot(object):
    def __init__(self, candidate, nlp=None):
        """ Prepare the bot for the input candidate."""
        #############################
        # Set some variables
        #############################
        # Path to files/dependencies
        self.path = "/".join([os.getcwd(),"dependencies/"])
        self.candidate = candidate.lower()

        #############################
        # Connect to the SQL database
        #############################
        self.DB = ConnectToDB()
        self.corpus_table = 'corpus_table'
        self.response_table = 'response_table'

        ############################
        # Initialize the vectorizer
        ###########################
        if nlp is None:
            self.nlp = spacy.en.English(tagger=True, parser=False,
                    entity=False, matcher=False)
        else:
            self.nlp = nlp

        self.TV = TokenVectorizer(nlp=self.nlp)

        ##################################
        # Set up TopicModeling
        ##################################
        self.TP = TopicModeling(TV=self.TV)

        # Check to see if the candidate specific files are there.
        if os.path.isfile("".join([self.path,candidate,"_lsi_index.index"])):
            corpus_df = self.DB.pull_candidate_corpus('corpus_table', self.candidate)
            self.corpus = corpus_df['speaker_text'].values.tolist()
            self.index = similarities.MatrixSimilarity.load(
                    "".join([self.path,self.candidate,'_tfidf_index.index']))
            self.lsi_index = similarities.MatrixSimilarity.load(
                    "".join([self.path,self.candidate,'_lsi_index.index']))
        else:
            corpus_df = self.DB.pull_candidate_corpus('corpus_table', self.candidate)
            self.corpus = corpus_df['speaker_text'].values.tolist()
            self.TP.prepare_candidate_corpus(self.corpus, self.candidate)
            self.index = similarities.MatrixSimilarity.load(
                    "".join([self.path,self.candidate,'_tfidf_index.index']))
            self.lsi_index = similarities.MatrixSimilarity.load(
                    "".join([self.path,self.candidate,'_lsi_index.index']))

        #############################
        # Initialize the markov chain
        #############################
        # Get the most recent markov chain.
        markov_models = glob.glob("".join([self.path,
                                           self.candidate,
                                           "_markov_models/*"]))
        if len(markov_models)==0:
            corpus = self.get_corpus()
            sorin = MarkovChain(state_size=3)
            sorin.train_model(corpus)

            dt = datetime.datetime.now()
            wk_of_yr = datetime.date(dt.year, dt.month, dt.day).isocalendar()[1]
            timestamp = dt.year*100+wk_of_yr
            fname = "".join([self.path,
                             self.candidate,
                             "_markov_models/",
                             str(timestamp),
                             "_markov_model.pkl"])

            with open(fname, "wb") as f:
                pickle.dump(sorin, f)

            self.markov_model = sorin

        else:
            markov_fname = markov_models[-1]
            pkl_file = open(markov_fname, 'rb')
            sorin = pickle.load(pkl_file)
            self.markov_model = sorin

        # Log dictionary for questions and responses
        self.idnum = 0

    def update_model(self, text, sim):

        new_sorin = self.markov_model.update(text, sim)

        dt = datetime.datetime.now()
        wk_of_yr = datetime.date(dt.year, dt.month, dt.day).isocalendar()[1]
        timestamp = dt.year*100+wk_of_yr
        fname = "".join([self.path, self.candidate, "_markov_models/",
                         str(timestamp),"_markov_model.pkl"])

        with open(fname, "wb") as f:
            pickle.dump(new_sorin, f)

        self.markov_model = new_sorin

        return self

    def question_getbest_responses(self, question, nsent=100):

            responses = self.get_responses(num_sent=nsent)
            response_text = [" ".join(response[0].split( )) for response in responses]
            best_responses = self.get_tfidf_matches(response_text, question)

            return best_responses

    def ask_question(self, question=None):

        token_list = self.TV.get_tokens(question)

        if token_list is None:
            return None
        else:
            return (question, token_list)

    def get_responses(self, num_sent=100, tries=1, save_to_db=False):

        responses = self.markov_model.make_response(n_sentences=num_sent)

        response_list = []
        for i, response in enumerate(responses):
            token_list = self.TV.get_tokens(response)
            response_list.append((response, token_list))

        return response_list

    def response_tfidf_matches(self, sentences, question, n_return=None):

        index = self.TP.get_corpus_index(sentences)
        sims = index[self.TP.tfidf[self.TP.get_doc2bow(question)]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])

        if n_return is None:
            return [(sims[i][0],sentences[sims[i][0]],sims[i][1]) for i in range(len(sentences))]
        else:
            return [(sims[i][0],sentences[sims[i][0]],sims[i][1]) for i in range(n_return)]

    def text_tfidf_matches(self, question, n_return=5):

        sims = self.index[self.TP.tfidf[self.TP.get_doc2bow(question)]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])

        if n_return is None:
            return [(sims[i][0],self.corpus[sims[i][0]],sims[i][1]) for i in range(len(sentences))]
        else:
            return [(sims[i][0],self.corpus[sims[i][0]],sims[i][1]) for i in range(n_return)]

    def response_lsi_matches(self, sentences, question, n_return=5):

        index = self.TP.get_corpus_index(sentences, lsi=True)
        sims = index[self.TP.lsi[self.TP.tfidf[self.TP.get_doc2bow(question)]]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])

        if n_return is None:
            return [(sims[i][0],sentences[sims[i][0]],sims[i][1]) for i in range(len(sentences))]
        else:
            return [(sims[i][0],sentences[sims[i][0]],sims[i][1]) for i in range(n_return)]

    def text_lsi_matches(self, question, n_return=5):

        sims = self.lsi_index[self.TP.lsi[self.TP.tfidf[self.TP.get_doc2bow(question)]]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])

        if n_return is None:
            return [(sims[i][0],self.corpus[sims[i][0]],sims[i][1]) for i in range(len(sentences))]
        else:
            return [(sims[i][0],self.corpus[sims[i][0]],sims[i][1]) for i in range(n_return)]

    def get_corpus(self):

        df = self.DB.pull_candidate_corpus(self.corpus_table, self.candidate)

        corpus = deque()
        for doc in self.nlp.pipe(df['speaker_text'], batch_size=50, n_threads=1):
            pos_tagged_sentence = list()
            for tok in doc:
                if tok.like_url or tok.like_email:
                    continue
                if tok.is_alpha:
                    pos_tagged_sentence.append('::'.join([tok.orth_, tok.pos_]))
                elif tok.is_punct and tok.text in [',', '.', '?', '!']:
                    pos_tagged_sentence.append(tok.text)
                elif "\'" in tok.text and tok.lemma_ not in string.punctuation:
                    pos_tagged_sentence.append(tok.lemma_)
            corpus.append(pos_tagged_sentence)

        return list(corpus)
