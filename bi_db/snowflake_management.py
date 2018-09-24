import sys
import pandas as pd
import snowflake.connector
from snowflake_connection import SnowflakeConnection
from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL

#from bi_tools import Logger
#logger = Logger("debug")

from biz_intel_creds import CredsList
snowflake_creds = CredsList().snowflake

class SnowflakeManagement(object):
    def __init__(self, username):
        self.username = username

    def create_user(self):
        pass

    def change_roles(self, desired_role):
        pass

    def change_table_name(self):

    def grant_permission(self):

    def update_snowflake_history(self):


    
