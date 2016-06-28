import re
import spacy

class TokenVectorizer(object):
    def __init__(self, nlp=None):

        if nlp is None:
            self.nlp = spacy.en.English(tagger=True, parser=True,
                    entity=False, matcher=False)
        else:
            self.nlp = nlp

    def get_tokens(self, sentence):
        '''
        Check that input text has at least one token
        Make sure that it has at least one non
        '''
        tokens = self.nlp(sentence, parse=True)
        try:
            tokens = [t.lemma_ for t in tokens if (t.is_alpha==True and t.is_stop==False)]
        except:
            tokens = []

        try:
            token_list = [str(t) for t in tokens]
        except:
            token_list = []

        if len(token_list) > 0:
            return token_list
        else:
            return []

    def tokenize_tosentence(self, text):
        ''' Seperates text into the individual words and stems.'''
        tokens = self.nlp(text, parse=True)

        '''
        sentences = []
        for s in tokens.sents:
            print(''.join(tok.string for tok in tokens))
        '''
        sentences = []
        for sent in tokens.sents:
            try:
                sentences.append(str(sent))
            except:
                continue

        return sentences

    def tokenize_full(self,sentence):
        # Split into word tokens
        try:
            tokens = self.tokenize_towords(sentence)
        except:
            return None

        # Remove stop words
        try:
            tokens_nostops = self.remove_stops(tokens)
        except:
            return None

        return tokens_nostops

    def tokenize_towords(self, text):
        ''' Seperates text into the individual words and stems.'''
        #clean_text = re.sub("[^a-zA-Z]"," ", text)
        #words = clean_text.lower().split()
        tokens = self.nlp(text, parse=True)

        return [t for t in tokens if t.is_alpha==True]

    def remove_stops(self, tokens):
        ''' Remove stop words from the list; i.e. words that don't
            matter (is, the, you, etc.)
        '''

        return [t for t in tokens if t.is_stop==False]

    def make_vector(self, tokens):
        ''' @pre: unique(vectorIndex) '''
        vector = []

        for tok in tokens:
            try:
                vector.append(self.model[tok.lower()])
            except:
                continue

        return vector
