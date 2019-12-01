import os
import sys
import time
import json
import queue
import random
import datetime
import requests
import threading

lock = threading.RLock()
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class myxl(object):
    msisdn = ''
    session_id = ''

    package_queue = queue.Queue()
    package_queue_done = 0
    package_queue_total = 0

    def input_value(self, value, min_length=0):
        try:
            while True:
                result = str(input(value)).strip()
                if (not result and min_length > 0) or (len(result) < min_length):
                    continue
                if result != '':
                    print()
                return result

        except KeyboardInterrupt:
            sys.exit()

    def log(self, value):
        with lock:
            sys.stdout.write('\033[K' + str(value) + '\033[0m' + '\n')
            sys.stdout.flush()

    def log_replace(self, value):
        terminal_columns = os.get_terminal_size()[0]
        value = 'from {} to {} - {}% - {}'.format(self.package_queue_done, self.package_queue_total, self.package_queue_done % self.package_queue_total, value)
        value = value[:terminal_columns-3] + '...' if len(value) > terminal_columns else value

        with lock:
            sys.stdout.write('\033[K' + str(value) + '\033[0m' + '\r')
            sys.stdout.flush()

    def sleep(self, interval):
        while interval:
            self.log_replace(f"Resumming in {interval} seconds")
            interval = interval - 1
            time.sleep(1)

    def request(self, method, target, headers={}, **args):
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'

        while True:
            try:
                response = requests.request(method, target, **args)
            except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as exception:
                self.log(f"Exception:\n\n|   {exception} \n|   Sleeping 10 seconds... \n|\n")
                time.sleep(10)
            else: break

        return response

    def request_id(self):
        return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    def request_date(self):
        return datetime.datetime.now().strftime('%Y%m%d')

    def is_signed_in(self):
        msisdn = self.msisdn
        session_id = self.session_id
        request_id = self.request_id()

        host = 'my.xl.co.id'
        content = {
            "Header": None,
            "Body": {
                "Header": {
                    "ReqID": request_id,
                },
                "opGetSubscriberProfileRq": {
                    "headerRq": {
                        "requestDate": "2019-06-22T20:01:51.065Z",
                        "requestId": request_id,
                        "channel": "MYXLPRE"
                    },
                    "msisdn": msisdn,
                }
            },
            "sessionId": session_id,
            "platform": "04",
            "appVersion": "3.8.2",
            "sourceName": "Firefox",
            "msisdn_Type": "P",
            "screenName": "home.dashboard",
        }
        headers = {
            'Host': host,
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://my.xl.co.id/pre/index1.html',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Content-Length': str(len(str(content))),
            'Accept-Language': 'en-US,id;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Access-Control-Allow-Origin': True,
            'DNT': 1,
        }

        response = self.request('POST', f"https://{host}/pre/opGetSubscriberProfileRq", headers=headers, json=content, timeout=30, verify=False)
        response = json.loads(response.text)

        if 'opGetSubscriberProfileRs' in response:
            data = response['opGetSubscriberProfileRs']

            value = '{}{}{} ({})\n'.format(
                f"{data['profile']['firstName']}",
                f" {data['profile']['middleName']}" if data['profile']['middleName'] else '',
                f" {data['profile']['lastName']}" if data['profile']['lastName'] else '',
                f"{data['profile']['phone']}",
            )
            value += f"  Session Id: {response['sessionId']}" + '\n'

            self.log(value)

            return True

        return False

    def request_otp(self, msisdn):
        while True:
            request_id = self.request_id()

            host = 'myxl.co.id'
            content = {
                "Header": None,
                "Body": {
                    "Header": {
                      "ReqID": request_id,
                    },
                    "LoginSendOTPRq": {
                      "msisdn": msisdn,
                    }
                },
                "sessionId": None,
                "onNet": "False",
                "platform": "04",
                "appVersion": "3.8.2",
                "sourceName": "Firefox",
                "screenName": "login.enterLoginNumber",
            }

            headers = {
                "Host": host,
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://my.xl.co.id/pre/index1.html",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
                "Content-Length": str(len(str(content))),
                "Accept-Language": "en-US,id;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Access-Control-Allow-Origin": 'true',
                "DNT": "1",
            }

            response = requests.request('POST', f"https://{host}/pre/LoginSendOTPRq", headers=headers, json=content, timeout=30, verify=False)
            response = json.loads(response.text)

            if response.get('LoginSendOTPRs', {}).get('headerRs', {}).get('responseCode', '') == '00':
                return True

            self.log(response)

    def signin(self, msisdn, account_file):
        while True:
            if not msisdn or not msisdn.startswith('628'):
                msisdn = self.input_value('MSISDN (e.g. 628xx) \n', min_length=12)

            if self.request_otp(msisdn):
                break

        while True:
            otp = self.input_value('One Time Password (OTP) [blank for cancel] \n').upper()

            if not otp:
                break

            request_id = self.request_id()
            request_date = self.request_date()

            host = 'my.xl.co.id'
            content = {
                "Header": None,
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
                        "msisdn": msisdn,
                        "otp": otp,
                    }
                },
                "sessionId": None,
                "platform": "04",
                "msisdn_Type": "P",
                "appVersion": "3.8.2",
                "sourceName": "Firefox",
                "screenName": "login.enterLoginOTP",
            }

            response = self.request('POST', f"https://{host}/pre/LoginValidateOTPRq", json=content, timeout=30)
            response = json.loads(response.text)

            if response.get('LoginValidateOTPRs', {}).get('responseCode', '') == '00':
                with open(account_file, 'w', encoding='UTF-8') as file:
                    self.msisdn = response['LoginValidateOTPRs']['msisdn']
                    self.session_id = response['sessionId']

                    json.dump({'msisdn': self.msisdn, 'session_id': self.session_id}, file, indent=4, ensure_ascii=False)

                return True

            elif response.get('LoginValidateOTPRs', {}).get('responseCode', '') == '01':
                self.log('Invalid Otp!')

            self.log(response)

    def signout(self, account_file):
        if os.path.exists(account_file):
            os.remove(account_file)

    def get_package_info(self, service_id):
        msisdn = self.msisdn
        session_id = self.session_id

        service_id = str(service_id)
        request_id = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

        host = 'my.xl.co.id'
        content = {
            "type": "icon",
            "param": service_id,
            "lang": "bahasa",
            "platform": "04",
            "ReqID": request_id,
            "appVersion": "3.8.2",
            "sourceName": "Others",
            "msisdn_Type": "P",
            "screenName": "home.packages",
            "sessionId": session_id,
            "msisdn": msisdn,
        }
        headers = {
            'Host': host,
            'Origin': f"https://{host}",
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://my.xl.co.id/pre/index1.html',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Content-Length': str(len(str(content))),
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en,id;q=0.9',
            'Access-Control-Allow-Origin': True,
            'DNT': 1,
        }

        response = self.request('POST', f"https://{host}/pre/CMS", headers=headers, json=content, timeout=30, verify=False)
        response = json.loads(response.text)

        if service_id in response:
            value = f"{response[service_id]['package_info']['service_name']} ({service_id})" + '\n'
            for info in response[service_id]['package_info']['benefit_info']:    
                value += f"  {info['package_benefits_name']}"
                value += f" ({info['package_benefit_type']})"
                value += f" ({info['package_benefit_quota']} {info['package_benefit_unit']})" if info['package_benefit_quota'] or info['package_benefit_unit'] else ''
                value += f" \n"

            self.log(value)

        else:
            self.log(response)


    def buy_package(self, data):
        while True:
            msisdn = self.msisdn
            session_id = self.session_id

            imsi = '510110032177230'
            imei = '3571250436519001'
            trans_id = str(random.randint(100000000000, 999999999999))
            request_id = str(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))

            service_id = str(data['service_id'])
            subscriber_number = str(data['subscriber_number'])

            host = 'my.xl.co.id'
            content = {
                "Header": None,
                "Body": {
                    "HeaderRequest": {
                        "applicationID": "3",
                        "applicationSubID": "1",
                        "touchpoint": "MYXL",
                        "requestID": request_id,
                        "msisdn": msisdn,
                        "serviceID": service_id,
                    },
                    "opPurchase": {
                        "msisdn": msisdn,
                        "serviceid": service_id,
                    },
                    "XBOXRequest": {
                        "requestName": "GetSubscriberMenuId",
                        "Subscriber_Number": subscriber_number,
                        "Source": "mapps",
                        "Trans_ID": trans_id,
                        "Home_POC": "JK0",
                        "PRICE_PLAN": "513738114",
                        "PayCat": "PRE-PAID",
                        "Active_End": "20190704",
                        "Grace_End": "20190803",
                        "Rembal": "0",
                        "IMSI": imsi,
                        "IMEI": imei,
                        "Shortcode": "mapps"
                    },
                    "Header": {
                        "ReqID": request_id,
                    }
                },
                "sessionId": session_id,
                "serviceId": service_id,
                "packageRegUnreg": "Reg",
                "packageAmt": "11.900",
                "platform": "04",
                "appVersion": "3.8.2",
                "sourceName": "Firefox",
                "msisdn_Type": "P",
                "screenName": "home.storeFrontReviewConfirm",
            }
            headers = {
                'Host': host,
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://my.xl.co.id/pre/index1.html',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Content-Length': str(len(str(content))),
                'Accept-Language': 'en-US,id;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Access-Control-Allow-Origin': True,
                'DNT': 1,
            }

            response = self.request('POST', f'https://{host}/pre/opPurchase', headers=headers, json=content, timeout=30, verify=False)
            response = json.loads(response.text)

            status = response.get('SOAP-ENV:Envelope', {}).get('SOAP-ENV:Body', [{}])[0].get('ns0:opPurchaseRs', [{}])[0].get('ns0:Status', [''])[0]

            if status == 'IN PROGRESS':
                self.get_package_info(service_id)

            elif status == 'DUPLICATE':
                self.log(f"Duplicate ({service_id}) ({subscriber_number}) \n  Sleeping 120 seconds... \n")
                self.sleep(120)
                continue

            elif response.get('responseCode') == '04':
                pass

            else:
                self.log(f"{service_id:.<12} {response}")


            self.package_queue_done += 1
            break

    def buy_packages(self, service_id_range, subscriber_number_range, threads=32):
        def task():
            while True:
                data = self.package_queue.get()
                self.log_replace(f"Sending {data['service_id']} ({data['subscriber_number']})")
                self.buy_package(data)
                self.log_replace(f"Sending {data['service_id']} ({data['subscriber_number']})")
                self.package_queue.task_done()

        for subscriber_number in range(int(subscriber_number_range[0]), int(subscriber_number_range[1]) + 1):
            for service_id in range(int(service_id_range[0]), int(service_id_range[1]) + 1):
                self.package_queue.put({
                    'service_id': str(service_id),
                    'subscriber_number': str(subscriber_number) + '00',
                })

        self.package_queue_total = self.package_queue.qsize()

        for i in range(threads if threads > self.package_queue_total else self.package_queue_total):
            thread = threading.Thread(target=task)
            thread.daemon = True
            thread.start()

        self.package_queue.join()
