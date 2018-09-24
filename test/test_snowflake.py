import unittest
import pandas as pd
from bi_tools import flex_write
from bi_db import SnowflakeConnection

class TestSnowflakeConnection(unittest.TestCase):

    def test_write_to_sql(self):
        df1, df2 = self._create_test_df()
        conn = SnowflakeConnection()
        conn.write_to_sql(df1, schema_name="RTS_UPDATE", table_name="test")
        conn.query_executor("USE DATABASE BUSINESS_INTELLIGENCE")
        df = conn.sql_dataframe("SELECT * FROM RTS_UPDATE.TEST")
        conn.query_executor("DROP TABLE RTS_UPDATE.test")
        self.assertTrue(df.equals(df1))

    def test_sql_dataframe(self):
        conn = SnowflakeConnection()
        df = conn.sql_dataframe(
            "select * from BUSINESS_INTELLIGENCE.RTS_UPDATE.WORKFLOW limit 1;")
        self.assertFalse(df.empty)

    def test_create(self):
        conn = SnowflakeConnection()
        conn.create(object_name="TEST",
                        object_type="schema",
                        DATABASE="BUSINESS_INTELLIGENCE")
        df = conn.sql_dataframe("show schemas;")
        if "TEST" in df.name.unique():
            test_results = True
        else:
            test_results = False
        conn.query_executor("USE DATABASE BUSINESS_INTELLIGENCE")
        conn.query_executor("DROP SCHEMA TEST")
        self.assertTrue(test_results)

    def test_get_metadata(self):
        conn = SnowflakeConnection()
        ls = conn.get_metadata("BUSINESS_INTELLIGENCE", "RTS_UPDATE","WORKFLOW")
        self.assertFalse(ls!=[])

    def test_append(self):
        conn = SnowflakeConnection()
        answer = pd.DataFrame(columns={"NAME", "NUMBER"})
        answer.NAME = ["sam", "alex", "chad", "sam", "alex", "jun"]
        answer.NUMBER = [1,2,8,3,2,7]
        df1, df2 = self._create_test_df()
        # create the destination table
        savepath = "s3://pitchbook-snowflake/test_objects/df1.csv"
        conn.create(object_name="TEST",object_type="TABLE",
            DATABASE="BUSINESS_INTELLIGENCE",SCHEMA="RTS_UPDATE",df=df1)
        # create an s3 object to bulk append
        savepath = "s3://pitchbook-snowflake/test_objects/df2.csv"
        flex_write(df2, savepath, s3=True)
        conn.append(schema_name="RTS_UPDATE", table_name="TEST",
            filepath=savepath)
        conn.query_executor("USE DATABASE BUSINESS_INTELLIGENCE")
        df = conn.sql_dataframe("SELECT * FROM RTS_UPDATE.TEST")
        conn.query_executor("DROP TABLE RTS_UPDATE.TEST")
        self.assertTrue(df.equals(answer))

    def test_replace(self):
        conn = SnowflakeConnection()
        answer = pd.DataFrame(columns={"NAME", "NUMBER"})
        answer.NAME = ["sam", "alex", "jun"]
        answer.NUMBER = [3, 2, 7]
        df1, df2 = self._create_test_df()
        # create the destination table
        savepath = "s3://pitchbook-snowflake/test_objects/df1.csv"
        conn.create(object_name="TEST",object_type="TABLE",
            DATABASE="BUSINESS_INTELLIGENCE",SCHEMA="RTS_UPDATE",df=df1)
        # create an s3 object to bulk append
        savepath = "s3://pitchbook-snowflake/test_objects/df2.csv"
        flex_write(df2, savepath, s3=True)
        conn.replace(schema_name="RTS_UPDATE", table_name="TEST",
            filepath=savepath)
        conn.query_executor("USE DATABASE BUSINESS_INTELLIGENCE")
        df = conn.sql_dataframe("SELECT * FROM RTS_UPDATE.TEST")
        conn.query_executor("DROP TABLE RTS_UPDATE.TEST")
        self.assertTrue(df.equals(answer))

    def test_update(self):
        conn = SnowflakeConnection()
        answer = pd.DataFrame(columns={"NAME", "NUMBER"})
        answer.NAME = ["chad", "sam", "alex", "jun"]
        answer.NUMBER = [8, 3, 2, 7]
        df1, df2 = self._create_test_df()
        # create the destination table
        savepath = "s3://pitchbook-snowflake/test_objects/df1.csv"
        conn.create(object_name="TEST",object_type="TABLE",
            DATABASE="BUSINESS_INTELLIGENCE",SCHEMA="RTS_UPDATE",df=df1)
        # create an s3 object to bulk append
        savepath = "s3://pitchbook-snowflake/test_objects/df2.csv"
        flex_write(df2, savepath, s3=True)
        conn.update(schema_name="RTS_UPDATE", table_name="TEST",
            filepath=savepath, update_on="NAME")
        conn.query_executor("USE DATABASE BUSINESS_INTELLIGENCE")
        df = conn.sql_dataframe("SELECT * FROM RTS_UPDATE.TEST")
        conn.query_executor("DROP TABLE RTS_UPDATE.TEST")
        self.assertTrue(df.equals(answer))

    def _create_test_df(self):
        df1 = pd.DataFrame(columns={"NAME", "NUMBER"})
        df1.NAME = ["sam", "alex", "chad"]
        df1.NUMBER = [1,2, 8]
        df2 = pd.DataFrame(columns={"NAME", "NUMBER"})
        df2.NAME = ["sam", "alex", "jun"]
        df2.NUMBER = [3,2,7]
        return df1, df2

if __name__ == '__main__':
    unittest.main()
