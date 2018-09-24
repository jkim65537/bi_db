from __future__ import print_function
import pandas as pd
import sys
import getpass
from sqlalchemy import create_engine
from bi_db.bi_exceptions import RedshiftException
from bi_db.db_connection import dbConnection
from datetime import datetime
from bi_tools import flex_write

from biz_intel_creds import CredsList
redshift_creds = CredsList().rs_dw

global username
username = getpass.getuser()

def list_to_string(insert_list):
    """Transforms a list into a string.

    Args:
        insert_list: the list to transform into a string
    Returns:
        transformed list
    Raises:
        NA
    """
    field_string = ', '.join("{0}".format(i) for i in insert_list)
    return field_string

class RedshiftConnection(dbConnection):
    def __init__(self):
        ctype = "postgresql+psycopg2://"
        port_num = "5439"
        super(RedshiftConnection, self).__init__(connection_type=ctype,
                                                creds=redshift_creds,
                                                port=port_num)

    def load(self, schema_name, table_name, s3_path):
        query = """
        copy {schemaname}.{tablename}
        from '{s3path}'
        iam_role 'arn:aws:iam::542960883369:role/redshift_access_role'
        DELIMITER ','
        IGNOREHEADER 1
        maxerror as 100
        csv dateformat 'auto';
        """.format(schemaname=schema_name,
                    tablename= table_name,
                    s3path=s3_path)
        self.query_executor(query)

    def unload(self, database, schema, table, **kwargs):
        """Unload a database table into a specified s3 location

        Args:
            database: name of the database
            schema_name: name of the schema
            table_name: name of the table
            s3_path: filepath of the s3 object
            kwargs: ["aws_access_key_id", "aws_secret_access_key"]
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

        if set(["aws_access_key_id", "aws_secret_access_key"]) < \
            set(list(kwargs)):
            aws_key_given = True
        else:
            aws_key_given = False

        if not aws_key_given:
            sql="""
        UNLOAD \
('select * from {database}.{schema}.{table}') TO '{s3path}/{schema}_{table}' \
        CREDENTIALS
            'aws_iam_role=arn:aws:iam::542960883369:role/redshift_access_role' \
        DELIMITER AS ',' \
        ADDQUOTES \
        NULL AS '' \
        ALLOWOVERWRITE \
        MAXFILESIZE AS 2500 \
        PARALLEL OFF;"""\
            .format(database=database,
                   schema=schema,
                   table=table,
                   s3path=s3_path)
        elif aws_key_given:
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
                   aki=kwargs["aws_access_key_id"],
                   sck=kwargs["aws_secret_access_key"])
        #logger.custom_log("Unloading your table")
        self.query_executor(sql)

        df = self.sql_dataframe("select * from {}.{}.{} limit 3;".format(
                database, schema, table))
        df = pd.DataFrame(df.columns)
        df.rename(columns={0:"column_name"}, inplace=True)
        flex_write(df, s3_path + "/column_names.csv", "csv", s3=True)

    def get_metadata_table(self, table_name):
        query = """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTh
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{}'
                """.format(table_name)
        df = self.sql_dataframe(query)
        if len(df) == 0:
            raise RedshiftException("{} does not exist".format(table_name))
        return df

    def make_table(self, df, table_name, schema_name):
        final_df = pd.DataFrame()
        dftype = dict(df.dtypes)
        strings = dict((k, v) for k, v in dftype.items() if v == object)
        numbers = dict((k, v) for k, v in dftype.items() if v != object)

        for col in strings:
            df["len"] = df[col].str.len()
            df_to_append = df.sort_values(by="len", ascending=False)
            final_df.append(df_to_append[:1])

        for col in numbers:
            max_num = df[col].idxmax(axis=1)
            df_to_append = df.loc[df[col] == max_num]
            final_df.append(df_to_append[:1])

        del final_df["len"]

        final_df.to_sql(name=table_name, con=self.connection,
                         schema=schema_name, index = False,
                         if_exists = 'create', chunksize=10000)

    def query_executor(self, query):
        """Executes the specified query.

        Args:
            query: query to execute
        Returns:
            NA
        Raises:
            NA
        """
        self.connection.execute(query)

    def _table_exists(self, table_name):
        """Check whether a given table exists in a given database schema.

        Args:
            schema_name: name of the database schema
            table_name: name of the table
        Returns:
            table_exists: boolean
        Raises:
            NA
        """
        exist_query = "SELECT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES" \
        " where table_name = '{table_name}')".format(table_name=table_name)
        df = pd.read_sql(exist_query, self.connection)
        table_exists = df['?column?'][0]
        return table_exists

    def _grant_permission(self, table_name, schema_name):
        query = "GRANT SELECT ON {sn}.{tn} TO GROUP ro_group;".\
                format(tn=table_name, sn=schema_name)
        self.query_executor(query)

    def drop_table(self, table_name, schema_name):
        """Drop the specified table in the specified schema.

        Args:
            table_name: name of the table that needs to be dropped
            schema_name: name of the schema that the table_name is in
        Returns:
            NA
        Raises:
            NA
        """
        drop_query = """SET SEARCH_PATH TO {0}; DROP TABLE IF EXISTS {1}""".\
                        format(schema_name, table_name)
        self.connection.execute(drop_query)
        self.connection.close()

    def create_table(self, table_name, schema_name, df=None):
        """Insert table.

        Args:
            df: pandas dataframe to upload
            table_name: name of the table to insert
            schema_name: name of the schema the table is in
        Returns:
            NA
        Raises:
            RedshiftException: Table already exists, so replace_table function
                            should be used instead
        """

        #if not given a dataframe, then use an empty dataframe to create table
        if df==None:
            df = pd.DataFrame()
        if int(str(pd.__version__).replace(".", "")) <= 181:
            raise RedshiftException("Update your python version to use this func")

        if self._table_exists("table_name"):
            raise RedshiftException("Table already exists."\
                            "Please use the replace_table function instead.")
        else:
            df.to_sql(name=table_name, con= self.connection, schema=schema_name,\
                    index=False, if_exists="fail", chunksize=500)
            print("{table} successfully created.".format(table=table_name))
            self._grant_permission(table_name, schema_name)

    def replace_table(self, df, table_name, schema_name):
        """Replace an existing table.

        Args:
            df: pandas dataframe to upload
            table_name: name of the table to replace
            schema_name: name of the schema the table is in
        Returns:
            NA
        Raises:
            NA
        """
        if int(str(pd.__version__).replace(".", "")) <= 181:
            raise RedshiftException("Update your python version to use this func")
        df.to_sql(name=table_name, con=self.connection, schema=schema_name,\
                index=False, if_exists="replace", chunksize=500)
        print("{table} successfully replaced.".format(table=table_name))
        self._grant_permission(table_name, schema_name)

    def update_table(self, df, table_name, schema_name):
        """Update the sql data table of your choice

        Args:
            df: pandas dataframe to upload
            table_name: name of the table to insert
            schema_name: name of the schema the table is in
        Returns:
            NA
        Raises:
            NA
        """
        if int(str(pd.__version__).replace(".", "")) <= 181:
            raise RedshiftException("Update your python version to use this func")
        print("Updating table...")
        df.to_sql(name=table_name, con=self.connection, schema=schema_name,\
                index=False, if_exists="append", chunksize=500)
        print("{table} successfully updated.".format(table=table_name))
        self._grant_permission(table_name, schema_name)


    def change_table_name(self, schema_name, old_table_name, new_table_name):
        """Change the table name of your choice.

        Args:
            schema_name: name of the schema the table you want to change the
                        name of is in
            old_table_name: name of the table that you want to change
            new_table_name: new name of the table
        Returns:
            NA
        Raises:
            NA
        """

        table_name_change_query = """alter table {schema}.{old} rename
                                    to {new};
                                    """.format(schema=schema_name,
                                               old=old_table_name,
                                               new=new_table_name)
        self.connection.execute(table_name_change_query)
        self.connection.close()

    def csv_s3_redshift(self, insert_dataframe, table_name, schema_name):
        """Saves the CSV, uploads the CSV to S3, and updates the table within
            Redshift.

        Args:
            query: query to execute
        Returns:
            NA
        Raises:
            InternalError: when the table named after `table_name` does not
                           exist in `scehma_name`
        """
        filename = table_name + ".csv"
        filepath = "/home/{username}/csv/{filename}".format(username=username,
                                                            filename=filename)
        bucket_name = "redshiftstoragetransfer"
        print("Writing the CSV...")
        insert_dataframe.to_csv(filepath, header=None, index=False)
        s3 = boto3.client('s3')
        print("Uploading the CSV to S3")
        s3.upload_file(filename, bucket_name, filename)
        column_names = list_to_string(list(insert_dataframe))
        copy_query = """
                    SET SEARCH_PATH TO {schema}; COPY {table}({columns})
                    FROM 's3://redshiftstoragetransfer/{csv_name}'
                    CREDENTIALS 'aws_iam_role=arn:aws:iam::542960883369:role"""\
                    """/redshift_access_role' csv dateformat 'auto';"""\
                    .format(schema=schema_name,
                            table=table_name,
                            columns=column_names,
                            csv_name=filename)

        if self._table_exists(table_name):
            self.connection.execute(copy_query)
            self.connection.close()
        else:
            print("{table_name} does not exist in {schema_name}".\
                format(table_name=table_name, schema_name=schema_name))
        print("Saving {table_name} on {schema_name}".\
            format(table_name=table_name, schema_name=schema_name))

    def sql_dataframe(self, query):
        """Execute the query and return the queried results
           in a pandas dataframe.

        Args:
            query: query to execute
        Returns:
            df_result: pandas DataFrame of the queried result
        Raises:
            NA
        """
        try:
            df_result = pd.read_sql(query, self.connection)
        except TypeError:
            df_result = pd.read_sql(query.replace("%", "%%"), self.connection)

        return df_result

    def csv_s3_merge_redshift(self, insert_dataframe, table_name, key, schema_name):
        """Swap out the rows in a specified table in redshift with the rows in
           a specified dataframe by merging the two tables on a specified key.

        Args:
            insert_dataframe: pandas DataFrameto insert
            table_name: name of the table on redshift that will be modified
            key: name of the key variable to use
            schema_name: name of the schema that the table
                         you want to modify is in
        Returns:
            NA
        Raises:
            NA
        """
        if len(insert_dataframe) > 0:
            filename = table_name + "_temp.csv"
            bucket_name = "redshiftstoragetransfer"
            insert_dataframe.to_csv(filename, header=None, index=False)
            s3 = boto3.client('s3')
            s3.upload_file(filename, bucket_name, filename)
            column_names = list_to_string(list(insert_dataframe))
            temp_table_name = table_name + "_temp"
            merge_query = """
                            SET SEARCH_PATH TO {schema}; CREATE TEMP TABLE {temp_table_name} (LIKE {actual_table});

                                  COPY {temp_table_name}({columns}) FROM 's3://redshiftstoragetransfer/{csv_name}' CREDENTIALS 'aws_iam_role=arn:aws:iam::542960883369:role/redshift_access_role' csv dateformat 'auto';

                                  BEGIN TRANSACTION;

                                  DELETE FROM {actual_table}

                                  USING {temp_table_name}

                                  WHERE {temp_table_name}.{key} = {actual_table}.{key};

                                  INSERT INTO {actual_table}

                                  SELECT * FROM {temp_table_name};

                                  END TRANSACTION;

                                  DROP TABLE {temp_table_name};""".format(schema=schema_name, temp_table_name=temp_table_name, actual_table=table_name, columns=column_names, csv_name=filename, key=key)

            connection = self.engine.connect()
            connection.execute(merge_query)
            connection.close()
        else:
            pass
