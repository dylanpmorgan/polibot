from flask import render_template, request, jsonify, redirect
from flask_app import app
import pdb, time, json, datetime
import pandas as pd
import spacy
import random

from connect_to_db import ConnectToDB
from polibot import PoliBot

st = time.time()
nlp = spacy.en.English(tagger=True, parser=True, entity=False, matcher=False)
global trump
trump = PoliBot("trump", nlp=nlp)
global clinton
clinton = PoliBot("clinton",nlp=nlp)
ed = time.time()
print("Load up time %s" %(ed-st))

global clinton_data
clinton_data = []
global trump_data
trump_data = []
global responseSessionData
responseSessionData = []

@app.route('/')
@app.route('/index')
def index():
    clinton_data = []
    trump_data = []
    responseSessionData = []

    return render_template("index.html", title='Home')

@app.route('/input')
def input():
    return render_template("input.html")

@app.route('/output', methods=['GET', 'POST'])
def output():

    question = request.args.get("question")

    question_error=""
    if question is None:
        question_error="Can you repeat the question?"
    elif len(trump.TV.get_tokens(question))==0:
        question_error="You will have to be more specific with your question"
    else:
        data = getData(question=question)
        global trump_data
        trump_data = [d for d in data if d['speaker'] == 'Donald Trump']
        global clinton_data
        clinton_data = [d for d in data if d['speaker'] == 'Hilary Clinton']

    return render_template("output2.html",
            question=question,
            trump_data=json.dumps(trump_data),
            clinton_data=json.dumps(clinton_data))

@app.route('/results')
def results():

    sqlQuery = """
        SELECT clinton_isbot, trump_isbot
        FROM response_table;
    """

    DB = ConnectToDB()
    queryresults = DB.pull_from_db(sqlQuery)
    totCt = len(queryresults)

    # If _isbot = 0 or 2, the users got it right (they weren't fooled by the bot)
    # if _isbot = 1, they were fooled!
    trump_wrong = len([wrong for wrong in queryresults['trump_isbot'] if wrong==1])
    trump_right = totCt - trump_wrong
    clinton_wrong = len([wrong for wrong in queryresults['clinton_isbot'] if wrong==1])
    clinton_right = totCt - clinton_wrong

    questionTot = len(responseSessionData)
    trumpSess_wrong=0
    clintonSess_wrong=0
    for rsd in responseSessionData:
        if rsd['trump_isbot'] == 1:
            trumpSess_wrong+=1
        if rsd['clinton_isbot'] == 1:
            clintonSess_wrong+=1

    trumpSess_right = questionTot - trumpSess_wrong
    clintonSess_right = questionTot - clintonSess_wrong

    all_results = [{
            "name": "Trump",
            "data": [trump_right, trumpSess_right],
            "stack": "trump"
        }, {
            "name": "TrumpBot",
            "data": [trump_wrong, trumpSess_wrong],
            "stack": "trump"
        }, {
            "name": "Clinton",
            "data": [clinton_right, clintonSess_right],
            "stack": "clinton"
        }, {
            "name": "ClintonBot",
            "data": [clinton_wrong, clintonSess_wrong],
            "stack": "clinton"
        }]

    return render_template("results.html", results_data=json.dumps(all_results),
                           questionTot1=questionTot, questionTot2=questionTot,
                           trumpBotCt=trumpSess_wrong, trumpCt=trumpSess_right,
                           hilaryBotCt=clintonSess_wrong, hilaryCt=clintonSess_right)

@app.route('/logData', methods=['GET', 'POST'])
def logData():
    error=""
    if request.method == 'POST':
        trumpResp = request.form.get('Trump_Answer')
        clintonResp = request.form.get('Clinton_Answer')

        if trumpResp is not None and clintonResp is not None:
            dt = datetime.datetime.now()

            if "not" in trumpResp:
                trumpResp=0
            else:
                trumpResp=1

            if "not" in clintonResp:
                clintonResp=0
            else:
                clintonResp=1

            saved = {
                    'question_num':[len(responseSessionData)+1],
                    'uniq_id': [time.time()],
                    'date': [dt.year*10000 + 100*dt.month + dt.day],
                    'question': [trump_data[0]['question']],
                    'trump_response': [trump_data[0]['speaker_text']],
                    'trump_isbot': [trump_data[0]['is_bot']+int(trumpResp)],
                    'trump_sim': [trump_data[0]['sim']],
                    'clinton_response': [clinton_data[0]['speaker_text']],
                    'clinton_isbot': [clinton_data[0]['is_bot']+int(clintonResp)],
                    'clinton_sim': [clinton_data[0]['sim']]
            }
            '''
            for d in data:
                if trumpResp in d['id']:
                    saved['trump_response'].append(d['speaker_text'])
                    saved['trump_isbot'].append(d['is_bot'])
                    saved['trump_sim'].append(d['sim'])
                elif clintonResp in d['id']:
                    saved['clinton_response'].append(d['speaker_text'])
                    saved['clinton_isbot'].append(d['is_bot'])
                    saved['clinton_sim'].append(d['sim'])
                else:
                    continue
            '''
            # Update markov chain
            '''
            if saved['trump_isbot'][0]==1:
                MarkovChain.update(saved['trump_response'])
            elif saved['clinton_isbot'][0]==1:
            '''

            DB = ConnectToDB()
            DB.save_to_db('response_table', saved)

            responseSessionData.append(saved)

            # you can redirect to home page on successful commit. or anywhere else
            return render_template("input2.html", responses=responseSessionData)
        else:
            error=("Error, your log is incomplete! Please check and submit it again!")

def getData(question=None):

    output_dict = []

    st = time.time()
    num_sent = 1000
    n_return = 3
    responses = trump.get_responses(num_sent=num_sent)
    response_text = [" ".join(response[0].split( )) for response in responses]
    best_bot = trump.response_tfidf_matches(response_text, question, n_return=n_return)

    trump_dict = []

    tct=1
    for i in range(len(best_bot)):
        str_id = "".join(["T",str(tct)])
        trump_dict.append({
            'question': question,
            'id': str_id,
            'speaker': "Donald Trump",
            'speaker_id': 1,
            'speaker_text': best_bot[i][1],
            'sim': float(best_bot[i][2]),
            'size': float(2+(best_bot[i][2]*10)),
            'is_bot': 1
        })
        tct+=1

    best_text = trump.text_tfidf_matches(question, n_return=n_return)

    for i in range(len(best_text)):
        str_id = "".join(["T",str(tct)])
        trump_dict.append({
            'question': question,
            'id': str_id,
            'speaker': "Donald Trump",
            'speaker_id': 1,
            'speaker_text': best_text[i][1],
            'sim': float(best_text[i][2]),
            'size': float(best_text[i][2]*10),
            'is_bot': 0
        })
        tct+=1

    responses = clinton.get_responses(num_sent=num_sent)
    response_text = [" ".join(response[0].split( )) for response in responses]
    best_bot = clinton.response_tfidf_matches(response_text, question, n_return=n_return)

    clinton_dict = []

    cct=1
    for i in range(len(best_bot)):
        str_id = "".join(["C",str(cct)])
        clinton_dict.append({
            'question': question,
            'id': str_id,
            'speaker': "Hilary Clinton",
            'speaker_id': 2,
            'speaker_text': best_bot[i][1],
            'sim': float(best_bot[i][2]),
            'size': float(2+(best_bot[i][2]*10)),
            'is_bot': 1
        })
        cct+=1
    best_text = clinton.text_tfidf_matches(question, n_return=n_return)

    for i in range(len(best_text)):
        str_id = "".join(["C",str(cct)])
        clinton_dict.append({
            'question': question,
            'id': str_id,
            'speaker': "Hilary Clinton",
            'speaker_id': 1,
            'speaker_text': best_text[i][1],
            'sim': float(best_text[i][2]),
            'size': float(best_text[i][2]*10),
            'is_bot': 0
        })
        cct+=1

    random.shuffle(trump_dict)
    random.shuffle(clinton_dict)

    output_dict.append(trump_dict[0])
    output_dict.append(clinton_dict[0])

    ed = time.time()
    print("%s time to generate responses" %(ed-st))

    return output_dict
