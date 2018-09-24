from sqlalchemy import create_engine
from biz_intel_creds import CredsList
pb_log_copy_creds = CredsList().pb_log_copy
import pandas as pd

class PBLogCopyConnection():
    def __init__(self):
        self.engine = create_engine("mssql+pymssql://" +
                                    pb_log_copy_creds['login'] +
                                    ":" +
                                    pb_log_copy_creds['pw'] +
                                    "@" +
                                    pb_log_copy_creds['server'] +
                                    "/" +
                                    pb_log_copy_creds['db'] +
                                    "?charset=utf8")

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
