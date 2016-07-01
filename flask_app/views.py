from flask import render_template, request, jsonify, redirect
from flask_app import app
import pdb, time, json, datetime
import pandas as pd
import spacy
import random
from collections import OrderedDict

from connect_to_db import ConnectToDB
from polibot import PoliBot

st = time.time()
nlp = spacy.en.English(tagger=True, parser=False, entity=False, matcher=False)
global trump
trump = PoliBot("trump", nlp=nlp)
global clinton
clinton = PoliBot("clinton",nlp=nlp)
ed = time.time()
print("Load up time %s" %(ed-st))
global session_dict
session_dict = {}

class MaxDict(OrderedDict):
   """
   Ordered dictionary that holds a max number of elements.
   """
   def __init__(self, max_elements=100):
       super(MaxDict, self).__init__()
       self.max_elements = max_elements

   def __setitem__(self, key, value):
       if len(self) >= self.max_elements:
           super(MaxDict, self).popitem(last=False)
       super(MaxDict, self).__setitem__(key, value)

@app.route('/')
@app.route('/index')
def index():

    session_dict['session_id'] = ["_".join([str(random.getrandbits(12)),str(time.time())])]
    session_dict['question_num'] = [0]

    return render_template("index.html", title='Home')

@app.route('/input')
def input():
    return render_template("input.html")

@app.route('/slides')
def slides():
    return render_template("slides.html")

@app.route('/output', methods=['GET', 'POST'])
def output():

    question = request.args.get("question")

    question_error=""
    if question is None:
        question_error="Can you repeat the question?"
        return render_template("input2.html", error_msg=question_error,
                responses=responseSessionData)
    elif len(trump.TV.get_tokens(question))==0:
        question_error="You will have to be more specific with your question"
        return render_template("input2.html", error_msg=question_error,
                responses=responseSessionData)
    else:
        session_dict['question'] = [question]
        getData(question=question)

    return render_template("output2.html",
            question=session_dict['question'][0],
            trump_data=json.dumps([{
                    "text": session_dict['trump_text'][0],
                    "size": float(0.05+session_dict['trump_sim'][0])
                    }]),
            clinton_data=json.dumps([{
                    "text": session_dict['clinton_text'][0],
                    "size": float(0.05+session_dict['clinton_sim'][0])
                    }])
            )

@app.route('/results')
def results():

    # Want to pull all data from the response_table and count isbot, userguess
    # count(clinton_isbot)
    # count(clinton_userguess)
    # count(clinton_answer)
    allQuery = """
        SELECT
               count(clinton_isbot) as all_total,
               sum(clinton_isbot) as all_clinton_bot,
               sum(clinton_answer) as all_clinton_correct,
               sum(trump_isbot) as all_trump_bot,
               sum(trump_answer) as all_trump_correct,
               (SELECT count(clinton_isbot)
                FROM response_table
                WHERE session_id = '%s') as session_total,
               (SELECT sum(clinton_isbot)
                FROM response_table
                WHERE session_id = '%s') as session_clinton_bot,
               (SELECT sum(clinton_answer)
                FROM response_table
                WHERE session_id = '%s') as session_clinton_correct,
               (SELECT sum(trump_isbot)
                FROM response_table
                WHERE session_id = '%s') as session_trump_bot,
               (SELECT sum(trump_answer)
                FROM response_table
                WHERE session_id = '%s') as session_trump_correct
        FROM response_table;
    """ %(session_dict['session_id'][0],
          session_dict['session_id'][0],
          session_dict['session_id'][0],
          session_dict['session_id'][0],
          session_dict['session_id'][0])

    DB = ConnectToDB()
    qr = DB.pull_from_db(allQuery)

    all_results = [{
            "name": "Trump",
            "data": [int(qr['all_trump_correct']),
                     int(qr['session_trump_correct'])],
            "stack": "trump"
        }, {
            "name": "Trump Bot",
            "data": [int(qr['all_total'])-int(qr['all_trump_correct']),
                     int(qr['session_total'])-int(qr['session_trump_correct'])],
            "stack": "trump"
        }, {
            "name": "Clinton",
            "data": [int(qr['all_clinton_correct']),
                     int(qr['session_clinton_correct'])],
            "stack": "clinton"
        }, {
            "name": "Clinton Bot",
            "data": [int(qr['all_total'])-int(qr['all_clinton_correct']),
                     int(qr['session_total'])-int(qr['session_clinton_correct'])],
            "stack": "clinton"
        }]

    trump_score = "/".join([str(int(qr['session_trump_correct'])),
                            str(int(qr['session_total']))
                            ])
    clinton_score = "/".join([str(int(qr['session_clinton_correct'])),
                              str(int(qr['session_total']))
                              ])

    return render_template("results.html", results_data=json.dumps(all_results),
                           trump_score=trump_score,
                           clinton_score=clinton_score)

@app.route('/logData', methods=['GET', 'POST'])
def logData():
    error=""
    if request.method == 'POST':
        trumpResp = request.form.get('Trump_Answer')
        clintonResp = request.form.get('Clinton_Answer')

        if trumpResp is not None and clintonResp is not None:
            dt = datetime.datetime.now()

            # if user selected "bot"
            if trumpResp == "Tbot":
                session_dict['trump_userguess'] = ["bot"]
                # if response is "bot"
                if (session_dict['trump_isbot'][0]) == 1:
                    # answer = 1 (correct)
                    session_dict['trump_answer'] = [1]
                else:
                    # answer = 0 (wrong)
                    session_dict['trump_answer'] = [0]
            # else if user selected "not"
            else:
                session_dict['trump_userguess'] = ["not"]
                # if response is "bot"
                if (session_dict['trump_isbot'][0]) == 1:
                    #answer is wrong
                    session_dict['trump_answer'] = [0]
                else:
                    # else answer is right
                    session_dict['trump_answer'] = [1]

            if clintonResp == "Cbot":
                session_dict['clinton_userguess'] = ["bot"]
                if (session_dict['clinton_isbot'][0]) == 1:
                    session_dict['clinton_answer'] = [1]
                else:
                    session_dict['clinton_answer'] = [0]
            else:
                session_dict['clinton_userguess'] = ["not"]
                if (session_dict['clinton_isbot'][0]) == 1:
                    session_dict['clinton_answer'] = [0]
                else:
                    session_dict['clinton_answer'] = [1]

            session_dict['question_num'][0]+=1
            session_dict['date'] = [dt.year*10000 + 100*dt.month + dt.day]
            session_dict['time'] = [dt.hour*1e4+dt.minute*1e2+round(dt.microsecond/1e6, 3)]

            # Update markov chain
            '''
            if saved['trump_isbot'][0]==1:
                MarkovChain.update(saved['trump_response'])
            elif saved['clinton_isbot'][0]==1:
            '''

            DB = ConnectToDB()
            DB.save_to_db('response_table', session_dict)

            #responseSessionData.append(saved)
            session_data = getSessionData(session_dict['session_id'][0])

            # you can redirect to home page on successful commit. or anywhere else
            return render_template("input2.html", error_msg="",
                    responses=session_data)
        else:
            error=("Error, your log is incomplete! Please check and submit it again!")

def getData(question=None):

    st = time.time()
    num_sent = 1000
    n_return = 3

    #####################
    # Trump
    responses = trump.get_responses(num_sent=num_sent)
    response_text = [" ".join(response[0].split( )) for response in responses]
    best_bot = trump.response_tfidf_matches(response_text, question, n_return=n_return)
    best_text = trump.text_tfidf_matches(question, n_return=n_return)

    trump_best = [(1, bb[1], bb[2]) for bb in best_bot]+ \
                 [(0, bt[1], bt[2]) for bt in best_text]
    random.shuffle(trump_best)
    session_dict["trump_isbot"] = [trump_best[0][0]]
    session_dict["trump_text"] = [trump_best[0][1]]
    session_dict["trump_sim"] = [trump_best[0][2]]

    #####################
    # Clinton
    responses = clinton.get_responses(num_sent=num_sent)
    response_text = [" ".join(response[0].split( )) for response in responses]
    best_bot = clinton.response_tfidf_matches(response_text, question, n_return=n_return)
    best_text = clinton.text_tfidf_matches(question, n_return=n_return)

    clinton_best = [(1, bb[1], bb[2]) for bb in best_bot]+ \
                   [(0, bt[1], bt[2]) for bt in best_text]
    random.shuffle(clinton_best)
    session_dict["clinton_isbot"] = [clinton_best[0][0]]
    session_dict["clinton_text"] = [clinton_best[0][1]]
    session_dict["clinton_sim"] = [clinton_best[0][2]]

    ed = time.time()
    print("%s time to generate responses" %(ed-st))

def getSessionData(sessionID=None):

    # RESPONSE_TABE session_id, question_num, date, time, question,
    #               trump_text, trump_sim, trump_isbot, trump_userguess, trump_answer
    #               clinton_text, clinton_sim, clinton_isbot, clinton_userguess, clinton_answer

    sqlQuery = """
        SELECT session_id, question_num, question,
               trump_text, trump_userguess,
               clinton_text, clinton_userguess
        FROM response_table
        WHERE session_id = '%s'
        ORDER BY question_num ASC;
    """ %(sessionID)

    DB = ConnectToDB()
    queryresults = DB.pull_from_db(sqlQuery)

    return pd.DataFrame.to_dict(queryresults, 'records')
