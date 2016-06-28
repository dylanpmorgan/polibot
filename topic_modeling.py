import os, os.path, pdb, time
from collections import defaultdict
import numpy as np
from gensim import models, corpora, similarities, matutils

from connect_to_db import ConnectToDB
from token_vectorizer import TokenVectorizer
#from polibot2 import PoliBot

class TopicModeling(object):
    def __init__(self, TV=None):
        self.path = "/".join([os.getcwd(),"dependencies/"])

        if TV is None:
            self.TV = TokenVectorizer()
        else:
            self.TV = TV

        # Check to see if dictioanry exists
        if os.path.isfile(self.path+'topic_dict'):
            self.topic_dict = corpora.Dictionary.load(self.path+'topic_dict')
        else:
            self.topic_dict = self.get_topic_dict()

        if os.path.isfile(self.path+'tfidf_model'):
            self.tfidf = models.TfidfModel.load(self.path+'tfidf_model')
        else:
            self.tfidf = self.train_tfidf()

        #if os.path.isfile(self.path+'lda_model'):
        #    self.lda = models.ldamodel.LdaModel.load(self.path+'lda_model')
        #else:
        #    self.lda = self.train_lda_model()

        if os.path.isfile(self.path+'lsi_model'):
            self.lsi = models.LsiModel.load(self.path+'lsi_model')
        else:
            self.lsi = self.train_lsi_model()

    def prepare_candidate_corpus(self, input_text, candidate):
        fname = "".join([self.path,candidate])

        texts = [[str(word).lower() for word in self.TV.get_tokens(doc)]
                 for doc in input_text]

        corpus = [self.topic_dict.doc2bow(text) for text in texts]
        corpora.MmCorpus.serialize("".join([fname,"_corpus.mm"]), corpus)
        corpora.MmCorpus.serialize("".join([fname,"_tfidf_corpus.mm"]),self.tfidf[corpus])
        corpora.MmCorpus.serialize("".join([fname,"_lsi_corpus.mm"]),self.lsi[self.tfidf[corpus]])

        mm_lsi = corpora.MmCorpus("".join([fname,"_lsi_corpus.mm"]))
        mm_tfidf = corpora.MmCorpus("".join([fname,"_tfidf_corpus.mm"]))

        tfidf_index = similarities.SparseMatrixSimilarity(mm_tfidf, num_features=mm_tfidf.num_terms)
        tfidf_index.save("".join([fname,"_tfidf_index.index"]))

        lsi_index = similarities.MatrixSimilarity(mm_lsi, num_features=mm_lsi.num_terms)
        lsi_index.save("".join([fname,"_lsi_index.index"]))

        #lda_index = similarities.MatrixSimilarity(self.lda[mm_tfidf])
        #lda_index.save("".join([fname,"_lda_index.index"]))

    def get_cosinesim(self, vec1, vec2):

        return matutils.cossim(vec1, vec2)

    def get_helldist(self, vec1, vec2, lda_topics):

        dense1 = matutils.sparse2full(vec1, lda_topics)
        dense2 = matutils.sparse2full(vec2, lda_topics)

        return np.sqrt(0.5 * ((np.sqrt(dense1) - np.sqrt(dense2))**2).sum())

    def get_doc2bow(self, string):

        new_vec = self.topic_dict.doc2bow(self.TV.get_tokens(string))

        return new_vec

    def get_sparse_index(self, corpus=None):

        if corpus is None:
            mm = corpora.MmCorpus(self.path+'corpus_tfidf.mm')
        else:
            mm = self.tfidf[corpus]

        index = similarities.SparseMatrixSimilarity(mm,
                num_features=mm.num_terms)

        return index

    def get_dense_index(self,corpus=None):

        if corpus is None:
            mm = corpora.MmCorpus(self.path+'corpus_lsi.mm')
        else:
            mm = corpus

        index = similarities.MatrixSimilarity(mm,
                num_features=mm.num_terms)

        return index

    def get_corpus_index(self, input_text, lsi=False):

        corpus = [self.get_doc2bow(text) for text in input_text]
        if lsi is False:
            index = similarities.MatrixSimilarity(self.tfidf[corpus])
        else:
            index = similarities.MatrixSimilarity(
                    self.lsi[self.tfidf[corpus]])
        #corpora.MmCorpus.serialize('/tmp/corpus.mm', self.tfidf[corpus])
        #mm = corpora.MmCorpus('/tmp/corpus.mm')

        return index

    def get_corpus_tfidf_index(self, input_text):

        corpus = [self.get_doc2bow(text) for text in input_text]
        index = similarities.MatrixSimilarity(self.tfidf[corpus])
        #corpora.MmCorpus.serialize('/tmp/corpus.mm', self.tfidf[corpus])
        #mm = corpora.MmCorpus('/tmp/corpus.mm')

        return index

    def get_main_corpus(self):
        DB = ConnectToDB()

        sql_query = """
        SELECT doc_id, doc_date, line_of_doc, speaker_text
        FROM corpus_table
        ORDER BY doc_date DESC, line_of_doc ASC;
        """

        # Get entire corpus from database
        corpus_df = DB.pull_from_db(sql_query)
        docs = [sent for sent in corpus_df['speaker_text']]

        texts = [[str(word).lower() for word in self.TV.get_tokens(doc)]
                 for doc in docs]

        frequency = defaultdict(int)
        for text in texts:
            for token in text:
                frequency[token] += 1

        texts = [[token for token in text if frequency[token] > 1]
                  for text in texts]

        return texts

    def get_topic_dict(self):

        texts = self.get_main_corpus()

        dictionary = corpora.Dictionary(texts)
        dictionary.save(self.path+'topic_dict')

        corpus = [dictionary.doc2bow(text) for text in texts]
        corpora.MmCorpus.serialize(self.path+'corpus.mm', corpus)

        return dictionary

    def train_tfidf(self):

        corpus = corpora.MmCorpus(self.path+'corpus.mm')

        tfidf = models.TfidfModel(corpus, id2word=self.topic_dict)
        tfidf.save(self.path+'tfidf_model')

        corpora.MmCorpus.serialize(self.path+'corpus_tfidf.mm', tfidf[corpus])

        return tfidf

    def train_lda_model(self):

        mm = corpora.MmCorpus(self.path+'corpus.mm')
        lda = models.ldamodel.LdaModel(corpus=self.tfidf[mm], id2word=self.topic_dict,
                       num_topics=10, update_every=1, chunksize=512, passes=10)

        lda.save(self.path+'lda_model')

        return lda

    def train_lsi_model(self):

        corpus = corpora.MmCorpus(self.path+'corpus.mm')

        lsi = models.LsiModel(self.tfidf[corpus], id2word=self.topic_dict,
                num_topics=200)

        lsi.save(self.path+'lsi_model')
        corpora.MmCorpus.serialize(self.path+'corpus_lsi.mm', lsi[self.tfidf[corpus]])

        return lsi
