from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL

class dbConnection(object):
    def __init__(self, connection_type, creds, port):
        # initialize the connection to the redshift db and create engine
        if connection_type == "postgresql+psycopg2://":
            self.engine = create_engine(connection_type \
                                        + creds['login'] \
                                        + ":" \
                                        + creds['pw'] \
                                        + "@" \
                                        + creds['server'] \
                                        + ":" \
                                        + port \
                                        + "/" \
                                        + creds['db'],
                                        isolation_level="AUTOCOMMIT",
                                        client_encoding='utf8')
            self.connection = self.engine.connect()
        elif connection_type in ["mysql+pymysql://", "mssql+pymssql://"]:
            self.engine = create_engine(connection_type \
                                        + creds['login'] \
                                        + ":" \
                                        + creds['pw'] \
                                        + "@" \
                                        + creds['server'] \
                                        + "/" \
                                        + creds['db'] \
                                        + "?charset=utf8")
        elif connection_type in ["snowflake"]:
            url = URL(account=creds["ACCOUNT"],
                    user=creds["USER"],
                    password=creds["PASSWORD"],
                    role="ACCOUNTADMIN")
            self.engine = create_engine(url)
            self.connection = self.engine.connect()
