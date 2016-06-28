from markovify import Chain, combine
import pdb
from os import path
import pickle
import string
import datetime

class MarkovChain(object):
    def __init__(self, state_size=3, pos_bind_char='::'):
        self.state_size = state_size
        self.pos_bind_char = pos_bind_char

    def train_model(self, corpus):
        self.model = Chain(corpus, self.state_size)

        return self

    def update(self, corpus, contribution=1):
        new_model = Text(corpus, self.state_size)
        self.model = combine([self.model, new_model], [1, contribution])

        # Get the filename for the model to be saved.
        # A new model file is made every week, this allows for some ability
        # to refer back to old models if things get weird.
        dt = datetime.datetime.now()
        wk_of_yr = datetime.date(dt.year, dt.month, dt.day).isocalendar()[1]
        timestamp = dt.year*100+wk_of_yr
        fname = "".join([PoliBot.path,
                         PolitBot.candidate,
                         "_markov_models/",
                         str(timestamp),
                         "_markov_model.pkl"])

        with open(fname, "wb") as f:
            pickle.dump(self.model, f)

        return self

    def make_response(self, init_state=None, n_sentences=100):

        sentences = []
        while (len(sentences) < n_sentences):
            sentence_i = self.model.walk(init_state=init_state)
            if sentence_i is None:
                continue
            else:
                sentence_i = self._prune_pos_tags(sentence_i, self.pos_bind_char)
                sentences.append(sentence_i)

        return sentences

    def _prune_pos_tags(self, sentence, pos_bind_char):
        untagged_sentence = list()
        for i, token in enumerate(sentence):
            if self.pos_bind_char in token:
                token = token.split(self.pos_bind_char)[0]
            if i == 0 or token in string.punctuation:
                untagged_sentence.append(token)
            else:
                token = ' ' + token
                untagged_sentence.append(token)

        return ''.join(untagged_sentence)
