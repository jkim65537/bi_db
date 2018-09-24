import pandas as pd
from simple_salesforce import Salesforce
from simple_salesforce import SalesforceLogin
from salesforce_bulk import SalesforceBulk
from biz_intel_creds import CredsList
sf_api_creds = CredsList().prod

class SalesforceSOAPConnection():
    def __init__(self):
        self.sf_connection = Salesforce(username=sf_api_creds['login'],
                                        password=sf_api_creds['pw'],
                                        security_token=\
                                            sf_api_creds['author_token'])

    def sf_query(self, insert_dictionary, start_time, end_time):
        object_type = insert_dictionary["name"]
        field_list = [i['field_name'] for i in insert_dictionary['fields']]
        field_string = list_to_string(field_list)
        sf_get_data = self.sf_connection.query(
            """
            SELECT {0}
            FROM {1}
            WHERE LastModifiedDate >= {2}
            AND LastModifiedDate < {3}""".\
                format(field_string, object_type, start_time, end_time))
        sf_records = pd.DataFrame(sf_get_data['records'])
        sf_records_no_attributes = sf_records.drop('attributes', 1)
        return sf_records_no_attributes

    def sf_query_all(self, insert_dictionary, start_time, end_time):
        object_type = insert_dictionary["name"]
        field_list = [i['field_name'] for i in insert_dictionary['fields']]
        field_string = list_to_string(field_list)
        sf_get_data = self.sf_connection.query_all(
            """
            SELECT {0}
            FROM {1}
            WHERE LastModifiedDate >= {2}
            AND LastModifiedDate < {3}""".\
                format(field_string, object_type, start_time, end_time))
        sf_records = pd.DataFrame(sf_get_data['records'])
        if len(sf_records) > 0:
            sf_records_no_attributes = sf_records.drop('attributes', 1)
        else:
            sf_records_no_attributes = sf_records
        return sf_records_no_attributes

    def query_object(self, query):
        sf_get_data = self.sf_connection.query_all(query)
        sf_records = pd.DataFrame(sf_get_data['records'])
        if len(sf_records) > 0:
            sf_records_no_attributes = sf_records.drop('attributes', 1)
        else:
            sf_records_no_attributes = sf_records
        return sf_records_no_attributes

    def query_deleted_object(self, query):
        sf_get_data = self.sf_connection.restful(\
            'queryAll', {'q': "{0} AND IsDeleted = TRUE".format(query)})
        sf_records = pd.DataFrame([i for i in sf_get_data['records']])
        if len(sf_records) > 0:
            sf_records_no_attributes = sf_records.drop('attributes', 1)
        else:
            sf_records_no_attributes = sf_records
        return sf_records_no_attributes

    def sf_query_deleted(self, insert_dictionary, start_time, end_time):
        object_type = insert_dictionary["name"]
        field_list = [i['field_name'] for i in insert_dictionary['fields']]
        field_string = list_to_string(field_list)
        sf_get_data = self.sf_connection.restful(\
            'queryAll', {'q':
                        'SELECT {0} FROM {1} WHERE LastModifiedDate >= {2}' \
                        ' AND LastModifiedDate < {3} AND IsDeleted = TRUE'.\
                            format(field_string,
                                    object_type,
                                    start_time,
                                    end_time)})
        sf_records = pd.DataFrame([i for i in sf_get_data['records']])
        if len(sf_records) > 0:
            sf_records_no_attributes = sf_records.drop('attributes', 1)
        else:
            sf_records_no_attributes = sf_records
        return sf_records_no_attributes

    def sf_query_record_count(self, object_name):
        sf_get_data = self.sf_connection.restful(\
            'queryAll', {'q': 'SELECT count() FROM {0}'.format(object_name)})
        sf_records = pd.DataFrame([i for i in sf_get_data['records']])
        if len(sf_records) > 0:
            sf_records_no_attributes = sf_records.drop('attributes', 1)
        else:
            sf_records_no_attributes = sf_records
        return sf_records_no_attributes
