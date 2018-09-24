import pandas as pd
from bi_db.db_connection import dbConnection
from bi_db.redshift_connection import RedshiftConnection
from biz_intel_creds import CredsList
from bi_tools import flex_write
from datetime import datetime
gamma_creds = CredsList().gamma
gamma_keys = CredsList().gamma_key

class GammaRedshift(RedshiftConnection, dbConnection):
    def __init__(self):
        ctype = "postgresql+psycopg2://"
        port_num = "5439"
        super(RedshiftConnection, self).__init__(connection_type=ctype,
                                                creds=gamma_creds,
                                                port=port_num)
    def unload(self, database, schema, table):
        """Unload a database table into a specified s3 location

        Args:
            database: name of the database
            schema_name: name of the schema
            table_name: name of the table
            s3_path: filepath of the s3 object
        Returns:
            NA
        Raises:
            NA
        """
        schema = schema.upper()
        table = table.upper()
        try:
            kwargs["s3_path"]
            s3_path = kwargs["s3_path"]
        except NameError:
            today = datetime.strftime(datetime.today(), "%Y-%m-%d")
            s3_path = "s3://pitchbook-snowflake/schema={schema}/table={table}/"\
                "{today}".format(schema=schema, table=table, today=today)
        except KeyError:
            today = datetime.strftime(datetime.today(), "%Y-%m-%d")
            s3_path = "s3://pitchbook-snowflake/schema={schema}/table={table}/"\
                "{today}".format(schema=schema, table=table, today=today)

        sql="""
    UNLOAD \
('select * from {database}.{schema}.{table}') TO '{s3path}/{schema}_{table}' \
    CREDENTIALS
        'aws_access_key_id={aki};aws_secret_access_key={sck}' \
    DELIMITER AS ',' \
    ADDQUOTES \
    NULL AS '' \
    ALLOWOVERWRITE \
    MAXFILESIZE AS 2500 \
    PARALLEL OFF;"""\
        .format(database=database,
               schema=schema,
               table=table,
               s3path=s3_path,
               aki=gamma_keys["aws_access_key_id"],
               sck=gamma_keys["aws_secret_access_key"])
        #logger.custom_log("Unloading your table")
        self.query_executor(sql)

        df = self.sql_dataframe("select * from {}.{}.{} limit 3;".format(
                database, schema, table))
        df = pd.DataFrame(df.columns)
        df.rename(columns={0:"column_name"}, inplace=True)
        flex_write(df, s3_path + "/column_names.csv", "csv", s3=True)
