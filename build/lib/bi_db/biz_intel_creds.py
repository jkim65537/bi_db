class CredsList:
	def __init__(self):
		self.prod = {'pw': '', 'login' : '', 'author_token': ''}
		self.sf_replication = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.demand_gen = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.rts = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.pb_admin = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.pb_log_copy = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.businessintelligence = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.rs_dw = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.mongo = {'server': '', 'login': '', 'pw': ''}
		self.dev_s3 = {'key_id': '', 'key': '', 'bucket': ''}
		self.appuri_s3 = {'key_id': '', 'key': '', 'bucket': ''}
		self.airflow_email = {'email': '', 'pw': ''}
		self.api_db = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.jobvite = {'server': '', 'login': '', 'pw': '', 'db': ''}
		self.gamma = {'login':'', 'pw':'', 'server':'', 'db':''}
		self.snowflake = {'USER':'', 'PASSWORD':'', 'ACCOUNT':''}
		self.bi_s3 = {'key_id':"", "key":"", "bucket":""}
