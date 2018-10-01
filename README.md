# bi_db 1.3.2

# Introduction
Easy way to connect, query, and take actions on BI related databases.
It is by no means complete yet. Still building methods on top of the main API.
Only works with Pandas version 0.18.1 or higher.
Python 2 & 3 compatible and OS Independent

# API Details

## Installation

To install, run the command below

```
pip install bi_db
```

## Connections

* dbConnection
* DemandGenConnection
* GammaRedshift
* JobviteConnection
* PBAdminConnection
* PBAPIUsage
* PBLogCopyConnection
* RedshiftConnection
* RTSConnection
* S3DevTrackingData
* SalesforceSOAPConnection
* SFReplicationConnection
* SnowflakeConnection

## API Methods (applies to all)
* `sql_dataframe`: Execute the query and return the queried results
                   in a pandas dataframe.

## API Methods (only applies to SnowflakeConnection)
* `write_to_sql`: Append to or replace an existing table in snowflake.
* `load`: Bulk load s3 object into Snowflake.
* `append`: Bulk append s3 object into Snowflake.
* `replace`: Bulk replace s3 object into Snowflake.
* `update`: Bulk upsert s3 object into Snowflake.
* `create`: Create a database object.
* `unload`: Unload a database table into a specified s3 location (not tested yet).
* `get_metadata`: Get and return the metadata table.
* `get_query_id`: Get and return the query_id.
* `cancel_query`: Cancel the query of the given query_id.
* `query_executor`: Executes the query.
* `sql_dataframe`: Execute the query and return the queried results
                   in a pandas dataframe.
* `change_data_type`: Change the data type of a column in a table.
* `get_data_type_conversion_function` (private): Gets the sql function for the given data type.
* `create_custom_engine` (private): Creates custom engine to Snowflake.
* `table_exists` (private): Checks to see if table exists.
* `close_connection` (private): Closes the open connection to Snowflake db.
* `drop_table` (private): Drops a table from Snowflake db.
* `grant_permission` (private): Grants permission to database objects.
* `format_for_load` (private): Formats the Pandas DataFrame for database load operation.
* `get_bucket` (private): Returns the relevant information regarding the s3 bucket in use.

## Example Usage

### Set up

```python
from bi_db import SnowflakeConnection
sc = SnowflakeConnection()
```
### write_to_sql example

```python
# if_exists is a key argument. If not specified, it defaults to "append"
sc.write_to_sql(df=df, db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
                table_name="TABLE_NAME", if_exists="replace")
```

### load example

```python
sc.load(db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
        table_name="TABLE_NAME", filepath="s3://bucket_name/path/filename",
        format = "csv", if_exists="replace")
```

### append example

```python
sc.append(db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
          table_name="TABLE_NAME", filepath="s3://bucket_name/path/filename",
          format = "csv")
```

### replace example

```python
sc.replace(db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
           table_name="TABLE_NAME", filepath="s3://bucket_name/path/filename",
           format = "csv")
```

### update example

```python
sc.update(db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
          table_name="TABLE_NAME", filepath="s3://bucket_name/path/filename",
          format = "csv", updated_on="column_name")
```

### create example

```python
# create a database
sc.create(object_name="DATABASE_NAME", object_type="DATABASE")

# create a datawarehouse
sc.create(object_name="DATAWAREHOUSE_NAME", object_type="DATAWAREHOUSE")

# create a schema
sc.create(object_name="SCHEMA_NAME", object_type="SCHEMA",
        DATABASE="DATABASE_NAME")

# create a table
sc.create(object_name="TABLE_NAME", object_type="TABLE",
        DATABASE="DATABASE_NAME", SCHEMA="SCHEMA_NAME", df=df)
```

### get_metadata example

```python
sc.get_metadata(db_name="DATABASE_NAME", schema_name="SCHEMA_NAME",
                table_name="TABLE_NAME")
```

### get_query_id example

```python
# returns the query id of the last query ran
sc.get_query_id(query_order=-1)
```

### cancel_query example

```python
sc.cancel_query(query_id="abcdefghijk")
```

### query_executor example

```python
sc.query_executor(query="DROP TABLE TABLE_NAME")
```

### sql_dataframe example

```python
sc.sql_dataframe(query="SELECT * FROM DB.SCHEMA.TABLE")
```
