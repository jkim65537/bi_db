from sqlalchemy import create_engine
from biz_intel_creds import CredsList
pb_admin_creds = CredsList().pb_admin
import pandas as pd

class PBAdminConnection():
    def __init__(self):
        self.engine = create_engine("mssql+pymssql://" +
                                    pb_admin_creds['login'] +
                                    ":" +
                                    pb_admin_creds['pw'] +
                                    "@" +
                                    pb_admin_creds['server'] +
                                    "/" +
                                    pb_admin_creds['db'] +
                                    "?charset=utf8")

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
