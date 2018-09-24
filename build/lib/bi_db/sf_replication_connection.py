from sqlalchemy import create_engine
from biz_intel_creds import CredsList
sf_rep_creds = CredsList().sf_replication
import pandas as pd

class SFReplicationConnection():
    def __init__(self):
        self.engine = create_engine("mssql+pymssql://" +
                                    sf_rep_creds['login'] +
                                    ":" +
                                    sf_rep_creds['pw'] +
                                    "@" + sf_rep_creds['server'] +
                                    "/" + sf_rep_creds['db'] +
                                    "?charset=utf8")

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
