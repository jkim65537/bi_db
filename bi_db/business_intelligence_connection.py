from sqlalchemy import create_engine
from biz_intel_creds import CredsList
bi_db_creds = CredsList().businessintelligence
import pandas as pd

class BusinessIntelligenceConnection():
    def __init__(self):
        self.engine = create_engine("mysql+pymysql://" +
                                    bi_db_creds['login'] +
                                    ":" +
                                    bi_db_creds['pw'] +
                                    "@" +
                                    bi_db_creds['server'] +
                                    "/" +
                                    bi_db_creds['db'] +
                                    "?charset=utf8")
