from __future__ import print_function
import sys
import pandas as pd
import snowflake.connector
from bi_db.bi_exceptions import SnowflakeException
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from snowflake.sqlalchemy import URL
from datetime import datetime
from bi_tools import flex_read
from bi_tools import flex_write

from s3_buckets import S3Buckets
s3_snowflake = S3Buckets().snowflake
from biz_intel_creds import CredsList
snowflake_creds = CredsList().snowflake

class SnowflakeConnection(object):
    def __init__(self):
        """Snowflake Database Connection. Wrapper library designed and built
        to help users run database operations on Snowflake more easily.

        Args:
            NA
        Returns:
            NA
        Raises:
            NA
        """
        self.connection = snowflake.connector.connect(
                            user=snowflake_creds['USER'],
                            password=snowflake_creds['PASSWORD'],
                            account=snowflake_creds['ACCOUNT'],
                            role="ACCOUNTADMIN"
                        )
        self.engine = self.connection.cursor()

    def write_to_sql(self, df, schema_name, table_name,
        db_name=s3_snowflake["database_name"],**kwargs):
        """Writes records stored in a DataFrame to Snowflake database.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            kwargs: ["if_exists"]
        Returns:
            NA
        Raises:
            NA
        """
        # check to see if `if_exists` key argument was passed in
        try:
            kwargs["if_exists"]
            if kwargs["if_exists"] not in ["fail", "replace", "append"]:
                raise SnowflakeException("`if_exists` should be one of"\
                    "[`fail`, `replace`, `append`]")
            else:
                if_exists = kwargs["if_exists"]
        except NameError:
            if_exists = "append"
        except KeyError:
            if_exists = "append"

        custom_engine = self._create_custom_engine(db_name, schema_name)
        df = self._format_for_load(df)
        capitalize_columns_dict = {i: i.upper() for i in df.columns.tolist()}
        df = df.rename(columns=capitalize_columns_dict)
        df.to_sql(name=table_name, con=custom_engine, if_exists=if_exists,
            index=False, chunksize=1000)

    def load(self, schema_name, table_name,
        filepath, format , db_name=s3_snowflake["database_name"]):
        """Loads s3 object into Snowflake.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            filepath: filepath of the s3 object

            format: format of the s3 object
        Returns:
            NA
        Raises:
            NA
        """
        bucket = self._get_bucket(filepath)
        if format.upper() == "CSV":
            format = "comma_delimited"
        elif format.upper() == "JSON":
            raise SnowflakeException("format not supported")
        elif format.upper() == "GZIP":
            raise SnowflakeException("format not supported")
        else:
            raise SnowflakeException("format not supported")

        bucket_name = bucket["bucket_name"]

        if ".gz" in filepath:
            gz_df = flex_read(filepath, s3=True, bucket_name=bucket_name)
            import random
            random_num = random.randint(1,101)
            filepath = "{prefix}/tempfile/tempfile_{num}".format(
                prefix=s3_snowflake["prefix"], num=random_num)
            flex_write(gz_df, filepath, s3=True)

        load_query = """
        COPY INTO {schema}.{table} FROM {filepath}
        FILE_FORMAT = (FORMAT_NAME='{format}')
        ON_ERROR = CONTINUE
        force=true;
                    """.format(schema=schema_name,
                            table=table_name,
                            filepath=filepath.replace(bucket["prefix"],
                                                    bucket["stage"]),
                            format=format)
        if self._table_exists(table_name, schema_name, db_name):
            self.query_executor("USE SCHEMA {}.{}".format(db_name, "PUBLIC"))
            self.query_executor(load_query)
            self.query_executor("COMMIT")
        else:
            df = flex_read(filepath, s3=True,
                bucket_name=bucket["bucket_name"], nrows=500)
            self.engine.execute("USE SCHEMA {db_name}.{schema}".format(
                db_name=db_name,
                schema=schema_name
                )
            )
            self.write_to_sql(df=df, db_name=db_name,
                schema_name=schema_name, table_name=table_name,
                if_exists="replace"
            )
            self.query_executor("USE SCHEMA {}.{}".format(
                db_name, schema_name
                )
            )
            self.query_executor("DELETE FROM {}".format(table_name))
            self.query_executor("USE SCHEMA {}.{}".format(db_name, "PUBLIC"))
            self.query_executor(load_query)
            self.query_executor("COMMIT")
            self._grant_permission(db_name, schema_name)

    def append(self, schema_name, table_name,
        filepath, format="csv", db_name=s3_snowflake["database_name"]):
        """Bulk appends s3 object into Snowflake.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            filepath: filepath of the s3 object

            format: format of the s3 object
        Returns:
            NA
        Raises:
            NA
        """
        # default bulk load is bulk append
        self.load(schema_name, table_name,
            filepath, format, db_name)

    def update(self, schema_name, table_name, filepath, update_on,
        format="comma_delimited", db_name=s3_snowflake["database_name"]):
        """Bulk upserts s3 object into Snowflake.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            update_on: name of the column to update on

            filepath: filepath of the s3 object

            format: format of the s3 object
        Returns:
            NA
        Raises:
            NA
        """
        bucket = self._get_bucket(filepath)
        # create staging_{destination_table_name}
        # and upload to staging
        staging_name = "STAGING_" + table_name
        df = flex_read(filepath, s3=True,
                        bucket_name=bucket["bucket_name"], nrows=5)

        column_list = df.columns.tolist()
        update_column_match_string = ', '.join(
            "{column} = {schema}.{temp_table}.{column}".format(
            column=i, temp_table=staging_name,
            schema=schema_name) for i in column_list)
        temp_column_string = ', '.join(
            "{schema}.{temp_table}.{column}".format(
            column=i, temp_table=staging_name,
            schema=schema_name) for i in column_list)
        prod_column_string = ', '.join(
            "{column}".format(
            column=i) for i in column_list)
        self.query_executor("USE DATABASE {}".format(db_name))
        create_temp_table_query = \
            """CREATE TEMPORARY TABLE {schema}.{temp_table}
            LIKE {schema}.{table};""".format(
                schema=schema_name
                , table=table_name
                , temp_table=staging_name)
        load_temp_query = """COPY INTO {schema}.{temp_table}({prod_columns})
            FROM {filepath}
            FILE_FORMAT = (FORMAT_NAME='{format_name}'
            ESCAPE_UNENCLOSED_FIELD=NONE);""".format(
                schema=schema_name
                , temp_table=staging_name
                , prod_columns=prod_column_string
                , filepath=filepath.replace(
                    bucket["prefix"],
                    bucket["stage"])
                , format_name=format)
        merge_query = \
    """MERGE INTO {schema}.{table}
    USING {schema}.{temp_table}
    ON {schema}.{table}.{update_on} = {schema}.{temp_table}.{update_on}
    WHEN MATCHED THEN UPDATE SET {update_column_match_string}
    WHEN NOT MATCHED THEN INSERT({prod_columns}) VALUES({temp_columns});""".\
        format(
                schema=schema_name
                , table=table_name
                , temp_table=staging_name
                , update_on=update_on
                , update_column_match_string=update_column_match_string
                , prod_columns=prod_column_string
                , temp_columns=temp_column_string)
        self.query_executor("USE SCHEMA {}.{};".format(db_name, "PUBLIC"))
        self.query_executor(create_temp_table_query)
        self.query_executor(load_temp_query)
        self.query_executor(merge_query)

    def replace(self, schema_name, table_name,
        filepath, format="csv", db_name=s3_snowflake["database_name"]):
        """Bulk replaces s3 object into Snowflake.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            filepath: filepath of the s3 object

            format: format of the s3 object
        Returns:
            NA
        Raises:
            NA
        """
        # write staging
        staging_table_name = table_name.upper() + "_STAGING"
        self.query_executor("USE SCHEMA {db}.{sn}".format(
            db=db_name, sn=schema_name
            )
        )
        self.load(schema_name, staging_table_name,
            filepath, format, db_name
        )
        # change table names
        self.query_executor("USE SCHEMA {db}.{sn}".format(
            db=db_name, sn=schema_name
            )
        )
        self.query_executor("ALTER TABLE {tn} RENAME TO {gn}".format(
            tn=table_name, gn="garbage"
            )
        )
        self.query_executor("ALTER TABLE {stn} RENAME TO {tn}".format(
            stn=staging_table_name, tn=table_name
            )
        )
        # drop the old table
        self.query_executor("DROP TABLE {gn}".format(gn="garbage"))

    def create(self, object_name, object_type=None, **kwargs):
        """Creates a database object.

        Args:
            object_name: name of the object you are creating

            object_type: (DATABASE, SCHEMA, WAREHOUSE, TABLE)

            DATABASE(key argument): name of the database

            SCHEMA(key argument): name of the schema

            df(key argument): dataframe you want to create the table with
        Returns:
            NA
        Raises:
            NA
        """
        if "DATABASE" in kwargs:
            db_name = kwargs["DATABASE"]
            if "SCHEMA" in kwargs:
                schema_name = kwargs["SCHEMA"]

        if object_type is None:
            raise SnowflakeException("object type must be one of "\
                                        "['DATABASE', 'SCHEMA'," \
                                        "'WAREHOUSE', 'TABLE']"
                                    )
        elif object_type.upper() in ["DATABASE", "WAREHOUSE"]:
            self.engine.execute("CREATE {ot} IF NOT EXISTS {on}".format(
                ot=object_type, on=object_name
                )
            )
        elif object_type.upper() == "SCHEMA":
            self.engine.execute("USE DATABASE {db_name}".format(
                db_name=kwargs["DATABASE"]
                )
            )
            self.engine.execute("CREATE {ot} IF NOT EXISTS {on}".format(
                ot=object_type, on=object_name
                )
            )
            self._grant_permission(kwargs["DATABASE"], object_name)
        elif object_type.upper() == "TABLE":
            self.engine.execute("USE SCHEMA {db_name}.{schema}".format(
                db_name=kwargs["DATABASE"],
                schema=kwargs["SCHEMA"]
                )
            )
            # default append creates the table
            today = datetime.strftime(datetime.today(), "%Y-%m-%d")
            savepath = \
            "{prefix}/schema={schema}"\
            "/table={table}/{today}/{schema}_{table}.csv".format(
            prefix=s3_snowflake["prefix"], schema=kwargs["SCHEMA"],
            table=object_name, today=today)

            flex_write(kwargs["df"], savepath,s3=True)
            self.append(schema_name=kwargs["SCHEMA"], table_name=object_name,
                filepath=savepath)

    def unload(self, database, schema, table, **kwargs):
        """Unloads a database table into a specified s3 location

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
            s3_path = "{prefix}/schema={schema}/table={table}/"\
                "{today}".format(prefix=s3_snowflake["prefix"], schema=schema,
                                table=table, today=today)
        except KeyError:
            today = datetime.strftime(datetime.today(), "%Y-%m-%d")
            s3_path = "{prefix}/schema={schema}/table={table}/"\
                "{today}".format(prefix=s3_snowflake["prefix"], schema=schema,
                                table=table, today=today)
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


    def get_metadata(self, db_name, schema_name, table_name):
        """Gets and returns the metadata table.

        Args:
            database: name of the database

            schema: name of the schema

            table: name of the table
        Returns:
            metadata: list of metadata of each field
        Raises:
            NA
        """
        self.engine.execute("SELECT * FROM {}.{}.{} limit 5"\
            .format(db_name, schema_name, table_name))
        return ','.join([col[0] for col in self.engine.description])

    def get_query_id(self, query_order=-1):
        """Gets and returns the query_id.

        Args:
            query_order: the order of the query_id being fetched
        Returns:
            query_id: the id the of the query
        Raises:
            SnowflakeException
        """
        df = pd.read_sql(sql="select last_query_id({ord})"\
                        .format(ord=query_order),con=self.connection)
        return df["LAST_QUERY_ID({ord})".format(ord=query_order)][0]

    def cancel_query(self, query_id):
        """Cancels the query associated with the given query id.

        Args:
            query_id: the of query you want to cancel
        Returns:
            NA
        Raises:
            SnowflakeException
        """
        try:
            self.engine.execute(r"select SYSTEM$CANCEL_QUERY('{queryID}')"\
               .format(queryID=query_id))
        except:
            raise SnowflakeException("Cannot cancel query_id:{}"\
                .format(query_id))

    def query_executor(self, query):
        """Executes the query.

        Args:
            query: query to execute
        Returns:
            NA
        Raises:
            NA
        """
        self.engine.execute(query)

    def sql_dataframe(self, query):
        """Executes the query and return the queried results
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

    def change_data_type(self, schema_name, table_name, column_name,
        data_type, db_name="BUSINESS_INTELLIGENCE",
        need_confirmation=False, force=False, time_format='YYYY-MM-DD'):
        """Change the data type of a column in a table

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake

            table_name: name of the table in snowflake

            column_name: name of the column

            data_type: name of the desired data type in string

            need_confirmation: prompts to ask if the change should be committed
                                when set to True
            force: tries to force data type conversion then prompts to ask
                    if the rows with invalid values should be dropped
            time_format: format of time the string value is in
        Returns:
            NA
        Raises:
            NA

        Below is the mapping between your desired data type and sql functions
        used for each one.

        If 'force' argument is given and it's set to 'True':
        sql_functions = {
            "TIMESTAMP":"TRY_TO_TIMESTAMP",
            "DATE":"TRY_TO_DATE",
            "TIME":"TRY_TO_TIME",
            "NUMBER":"TRY_TO_NUMBER",
            "BINARY":"TRY_TO_BINARY",
            "BOOLEAN":"TRY_TO_BOOLEAN",
            "CHAR":"TO_CHAR",
            "NUMERIC":"TRY_TO_NUMERIC",
            "DECIMAL":"TRY_TO_DECIMAL",
            "DOUBLE":"TRY_TO_DOUBLE",
            "TIMESTAMP":"TRY_TO_TIMESTAMP"
            }
        else if 'force' argument is not given or it's set to 'False'
        sql_functions = {
            "TIMESTAMP":"TO_TIMESTAMP",
            "DATE":"TO_DATE",
            "TIME":"TO_TIME",
            "NUMBER":"TO_NUMBER",
            "BINARY":"TO_BINARY",
            "BOOLEAN":"TO_BOOLEAN",
            "CHAR":"TO_CHAR",
            "NUMERIC":"TO_NUMERIC",
            "DECIMAL":"TO_DECIMAL",
            "DOUBLE":"TO_DOUBLE",
            "TIMESTAMP":"TRY_TO_TIMESTAMP"
            }
        """
        # use the appropriate databae and schema
        self.query_executor("USE SCHEMA {dn}.{sn}".format(dn=db_name,
                                                        sn=schema_name))

        # add new column with prefix 'new_'
        self.query_executor("ALTER TABLE {tn} ADD NEW_{cn} {dt}"\
            .format(tn=table_name,
                    cn=column_name,
                    dt=data_type))

        # fetch the appropriate data type conversion sql function
        function_name = self._get_data_type_conversion_function(data_type,
                                                                force)

        # update the newly created column
        if function_name in ["TO_DATE", "TO_TIMESTAMP"]:
            self.query_executor(
            "Update {tn} SET NEW_{cn} = {fn}({cn}," + \
            " '{date_format}')"\
                .format(tn=table_name,
                        cn=column_name,
                        fn=function_name,
                        date_format=time_format))
        else:
            self.query_executor("Update {tn} SET NEW_{cn} = {fn}({cn})"\
                .format(tn=table_name,
                        cn=column_name,
                        fn=function_name))

        if force:
            # check for count of null values in the new column
            count = self.sql_dataframe(
            "SELECT COUNT(*) as COUNT FROM {tn} WHERE NEW_{cn} IS NULL"\
                .format(tn=table_name,
                        cn=column_name))["COUNT"][0]
            total_count = self.sql_dataframe(
            "SELECT COUNT(*) as COUNT FROM {tn}"\
                .format(tn=table_name,
                        cn=column_name))["COUNT"][0]
            # ask for user input as to if it's okay to drop those rows
            question = """
            Would you like to drop {cnt} rows out of {tcnt} where the values of
            NEW_{cn} are NULL to complete the data type conversion?
            \nAnswer 'yes' or 'no'""".format(cnt=count,
                                            tcnt=total_count,
                                            cn=column_name)
            if need_confirmation:
                answer = raw_input(question)
                if answer.lower() == "yes":
                    self.query_executor(
                        "DELETE FROM {tn} WHERE NEW_{cn} IS NULL".format(
                                                                tn=table_name,
                                                                cn=column_name))
                elif answer.lower() == "no":
                    self.query_executor("ALTER TABLE {tn} DROP COLUMN NEW_{cn}"\
                        .format(tn=table_name,
                                cn=column_name))
                    raise ValueError(
                        "Any changes you've made have been rolled back.")
            else:
                self.query_executor("DELETE FROM {tn} WHERE NEW_{cn} IS NULL"\
                    .format(tn=table_name,
                            cn=column_name))

        if need_confirmation:
            answer = raw_input(
                "Does the NEW_{cn} column look good?\nAnswer 'yes' or 'no'"\
                    .format(cn=column_name))
            if answer.lower() == "yes":
                pass
            elif answer.lower() == "no":
                self.query_executor(
                    "ALTER TABLE {tn} DROP COLUMN NEW_{cn}".format(
                                                                tn=table_name,
                                                                cn=column_name))
                raise ValueError(
                    "Any changes you've made have been rolled back.")

        # drop the old column
        self.query_executor("ALTER TABLE {tn} DROP COLUMN {cn}".format(
                                                                tn=table_name,
                                                                cn=column_name))

        # rename the new column to replace the old column
        self.query_executor("ALTER TABLE {tn} RENAME COLUMN NEW_{cn} to {cn}".\
            format(tn=table_name,
                    cn=column_name))


    def _get_data_type_conversion_function(self, data_type, force):
        """Gets the sql function for the given data type.

        Args:
            data_type: name of the desired data type in string
        Returns:
            sql_function: sql_function in string
        Raises:
            NA
        """
        #TODO add more sql functions for different data types
        if force:
            sql_functions = {
                "TIMESTAMP":"TRY_TO_TIMESTAMP",
                "DATE":"TRY_TO_DATE",
                "TIME":"TRY_TO_TIME",
                "NUMBER":"TRY_TO_NUMBER",
                "BINARY":"TRY_TO_BINARY",
                "BOOLEAN":"TRY_TO_BOOLEAN",
                "CHAR":"TO_CHAR",
                "NUMERIC":"TRY_TO_NUMERIC",
                "DECIMAL":"TRY_TO_DECIMAL",
                "DOUBLE":"TRY_TO_DOUBLE",
                "TIMESTAMP":"TRY_TO_TIMESTAMP"
                }
        elif not force:
            sql_functions = {
                "TIMESTAMP":"TO_TIMESTAMP",
                "DATE":"TO_DATE",
                "TIME":"TO_TIME",
                "NUMBER":"TO_NUMBER",
                "BINARY":"TO_BINARY",
                "BOOLEAN":"TO_BOOLEAN",
                "CHAR":"TO_CHAR",
                "NUMERIC":"TO_NUMERIC",
                "DECIMAL":"TO_DECIMAL",
                "DOUBLE":"TO_DOUBLE",
                "TIMESTAMP":"TRY_TO_TIMESTAMP"
                }
        return sql_functions[data_type.upper()]

    def _create_custom_engine(self, db_name, schema_name):
        """Creates custom engine to Snowflake.

        Args:
            db_name: name of the database in snowflake

            schema_name: name of the schema in snowflake
        Returns:
            NA
        Raises:
            NA
        """
        url = URL(account=snowflake_creds["ACCOUNT"],
                user=snowflake_creds["USER"],
                password=snowflake_creds["PASSWORD"],
                role="ACCOUNTADMIN",
                database=db_name,
                schema=schema_name,
                numpy=True)
        custom_engine = create_engine(url, poolclass=NullPool)
        return custom_engine

    def _table_exists(self, table_name, schema_name, db_name):
        """Checks to see if table exists.

        Args:
            table_name: name of the table in snowflake
        Returns:
            table_exists: boolean result of whether table exists or not
        Raises:
            NA
        """
        self.query_executor("USE DATABASE {}".format(db_name))
        df = self.sql_dataframe(
        "SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        df = df.loc[df.TABLE_SCHEMA==schema_name]
        if table_name in df.TABLE_NAME.unique():
            return True
        else:
            return False

    def _close_connection(self):
        """Closes the open connection to Snowflake db.

        Args:
            NA
        Returns:
            NA
        Raises:
            NA
        """
        self.connection.close()

    def _drop_table(self, db_name, schema_name, table_name):
        """Drops a table from Snowflake db.

        Args:
            NA
        Returns:
            NA
        Raises:
            NA
        """
        self.query_executor("USE SCHEMA {}.{}".format(db_name,schema_name))
        self.query_executor("DROP TABLE {}".format(table_name))

    def _grant_permission(self, db_name, schema_name, **kwargs):
        """Grants permission to database objects.

        Args:
            db_name:

            schema_name:

            table_name:

            role_name:
        Returns:
            NA
        Raises:
            NA
        """
        if "role" in kwargs:
            role = kwargs["role"]
        else:
            role = "BI_READ_ONLY"

        self.query_executor("USE DATABASE {}".format(db_name))
        self.query_executor(
            "grant usage on schema {} to role {};".format(schema_name, role))
        self.query_executor(
           "grant all on all tables in schema {} to role {};".format(
                schema_name, role))

    def _format_for_load(self, df):
        """Formats the Pandas DataFrame for database load operation

        Args:
            df: Pandas DataFrame for formatting
        Returns:
            df: Formatted Pandas DataFrame
        Raises:
            NA
        """
        try:
            datetime_cols = [x for x in df.columns if "_date" in x.lower()]
        except AttributeError as e:
            new_header = df.iloc[0]
            df = df[1:]
            df.columns = new_header
            datetime_cols = [x for x in df.columns if "_date" in x.lower()]
        except:
            raise ValueError("check your s3 object input")
        for col in datetime_cols:
            df[col] = pd.to_datetime(df[col], errors = 'coerce')
        # if all values for the given column is na, then set it to string
        for col in df.columns:
            if df[col].isnull().all():
                df[col] = df[col].astype(str)
        return df

    def _get_bucket(self, filepath):
        """Returns the relevant information regarding the s3 bucket in use

        Args:
            filepath: path to the flat file stored in s3
        Returns:
            dict_to_return: dictionary storing relevant information
        Raises:
            NA
        """
        import inspect
        s3_buckets = S3Buckets()
        attributes = inspect.getmembers(s3_buckets,
            lambda a:not(inspect.isroutine(a)))
        attr_dict = {}
        for i in range(2, len(attributes)):
            attr_dict[attributes[i][1]["prefix"]] = i

        prefix = [prefix for prefix in attr_dict.keys() \
                    if(prefix in filepath)]
        if prefix:
            prefix = prefix[0]
            dict_to_return = attributes[attr_dict[prefix]][1]
        else:
            raise SnowflakeException("invalid filepath: not supported bucket."\
            "Contact BI to add your s3 bucket to s3_bucket configuration file")
        return dict_to_return
