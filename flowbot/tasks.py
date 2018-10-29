from __future__ import print_function
import luigi
import pandas as pd
from sqlalchemy import create_engine
from data import run_flowbot

class TestConnection(luigi.Task):
    def requires(self):
        return []
    def output(self):
        return luigi.LocalTarget('/home/ec2-user/luigi/flowbot/runtime-data/TestConnection{}.txt'.format(get_date_string()))
    def run(self):

        conn_string = 'mysql+mysqlconnector://cbones:ilovebrian@foxton.cesioqvecevx.us-east-2.rds.amazonaws.com:3306/coloradopackrafter'

        print(conn_string)
        print('creating engine: ')
        engine = create_engine(conn_string)

        print('running sql')

        df2 = pd.read_sql('SELECT * FROM coloradopackrafter.flowbot_requests limit 10;', engine)
        print(df2)
        assert len(df2) > 0

        with self.output().open('w') as out_file:
            print(df2, file=out_file)

        return df2

class Flowbot(luigi.Task):
    def requires(self):
        return [TestConnection()]
    def output(self):
        return luigi.LocalTarget('/home/ec2-user/luigi/flowbot/runtime-data/Flowbot{}.txt'.format(get_date_string()))
    def run(self):
        try:
            res = run_flowbot()
            with self.output().open('w') as out_file:
                print(res, file=out_file)

        except Exception as e:    
            raise e
        return res
####  helper functions ###

def get_date_string():
    return pd.Timestamp.now().isoformat().split(':')[0]

if __name__ == '__main__':
    print(get_date_string())
