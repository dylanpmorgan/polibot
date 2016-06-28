from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import psycopg2
import pandas as pd
import pdb

#sql_query = """
#SELECT * FROM birth_data_table WHERE delivery_method='Cesarean';
#"""

class ConnectToDB(object):
    def __init__(self):
        dbname = 'polibot_data'
        username = 'dpmorg_mac'
        pswd = 'OpaOpa'

        self.engine = create_engine('postgresql://%s:%s@localhost/%s'
                %(username,pswd,dbname))

        if not database_exists(self.engine.url):
            create_database(self.engine.url)

        self.con = None
        self.con = psycopg2.connect(database=dbname,
                                    user=username,
                                    host='localhost',
                                    password=pswd)

    def save_to_db(self, table_name, input_dict, replace=False):

        temp_df = pd.DataFrame.from_dict(input_dict)

        if table_name=="corpus_table":
            entry_id = "corpus_id"
        elif table_name=="response_table":
            entry_id = "response_id"
        elif table_name=="model_table":
            entry_id = "model_id"

        if replace:
            temp_df.to_sql(table_name, self.engine, if_exists='replace')
        else:
            temp_df.to_sql(table_name, self.engine, if_exists='append')

    def pull_from_db(self, sql_query):
        data_request = pd.read_sql_query(sql_query, self.con)
        return data_request

    def pull_candidate_corpus(self, table_name, candidate):

        sql_query = """
        SELECT speaker, speaker_text
        FROM %s
        WHERE speaker='%s'
        ORDER BY doc_date DESC, line_of_doc ASC;
        """ %(table_name, candidate)

        candidate_pd = self.pull_from_db(sql_query)
        #sent = [s for s in candidate_pd['speaker_text']]
        return candidate_pd #" ".join(sent)

    def check_entry_exists(self, table_name, entry_id, entry):

        cursor = self.con.cursor()
        data = cursor.execute("SELECT count(*) FROM %s WHERE %s=%s"
                %(table_name, entry_id, entry))
        data = cursor.fetchone()[0]
        if data==0:
            return False
        else:
            return True
