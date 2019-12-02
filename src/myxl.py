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
    loop = True
    imei = '3571250436519001'
    imsi = '510110032177230'
    msisdn = ''
    session_id = ''

    package_queue = queue.Queue()
    package_queue_done = 0
    package_queue_total = 1

    def stop(self):
        self.loop = False

    def realpath(self, file):
        return os.path.dirname(os.path.abspath(__file__)) + file

    def save_file(self, filename, value):
        with lock:
            if not self.loop:
                return
            with open(filename, 'a+') as file:
                file.write(str(value) + '\n')

    def update_file(self, filename):
        if not os.path.exists(filename):
            return

        with lock:
            lines = open(filename).readlines()
            lines = list(set([x.strip() for x in lines if x]))
            lines.sort()

            with open(filename, 'w') as file:
                for line in lines:
                    file.write(str(line) + '\n')

    def input_value(self, value, min_length=0):
        try:
            while self.loop:
                result = str(input('\033[K' + str(value))).strip()
                if (not result and min_length > 0) or (len(result) < min_length):
                    continue
                if result != '':
                    print()
                return result

        except KeyboardInterrupt:
            sys.exit()

    def log(self, value):
        with lock:
            if not self.loop:
                return
            sys.stdout.write('\033[K' + str(value) + '\033[0m' + '\n')
            sys.stdout.flush()

    def log_replace(self, value):
        terminal_columns = os.get_terminal_size()[0]
        value = 'from {} to {} - {:.1f}% - {}'.format(self.package_queue_done, self.package_queue_total, (self.package_queue_done / self.package_queue_total) * 100, value)
        value = value[:terminal_columns-3] + '...' if len(value) > terminal_columns else value

        with lock:
            if not self.loop:
                return
            sys.stdout.write('\033[K' + str(value) + '\033[0m' + '\r')
            sys.stdout.flush()

    def sleep(self, interval, value=''):
        while interval and self.loop:
            self.log_replace('{:0>3} - {}'.format(interval, value))
            interval = interval - 1
            time.sleep(1)

        self.log_replace('{:0>3} - {}'.format(interval, value))

    def request(self, method, target, headers={}, **args):
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'

        while True:
            try:
                self.log_replace(f"Req - {target}")
                response = requests.request(method, target, headers=headers, **args)
            except requests.exceptions.ConnectionError:
                self.sleep(15, f"{target} (Connection Error)")
            except requests.exceptions.ReadTimeout:
                self.sleep(10, f"{target} (Read Timeout)")
            else: break

        return response

    def request_response_decode(self, text):
        try:
            data = {}
            data = json.loads(text)
        except json.decoder.JSONDecodeError:
            sys.stdout.write('\r' + '\033[K' + '\033[31;1m' + 'JSON Decode Error \033[0m \n' + f"  {text} \033[0m \n\n")
            sys.stdout.flush()

        return data

    def request_id(self):
        return datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    def request_date(self):
        return datetime.datetime.now().strftime('%Y%m%d')

    def transaction_id(self):
        return str(random.randint(100000000000, 999999999999))

    def is_signed_in(self):
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
                    "msisdn": self.msisdn,
                }
            },
            "sessionId": self.session_id,
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
            'Access-Control-Allow-Origin': 'True',
            'DNT': '1',
        }

        response = self.request('POST', f"https://{host}/pre/opGetSubscriberProfileRq", headers=headers, json=content, timeout=30, verify=False)
        response = self.request_response_decode(response.text)

        if 'opGetSubscriberProfileRs' in response:
            data = response['opGetSubscriberProfileRs']

            value = '\033[1m{}{}{} ({}) \033[0m \n'.format(
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
        while self.loop:
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
                "Access-Control-Allow-Origin": 'True',
                "DNT": "1",
            }

            response = self.request('POST', f"https://{host}/pre/LoginSendOTPRq", headers=headers, json=content, timeout=30, verify=False)
            response = self.request_response_decode(response.text)

            if response.get('LoginSendOTPRs', {}).get('headerRs', {}).get('responseCode', '') == '00':
                return True

            self.log(f"{response} \n")

    def signin(self, msisdn, account_file):
        while self.loop:
            if not msisdn or not msisdn.startswith('628'):
                msisdn = self.input_value('MSISDN (e.g. 628xx) \n', min_length=12)

            if self.request_otp(msisdn):
                break

        while self.loop:
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
            response = self.request_response_decode(response.text)

            if response.get('LoginValidateOTPRs', {}).get('responseCode', '') == '00':
                with open(account_file, 'w', encoding='UTF-8') as file:
                    self.msisdn = response['LoginValidateOTPRs']['msisdn']
                    self.session_id = response['sessionId']

                    json.dump({'msisdn': self.msisdn, 'session_id': self.session_id}, file, indent=4, ensure_ascii=False)

                return True

            self.log(f"Response Error ({msisdn}) \n  {response} \n")

    def signout(self, account_file):
        if os.path.exists(account_file):
            os.remove(account_file)

    def get_package_info(self, data):
        service_id = data['service_id']
        subscriber_number = data['subscriber_number']

        request_id = self.request_id()

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
            "sessionId": self.session_id,
            "msisdn": self.msisdn,
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
            'Access-Control-Allow-Origin': 'True',
            'DNT': '1',
        }

        response = self.request('POST', f"https://{host}/pre/CMS", headers=headers, json=content, timeout=30, verify=False)
        response = self.request_response_decode(response.text)

        if service_id in response:

            del response['gaUser']
            del response['sessionId']
            del response['timeStamp']

            self.save_file(self.realpath('/../storage/service_id_info.txt'), json.dumps(response))

            value = '\033[1m' + f"{response[service_id]['package_info']['service_name']} ({service_id}) ({subscriber_number})" + '\033[0m' + '\n'
            for info in response[service_id]['package_info']['benefit_info']:
                value += f"  {info['package_benefits_name']}"
                value += f" ({info['package_benefit_type']})"
                value += ' ({}{})'.format(f"{info['package_benefit_quota']} " if info['package_benefit_quota'] else '', info['package_benefit_unit'])
                value += ' \n'

            self.log(value)

        else:
            self.log(f"Response Error ({service_id}) ({subscriber_number}) \n  {response} \n")


    def buy_package(self, data):
        while self.loop:
            request_id = self.request_id()
            transaction_id = self.transaction_id()

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
                        "msisdn": self.msisdn,
                        "serviceID": service_id,
                    },
                    "opPurchase": {
                        "msisdn": self.msisdn,
                        "serviceid": service_id,
                    },
                    "XBOXRequest": {
                        "requestName": "GetSubscriberMenuId",
                        "Subscriber_Number": subscriber_number,
                        "Source": "mapps",
                        "Trans_ID": transaction_id,
                        "Home_POC": "JK0",
                        "PRICE_PLAN": "513738114",
                        "PayCat": "PRE-PAID",
                        "Active_End": "20190704",
                        "Grace_End": "20190803",
                        "Rembal": "0",
                        "IMSI": self.imsi,
                        "IMEI": self.imei,
                        "Shortcode": "mapps"
                    },
                    "Header": {
                        "ReqID": request_id,
                    }
                },
                "sessionId": self.session_id,
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
                'Access-Control-Allow-Origin': 'True',
                'DNT': '1',
            }

            response = self.request('POST', f'https://{host}/pre/opPurchase', headers=headers, json=content, timeout=30, verify=False)
            response = self.request_response_decode(response.text)

            status = response.get('SOAP-ENV:Envelope', {}).get('SOAP-ENV:Body', [{}])[0].get('ns0:opPurchaseRs', [{}])[0].get('ns0:Status', [''])[0]

            if status in ['IN PROGRESS', 'DUPLICATE']:
                self.save_file(self.realpath('/../storage/service_id.txt'), data['service_id'])
                self.save_file(self.realpath('/../storage/subscriber_number.txt'), data['subscriber_number'])

            if status == 'IN PROGRESS':
                self.get_package_info(data)

            elif status == 'DUPLICATE':
                self.log(f"\033[33;2mDuplicate ({service_id}) ({subscriber_number}) \033[0m \n  Request to this package stopped \n")

            elif response.get('responseCode') == '04':
                pass

            else:
                self.log(f"Response Error ({service_id}) ({subscriber_number}) \n  {response} \n")

            self.package_queue_done += 1
            break

    def buy_packages(self, service_id_range, subscriber_number_range, threads=32):
        def task():
            while self.loop:
                data = self.package_queue.get()
                self.buy_package(data)
                self.log_replace(f"Rcv - {data['service_id']} ({data['subscriber_number']})")
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
