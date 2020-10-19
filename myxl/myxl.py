import datetime
import json
import random

import multithreading
import requests


class MyXL(multithreading.MultiThreadRequest):
	host = 'my.xl.co.id'

	imei = '3571250436519001'
	imsi = '510110032177230'

	msisdn = None
	session_id = None

	default_platform = '04'
	default_priceplan = '513738114'
	default_subscriber_number = None

	file_name_success_list = 'data-event'

	def __init__(self, task_list=None, threads=None, verbose=False):
		super().__init__(task_list, threads=threads)
		self.logger = multithreading.Logger(level='DEBUG' if verbose else 'INFO')
		self.requests = requests.Session()

		self._task_success_event_list = []

	def request(self, method, uri, loop=False, **kwargs):
		while True:
			response = super().request(method, f'https://{self.host}/{uri}', **kwargs)
			if response is None and loop:
				continue
			return response

	def input(self, message, allow_blank=True):
		CC = self.logger.special_chars['CC']
		CN = self.logger.special_chars['CN']
		CR = self.logger.special_chars['CR']

		while True:
			result = str(input(f'{CR}{CN}{message}{CC}'))

			if not result and not allow_blank:
				continue

			if result:
				print('')

			return result

	"""
	Get
	"""

	def get_request_id(self):
		return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

	def get_request_date(self):
		return datetime.datetime.now().strftime('%Y%m%d')

	def get_transaction_id(self):
		return str(random.randint(100000000000, 999999999999))

	def get_headers(self, headers=None):
		default_headers = {
			'Host': self.host,
			'Accept': 'application/json, text/plain, */*',
			'Connection': 'keep-alive',
			'Content-Type': 'application/json',
			'Accept-Language': 'en-US,id;q=0.5',
			'Accept-Encoding': 'gzip, deflate, br',
			'Access-Control-Allow-Origin': 'True',
			'DNT': '1',
		}

		return self.dict_merge(default_headers, headers)

	def get_content(self, content=None):
		request_id = self.get_request_id()

		default_content = {
			'Header': None,
			'Body': {
				'Header': {
					'ReqID': request_id,
				},
				'opGetSubscriberProfileRq': {
					'headerRq': {
						'requestDate': '2019-06-22T20:01:51.065Z',
						'requestId': request_id,
						'channel': 'MYXLPRE'
					},
					'msisdn': self.msisdn,
				}
			},
			'sessionId': self.session_id,
			'platform': '04',
			'appVersion': '3.8.2',
			'sourceName': 'Firefox',
			'msisdn_Type': 'P',
			'screenName': 'home.dashboard',
		}

		return self.dict_merge(default_content, content)

	def get_default_subscriber_number(self):
		content = {
			"Body": {
				"PayloadQueryBalanceReq": {
					"msisdn": self.msisdn,
					"type": "ALL",
				}
			},
		}
		response = self.request('POST', 'pre/PayloadQueryBalanceReq', loop=True, json=self.get_content(content))

		subscriber_number = response.json().get('SOAP-ENV:Envelope', {}).get('SOAP-ENV:Body', [{}])[0]
		subscriber_number = subscriber_number.get('BilDiameterMediation:PayloadQueryBalanceResp', [{}])[0]
		subscriber_number = subscriber_number.get('diabilling:QueryInformation', [{}])[0]
		subscriber_number = subscriber_number.get('diabilling:SubscriberID', [''])[0]

		return subscriber_number

	"""
	"""

	def is_signed_in(self):
		response = self.request(
			'POST', 'pre/opGetSubscriberProfileRq', headers=self.get_headers(), json=self.get_content()
		)
		if response is None:
			return False

		response_json = response.json()
		if data := response_json.get('opGetSubscriberProfileRs'):
			user_info_list = [
				data['profile']['firstName'],
				data['profile']['middleName'],
				data['profile']['lastName'],
				f"({data['profile']['phone']})",
			]
			user_info_list = [x for x in user_info_list if x]
			user_info = ' '.join(user_info_list)

			CC = self.logger.special_chars['CC']
			W1 = self.logger.special_chars['W1']

			self.log('\n'.join([
				f"{W1}{user_info}{CC}",
				f"  Sesion Id: {response_json['sessionId']}",
				f"",
			]))

			self.default_subscriber_number = self.get_default_subscriber_number()

			return True

		return False

	def request_otp(self):
		content = {
			'Body': {
				'LoginSendOTPRq': {
					'msisdn': self.msisdn,
				}
			},
		}

		while True:
			response = self.request(
				'POST', 'pre/LoginSendOTPRq', headers=self.get_headers(), json=self.get_content(content)
			)
			if response is None:
				continue

			response_json = response.json()
			if response_json.get('LoginSendOTPRs', {}).get('headerRs', {}).get('responseCode', '') == '00':
				return True

			self.log(f'{response_json}\n')

			return False

	def signin(self):
		CC = self.logger.special_chars['CC']
		R1 = self.logger.special_chars['R1']

		while True:
			self.msisdn = self.input('MSISDN (e.g. 628xx)\n', allow_blank=False)

			if self.request_otp():
				break

		while True:
			otp = self.input('One Time Password (OTP) [blank for cancel]\n').upper()

			if not otp:
				break

			request_id = self.get_request_id()
			request_date = self.get_request_date()

			content = {
				"Body": {
					"Header": {
						"ReqID": request_id,
					},
					"LoginValidateOTPRq": {
						"headerRq": {
							"requestDate": request_date,
							"requestId": request_id,
							"channel": "MYXLPRELOGIN"
						},
						"msisdn": self.msisdn,
						"otp": otp,
					}
				},
			}

			response = self.request('POST', 'pre/LoginValidateOTPRq', loop=True, json=self.get_content(content))

			response_json = response.json()
			if response_json.get('LoginValidateOTPRs', {}).get('responseCode', '') != '00':
				self.log(
					'\n'.join([
						f'{R1}signin(){CC}',
						f'  {response_json}',
						f'',
					]),
					level='CRITICAL',
				)
				continue

			with open(self.real_path('account.json'), 'w', encoding='UTF-8') as file:
				self.msisdn = response_json['LoginValidateOTPRs']['msisdn']
				self.session_id = response_json['sessionId']

				json.dump(
					{
						'msisdn': self.msisdn,
						'session_id': self.session_id
					},
					file,
					indent='\t',
					ensure_ascii=False,
				)

			return True

	def get_package_info(self, payload, status_info):
		service_id = payload['service_id']
		platform = payload['platform']

		CC = self.logger.special_chars['CC']
		W1 = self.logger.special_chars['W1']
		R1 = self.logger.special_chars['R1']

		while True:
			content = {
				'type': 'icon',
				'lang': 'bahasa',
				'ReqID': self.get_request_id(),
				'param': service_id,
				'platform': platform,
				'appVersion': '3.8.2',
				'sourceName': 'Others',
				'msisdn_Type': 'P',
				'screenName': 'home.packages',
				'sessionId': self.session_id,
				'msisdn': self.msisdn,
			}

			response = self.request('POST', 'pre/CMS', headers=self.get_headers(), json=content)
			if response is None:
				return

			response_json = response.json()
			if service_id not in response_json:
				self.log(
					'\n'.join([
						f'{R1}get_package_info(){CC}',
						f'  {response_json}',
						f'',
					]),
					level='CRITICAL',
				)
				continue

			del response_json['gaUser']
			del response_json['sessionId']
			del response_json['timeStamp']

			self.task_success(response_json)

			status_info_list = []
			status_info_list.append(
				f"{W1}{status_info}{CC}"
			)
			status_info_list.append(
				f"  {W1}{response_json[service_id]['package_info']['service_name']}{CC}"
			)

			for info in response_json[service_id]['package_info']['benefit_info']:
				status_info_list.append(
					'    ' + ' '.join([
						f"{info['package_benefits_name']}",
						f"({info['package_benefit_type']})",
						'({}{})'.format(
							f"{info['package_benefit_quota']} " if info['package_benefit_quota'] else '',
							info['package_benefit_unit']
						),
					])
				)

			self.log('\n'.join(status_info_list) + '\n')

			break

	def task(self, event):
		if (event_type := event.get('type')) is not None:
			result = getattr(self, f'task__{event_type}')(event.get('payload'))
			if result is not None and result:
				self._task_success_event_list.append(event)

	def task__buy_package(self, payload):
		msisdn = self.msisdn

		subscriber_number = payload['subscriber_number'] = str(
			payload.get('subscriber_number', self.default_subscriber_number)
		)
		service_id = payload['service_id'] = str(payload.get('service_id', ''))
		price_plan = payload['price_plan'] = str(payload.get('price_plan', '513738114'))
		platform = payload['platform'] = str(payload.get('platform', self.default_platform))

		while True:
			request_id = self.get_request_id()
			transaction_id = self.get_transaction_id()

			content = {
				'Body': {
					'HeaderRequest': {
						'applicationID': '3',
						'applicationSubID': '1',
						'touchpoint': 'MYXL',
						'requestID': request_id,
						'msisdn': msisdn,
						'serviceID': service_id,
					},
					'opPurchase': {
						'msisdn': msisdn,
						'serviceid': service_id,
					},
					'XBOXRequest': {
						'requestName': 'GetSubscriberMenuId',
						'Subscriber_Number': subscriber_number,
						'Source': 'mapps',
						'Trans_ID': transaction_id,
						'Home_POC': 'JK0',
						'PRICE_PLAN': price_plan,
						'PayCat': 'PRE-PAID',
						'Active_End': '20190704',
						'Grace_End': '20190803',
						'Rembal': '0',
						'IMSI': self.imsi,
						'IMEI': self.imei,
						'Shortcode': 'mapps',
					},
					'Header': {
						'ReqID': request_id,
					}
				},
				'packageRegUnreg': 'Reg',
				'packageAmt': '11.900',
				'serviceId': service_id,
				'platform': platform,
			}

			response = self.request(
				'POST', 'pre/opPurchase', headers=self.get_headers(), json=self.get_content(content)
			)
			if response is None:
				continue

			response_json = response.json()
			status = response_json.get('SOAP-ENV:Envelope', {})
			status = status.get('SOAP-ENV:Body', [{}])[0]
			status = status.get('ns0:opPurchaseRs', [{}])[0]
			status = status.get('ns0:Status', [''])[0]

			CC = self.logger.special_chars['CC']
			R1 = self.logger.special_chars['R1']
			Y2 = self.logger.special_chars['Y2']

			status_info = f'{service_id} (sn {subscriber_number}) (pp {price_plan}) (p {platform})'

			if status == 'IN PROGRESS':
				self.get_package_info(payload, status_info)

			elif status == 'DUPLICATE':
				self.log('\n'.join([
					f'{Y2}{status_info}{CC}',
					'  Duplicate',
					'',
				]))

			elif response_json.get('responseCode') in ['04', '21']:
				self.log(
					'\n'.join([
						f"{R1}{status_info}{CC}",
						f"  {response_json['message']}",
						f"",
					]),
					level='DEBUG',
				)

			else:
				self.log(
					'\n'.join([
						f'{R1}{status_info}{CC}',
						f'  {response_json}',
						'',
					]),
					level='CRITICAL',
				)

			if status in ['IN PROGRESS', 'DUPLICATE']:
				return True

			return
