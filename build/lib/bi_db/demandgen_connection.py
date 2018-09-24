import pandas as pd
from bi_db.db_connection import dbConnection
from biz_intel_creds import CredsList
demand_gen_creds = CredsList().demand_gen

class DemandGenConnection(dbConnection):
    def __init__(self):
        ctype = "mysql+pymysql://"
        port_num = "not needed"
        super(DemandGenConnection, self).__init__(connection_type=ctype,
                                                creds=demand_gen_creds,
                                                port=port_num)

    def sql_dataframe(self, query):
        df_result = pd.read_sql(query, self.engine)
        return df_result

    def create_table(self, insert_dataframe, table_name,
                    if_exists='replace', index=False):
        insert_dataframe.to_sql(table_name, self.engine,
                                if_exists=if_exists, index=index)
