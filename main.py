from polibot import PoliBot
import pdb, time
import spacy

def main():

    st = time.time()
    nlp = nlp = spacy.en.English(tagger=True, parser=True,
            entity=False, matcher=False)
    ed = time.time()
    print("Time to load spacy.nlp: %s seconds" %(ed-st))

    st = time.time()
    trump = PoliBot("trump", nlp=nlp)
    ed = time.time()
    print("Time to load trump: %s seconds" %(ed-st))

    st = time.time()
    clinton = PoliBot("clinton", nlp=nlp)
    ed = time.time()
    print("Time to load clinton: %s seconds" %(ed-st))

    num_sent = 5000
    n_return = 5
    question = "What are your thoughts on abortion?"
    responses = trump.get_responses(num_sent=num_sent)
    response_text = [" ".join(response[0].split( )) for response in responses]
    best_bot = trump.response_tfidf_matches(response_text, question, n_return=n_return)
    best_lsi = trump.response_lsi_matches(response_text, question, n_return=n_return)
    tfidf_text = trump.text_tfidf_matches(question, n_return=n_return)
    lsi_text = trump.text_lsi_matches(question, n_return=n_return)

    pdb.set_trace()

if __name__ == 'main':
    main()
