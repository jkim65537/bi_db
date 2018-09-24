from sqlalchemy import create_engine
from biz_intel_creds import CredsList
rts_creds = CredsList().rts
import pandas as pd

class RTSConnection():
    def __init__(self):
        self.engine = create_engine("mssql+pymssql://" +
                                    rts_creds['login'] +
                                    ":" +
                                    rts_creds['pw'] +
                                    "@" +
                                    rts_creds['server'] +
                                    "/" +
                                    rts_creds['db'] +
                                    "?charset=utf8")

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
