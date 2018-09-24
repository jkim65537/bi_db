from sqlalchemy import create_engine
from biz_intel_creds import CredsList
api_db_creds = CredsList().api_db
import pandas as pd

class PBAPIUsage():
    def __init__(self):
        self.engine = create_engine("postgresql+psycopg2://" +
                                    api_db_creds['login'] +
                                    ":" +
                                    api_db_creds['pw'] +
                                    "@" +
                                    api_db_creds['server'] +
                                    ":5432/" +
                                    api_db_creds['db'], client_encoding='utf8')

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
