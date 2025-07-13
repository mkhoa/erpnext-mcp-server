import requests
import json
import os
# Use python-dotenv to load environment variables from a .env file
from dotenv import load_dotenv
from base64 import b64encode
from urllib.parse import quote
from io import StringIO
from typing import Optional

# Load environment variables from .env file in the project root
load_dotenv()
class AuthError(Exception):
	pass


class FrappeException(Exception):
	pass


class NotUploadableException(FrappeException):
	def __init__(self, doctype):
		self.message = "The doctype `{0}` is not uploadable, so you can't download the template".format(doctype)


class FrappeClient(object):
	def __init__(self, verify=True):
		self.headers = dict(Accept='application/json')
		self.session = requests.Session()
		self.can_download = []
		self.verify = verify
		self.url = os.environ.get("FRAPPE_URL")
		self.api_key = os.environ.get("FRAPPE_API_KEY")
		self.api_secret = os.environ.get("FRAPPE_API_SECRET")
		# Authenticate
		self.authenticate()

	def __enter__(self):
		return self

	def __exit__(self, *args, **kwargs):
		self.logout()

	def login(self, username, password):
		r = self.session.post(self.url, data={
			'cmd': 'login',
			'usr': username,
			'pwd': password,
		}, verify=self.verify, headers=self.headers)

		if r.json().get('message') == "Logged In":
			self.can_download = []
			return r.json()
		else:
			raise AuthError

	def authenticate(self):
		token = b64encode('{}:{}'.format(self.api_key, self.api_secret).encode()).decode()
		auth_header = {'Authorization': 'Basic {}'.format(token)}
		self.session.headers.update(auth_header)

	def logout(self):
		self.session.get(self.url, params={
			'cmd': 'logout',
		})

	def get_list(self, doctype, fields=["*"], filters=None, or_filters=None, limit_start=0, limit_page_length=0, order_by=None):
		fields = json.dumps(fields)
		params = {
			"fields": fields,
		}
		if filters:
			params["filters"] = json.dumps(filters)
		if or_filters:
			params["or_filters"] = json.dumps(or_filters)
		if limit_page_length:
			params["limit_start"] = limit_start
			params["limit_page_length"] = limit_page_length
		if order_by:
			params['order_by'] = order_by

		res = self.session.get(self.url + "/api/resource/" + doctype, params=params,
			verify=self.verify, headers=self.headers, timeout=30)
		return self.post_process(res)

	def insert(self, doc):
		'''Insert a document to the remote server

		:param doc: A dict or Document object to be inserted remotely'''
		res = self.session.post(self.url + "/api/resource/" + quote(doc.get("doctype")), timeout=30,
			data={"data":json.dumps(doc)})
		return self.post_process(res)

	def insert_many(self, docs):
		'''Insert multiple documents to the remote server

		:param docs: List of dict or Document objects to be inserted in one request'''
		return self.post_request({
			"cmd": "frappe.client.insert_many",
			"docs": 	(docs)
		})

	def update(self, doc):
		'''Update a remote document

		:param doc: dict or Document object to be updated remotely. `name` is mandatory for this'''
		url = self.url + "/api/resource/" + quote(doc.get("doctype")) + "/" + quote(doc.get("name"))
		res = self.session.put(url, data={"data":json.dumps(doc)}, timeout=30)
		return self.post_process(res)

	def bulk_update(self, docs):
		'''Bulk update documents remotely

		:param docs: List of dict or Document objects to be updated remotely (by `name`)'''
		return self.post_request({
			'cmd': 'frappe.client.bulk_update',
			'docs': json.dumps(docs)
		})

	def delete(self, doctype, name):
		'''Delete remote document by name

		:param doctype: `doctype` to be deleted
		:param name: `name` of document to be deleted'''
		return self.post_request({
			'cmd': 'frappe.client.delete',
			'doctype': doctype,
			'name': name
		})

	def submit(self, doclist):
		'''Submit remote document

		:param doc: dict or Document object to be submitted remotely'''
		return self.post_request({
			'cmd': 'frappe.client.submit',
			'doclist': json.dumps(doclist)
		})

	def get_value(self, doctype, fieldname=None, filters=None):
		return self.get_request({
			'cmd': 'frappe.client.get_value',
			'doctype': doctype,
			'fieldname': fieldname or 'name',
			'filters': json.dumps(filters)
		})

	def set_value(self, doctype, docname, fieldname, value):
		return self.post_request({
			'cmd': 'frappe.client.set_value',
			'doctype': doctype,
			'name': docname,
			'fieldname': fieldname,
			'value': value
		})

	def cancel(self, doctype, name):
		return self.post_request({
			'cmd': 'frappe.client.cancel',
			'doctype': doctype,
			'name': name
		})

	def get_doc(self, doctype, name="", filters=None, fields=None):
		'''Returns a single remote document

		:param doctype: DocType of the document to be returned
		:param name: (optional) `name` of the document to be returned
		:param filters: (optional) Filter by this dict if name is not set
		:param fields: (optional) Fields to be returned, will return everythign if not set'''
		params = {}
		if filters:
			params["filters"] = json.dumps(filters)
		if fields:
			params["fields"] = json.dumps(fields)
		
		res = self.session.get(self.url + '/api/resource/' + doctype + '/' + name, timeout=30,
							   params=params)
		
		return self.post_process(res)

	def get_customer_code(self, customer_name: str) -> str | None:
		"""Look up for Customer Code from Customer Name"""
		filters = {"customer_name": ["like", f"%{customer_name}%"]}
		customer_list = self.get_list("Customer", fields=["name"], filters=filters, limit_page_length=1)
		if customer_list:
			return customer_list[0].get("name")
		return None

	def get_item_code(self, item_query: str) -> str | None:
		"""Look up for Item_Code from Item Description or Item Name or Item Code itself"""
		# Convert spaces to SQL wildcards to handle missing middle words/characters.
		wildcard_query = '%'.join(item_query.split())

		or_filters = [
			['name', 'like', f'%{wildcard_query}%'],
			['item_name', 'like', f'%{wildcard_query}%'],
			['description', 'like', f'%{wildcard_query}%']
		]
		item_list = self.get_list("Item", fields=["name"], or_filters=or_filters, limit_page_length=1)
		if item_list:
			return item_list[0].get("name")
		return None

	def get_warehouse_code(self, warehouse_name: str) -> str | None:
		"""Look up for Warehouse Code from Warehouse Name"""
		filters = {"warehouse_name": ["like", f"%{warehouse_name}%"]}
		warehouse_list = self.get_list("Warehouse", fields=["name"], filters=filters, limit_page_length=1)
		if warehouse_list:
			return warehouse_list[0].get("name")
		return None

	def get_latest_stock_qty(self, item_code: str, warehouse: Optional[str] = None) -> float:
		"""Query a lasted stock quantity of an item_code"""
		return self.get_api('erpnext.stock.utils.get_latest_stock_qty', params={'item_code': item_code, 'warehouse': warehouse})

	def get_customer_outstanding_balance(self, customer_code: str) -> float:
		"""Query Outstanding AR Balance of a Customer_Code"""
		return self.get_api('erpnext.selling.doctype.customer.customer.get_customer_outstanding',
			params={'customer': customer_code})

	def rename_doc(self, doctype, old_name, new_name):
		'''Rename remote document

		:param doctype: DocType of the document to be renamed
		:param old_name: Current `name` of the document to be renamed
		:param new_name: New `name` to be set'''
		params = {
			'cmd': 'frappe.client.rename_doc',
			'doctype': doctype,
			'old_name': old_name,
			'new_name': new_name
		}
		return self.post_request(params)

	def get_pdf(self, doctype, name, print_format='Standard', letterhead=True):
		params = {
			'doctype': doctype,
			'name': name,
			'format': print_format,
			'no_letterhead': int(not bool(letterhead))
		}
		response = self.session.get(
			self.url + '/api/method/frappe.templates.pages.print.download_pdf',
			params=params, stream=True, timeout=30)

		return self.post_process_file_stream(response)

	def get_html(self, doctype, name, print_format='Standard', letterhead=True):
		params = {
			'doctype': doctype,
			'name': name,
			'format': print_format,
			'no_letterhead': int(not bool(letterhead))
		}
		response = self.session.get(
			self.url + '/print', params=params, stream=True, timeout=30
		)
		return self.post_process_file_stream(response)

	def __load_downloadable_templates(self):
		self.can_download = self.get_api('frappe.core.page.data_import_tool.data_import_tool.get_doctypes')

	def get_upload_template(self, doctype, with_data=False):
		if not self.can_download:
			self.__load_downloadable_templates()

		if doctype not in self.can_download:
			raise NotUploadableException(doctype)

		params = {
			'doctype': doctype,
			'parent_doctype': doctype,
			'with_data': 'Yes' if with_data else 'No',
			'all_doctypes': 'Yes'
		}

		request = self.session.get(
			self.url + '/api/method/frappe.core.page.data_import_tool.exporter.get_template',
			params=params, timeout=30
		)
		return self.post_process_file_stream(request)

	def get_api(self, method, params={}):
		res = self.session.get(self.url + '/api/method/' + method + '/', params=params, timeout=30)
		return self.post_process(res)

	def post_api(self, method, params={}):
		res = self.session.post(self.url + '/api/method/' + method + '/', params=params, timeout=30)
		return self.post_process(res)

	def get_request(self, params):
		res = self.session.get(self.url, params=self.preprocess(params), timeout=30)
		res = self.post_process(res)
		return res

	def post_request(self, data):
		res = self.session.post(self.url, data=self.preprocess(data), timeout=30)
		res = self.post_process(res)
		return res

	def preprocess(self, params):
		'''convert dicts, lists to json'''
		for key, value in params.items():
			if isinstance(value, (dict, list)):
				params[key] = json.dumps(value)

		return params

	def post_process(self, response):
		try:
			rjson = response.json()
		except ValueError:
			print(response.text)
			raise

		if rjson and ('exc' in rjson) and rjson['exc']:
			raise FrappeException(rjson['exc'])
		if 'message' in rjson:
			return rjson['message']
		elif 'data' in rjson:
			return rjson['data']
		else:
			return None

	def post_process_file_stream(self, response):
		if response.ok:
			output = StringIO()
			for block in response.iter_content(1024):
				output.write(block)
			return output

		else:
			try:
				rjson = response.json()
			except ValueError:
				print(response.text)
				raise

			if rjson and ('exc' in rjson) and rjson['exc']:
				raise FrappeException(rjson['exc'])
			if 'message' in rjson:
				return rjson['message']
			elif 'data' in rjson:
				return rjson['data']
			else:
				return None