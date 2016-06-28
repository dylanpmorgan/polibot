import urllib
from bs4 import BeautifulSoup as BS
import re
import pandas as pd
import pdb
from token_vectorizer import TokenVectorizer
from connect_to_db import ConnectToDB
import time

"""
Usage notes:
    1. fetch the htmltext from the given link
    2. clean the html text of html code
    3. split the document into speaker and speaker_text
    3a. for press releases, this will be only one speaker usually
    4. put the data in a pandas dataframe to then be stored in the sql database
    4a. corpus_ID -- debate_date_line-of-document
        link - link to documennt
        type - debate, speech, interview
        date - time of occurence
        speaker - speaker name
        speaker_text - speaker text
        line_of_document -
    4b. for each line of speaker_text:
        unique_token_id = token_date
        token = the token
        unique_text_ID = question_ID, response_ID, or corpus_ID where token was mentioned
"""

class BuildSaveCorpus(object):
    def __init__(self):
        # Get the html links
        self.html_links = self.get_html_links()
        # Tokenizer!
        self.TV = TokenVectorizer()
        #
        self.DB = ConnectToDB()
        self.table_name = 'corpus_table'

    def build_corpus(self):

        for key, vals in self.html_links.items():

            if 'speech' in key:
                key_speaker = key.split('_')[1]
                doc_type = key.split('_')[0]
            else:
                doc_type = key

            for html_link in vals:
                line_of_doc_cter = 0

                html_text = self.fetch_data(html_link)
                speakers, speakers_text = self.clean_html(html_text)

                if len(speakers)==0:
                    speakers = [str(key_speaker)]*len(speakers_text)

                for speaker, speaker_text in zip(speakers, speakers_text):
                    sentences = self.TV.tokenize_tosentence(speaker_text)

                    for s in sentences:
                        corpus_ID = "_".join([str(doc_type),
                                             str(self.doc_date),
                                             str(line_of_doc_cter)])

                        html_link_dict = {
                                "corpus_id": [corpus_ID],
                                "link": [html_link],
                                "doc_id": ["_".join([key,str(self.doc_date)])],
                                "doc_type": [doc_type],
                                "doc_date": [int(self.doc_date)],
                                "speaker": [speaker.lower()],
                                "speaker_text": [s],
                                "line_of_doc": [line_of_doc_cter]
                        }

                        self.save_corpus(html_link_dict)
                        print(line_of_doc_cter, s)

                        line_of_doc_cter+=1

            print("Done with %s - %s" %(key, html_link))

    def save_corpus(self, out_dict):
        '''
        Save dictionary to SQL database
        '''
        self.DB.save_to_db(self.table_name, out_dict)

    def fetch_data(self, htmlfile):
        '''Grabs and opens the html file given the url address'''
        url = htmlfile
        if url==None:
            print("No URL Provided")
        else:
            response = urllib.request.urlopen(url)

        return response.read()

    def clean_html(self, htmltext):
        '''Uses beautifulsoup to parse the html file and clean it a bit

           Returns two different arrays:
                speaker -- who was talking
                speaker_text -- that the speaker said.

           Useful, specificially for debates. Clean_text will provide, in
           chronological order, the speaker:what they said.
        '''
        soupy = BS(htmltext, 'lxml')

        # Get the document date. Save "March 16, 2015" as "20150316"
        date = str(soupy.find_all('span',class_='docdate'))
        date_str = " ".join(re.split(' |, ',re.sub(r"<.+?>|","", date)[1:-1]))
        stime = time.strptime(date_str,"%B %d %Y")
        self.doc_date = str((stime[0]*10000)+(stime[1]*100)+(stime[2]))

        text_only = str(soupy.find_all('span',class_='displaytext'))
        speaker = []
        speaker_text = []
        for each in text_only[1:-1].split('<p>'):
            clean_each = re.sub(r"<.+?>|\[.+?\]","", each)

            clean_each_split = clean_each.split(':')
            #print(clean_each_split)
            if len(clean_each_split) > 1:
                speaker.append(clean_each_split[0])
                try:
                    speaker_text.append(clean_each_split[1])
                except (AttributeError, TypeError):
                    pdb.set_trace()
            else:
                try:
                    speaker_text[-1] = speaker_text[-1]+' '+clean_each_split[0]
                except:
                    speaker_text.append(clean_each_split[0])

        return speaker, speaker_text

    def get_html_links(self):

        link_dict = {}

        link_dict['democratic_debate'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116995', #Brooklyn, New York; April 14, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112719', #Miami, Florida; March 9, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112718', #Flint, Michigan; March 6, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111520', #Milwaukee, Wisconsin; February 11, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111471', #Durham, New Hampshire; February 4, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111409', #Charleston, South Carolina; January 17, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111178', #Manchester, New Hampshire; December 19, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110910', #Des Moines, Iowa; November 14, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110903', #Las Vegas, Nevada; October 13, 2015
        ]

        link_dict['republican_debate'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=115148', #Miami, Florida; March 10, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111711', #Detroit, Michigan; March 3, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111634', #Houston, Texas; February 25, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111500', #Greenville, South Carolina; February 13, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111472', #Manchester, New Hampshire; February 6, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111412', #Des Moines, Iowa; January 28, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111395', #North Charleston, South Carolina; January 14, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111177', #Las Vegas, Nevada; December 15, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110908', #Milwaukee, Wisconsin; November 10, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110906', #Boulder, Colorado; October 28, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110756', #Simi Valley, California; September 16, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110489', #Cleveland, Ohio; August 6, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111413', #Des Moines, Iowa; January 28, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111394', #North Charleston, South Carolina; January 14, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111176', #Las Vegas, Nevada; December 15, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110909', #Milwaukee, Wisconsin: November 10, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110907', #Boulder, Colorado; October 28, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110758', #Simi Valley, California; September 16, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110757'  #Cleveland, Ohio; August 6, 2015
        ]

        link_dict['speech_trump'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110306',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116597'

        ]

        link_dict['speech_kaisch'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116599',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=113069',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116546']

        link_dict['speech_cruz'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117232',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116598',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114768',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110030',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=109774']

        link_dict['speech_malley'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112703',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112702',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112696',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112699',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112704',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112700',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=112716'
        ]

        link_dict['speech_clinton'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116600',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111596',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111586', #Rachel Maddow of MSNBC; February 8, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111589', #Jake Tapper of CNN's "State of the Union"; February 7, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111587',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111585',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111591',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111595',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111592',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111439',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111593',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111594',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111414',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111436',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111435',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111434',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111433',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111432',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111431',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111430',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111429',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111428',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111416',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111426',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111426',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111425',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111424',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111423',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111422',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111417',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111418',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111421',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111419',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111419',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110267',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110269',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110268',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110270',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110271',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111420'
        ]

        link_dict['speech_sanders'] = [
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117513', #Steve Inskeep of National Public Radio; May 5, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117194', #Conference Hosted by the Pontifical Academy of Social Sciences in Vatican City; April 15, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=116694', #Remarks on Policy in the Middle East in Salt Lake City, Utah; March 21, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117516', #Remarks in Essex Junction, Vermont Following the "Super Tuesday" Primaries, March 1, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117511', #Remarks in Concord Following the New Hampshire Primary; February 9, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=111440', #Remarks in Des Moines Following the Iowa Caucus; February 1, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117514', #Remarks in a Meeting with Steelworkers in Des Moines, Iowa; January 26, 2016
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114487', #Remarks at the New Hampshire Democratic Party Jefferson-Jackson Dinner in Manchester; November 29, 2015
            'http://www.presidency.ucsb.edu/ws/index.php?pid=117517',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114493',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114491',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114486',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114488',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114494',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114489',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114490',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114495',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=114492',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110222',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110221',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110125',
            'http://www.presidency.ucsb.edu/ws/index.php?pid=110124'
        ]

        return link_dict

    #DEFUNCT
    def combine_speakers(self):
        speakers = self.speakers
        text = self.speakers_text
        uniq_speakers = list(set(speakers))

        speaker_dict = {}

        speakerarr = np.array(speakers)
        textarr = np.array(text)
        for us in uniq_speakers:
            match = np.where(speakerarr == us)[0]
            matched_text = textarr[match]

            giant_text_str = ''
            for mt in matched_text:
                re_mt = re.sub(r'\[.+?\]','', mt.tolist())
                giant_text_str+=re_mt

            speaker_dict[us] = giant_text_str

        self.speaker_dict = speaker_dict
