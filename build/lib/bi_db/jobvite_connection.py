from bi_db.db_connection import dbConnection
from bi_db.redshift_connection import RedshiftConnection
from biz_intel_creds import CredsList
jobvite_creds = CredsList().jobvite
import pandas as pd

class JobviteConnection(RedshiftConnection, dbConnection):
    def __init__(self):
        ctype = "postgresql+psycopg2://"
        port_num = "5439"
        super(RedshiftConnection, self).__init__(connection_type=ctype,
                                                creds=jobvite_creds,
                                                port=port_num)
    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result
