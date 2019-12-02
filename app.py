import os
import sys
import src
import json
import argparse

def realpath(file):
    return os.path.dirname(os.path.abspath(__file__)) + file

def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=52))
    parser.add_argument('--verbose', help='increase output verbosity', dest='verbose', action='store_true')
    parser.add_argument('--signin', help='--signin 628xx', dest='msisdn', type=str)
    parser.add_argument('--buy', help='--buy 8210000-8219999', dest='service_id_range', type=str)
    parser.add_argument('--sub', help='--sub 20647200-20647299', dest='subscriber_number_range', type=str)
    parser.add_argument('--threads', help='--threads 32', dest='threads', type=int)
    parser.add_argument('--signout', help='--signout', dest='signout', action='store_true')

    arguments = parser.parse_args()
    arguments.threads = arguments.threads if arguments.threads else 32
    arguments.service_id_range = arguments.service_id_range.split('-') if arguments.service_id_range else []
    arguments.subscriber_number_range = arguments.subscriber_number_range.split('-') if arguments.subscriber_number_range else [20647244]

    if not os.path.exists(realpath('/account.json')):
        with open(realpath(f"/account.json"), 'w', encoding='UTF-8') as file:
            json.dump({'msisdn': '', 'session_id': ''}, file, indent=4, ensure_ascii=False)

    try:
        account = json.loads(open(realpath('/account.json')).read())

        myxl = src.myxl()
        myxl.msisdn = account['msisdn']
        myxl.session_id = account['session_id']

        if arguments.signout:
            myxl.signout(realpath('/account.json'))
            return

        if arguments.msisdn:
            myxl.signin(arguments.msisdn, account_file=realpath('/account.json'))

        while not myxl.is_signed_in():
            myxl.signin(arguments.msisdn, account_file=realpath('/account.json'))

        if arguments.service_id_range:    
            service_id_range = []
            service_id_range.append(arguments.service_id_range[0])
            service_id_range.append(arguments.service_id_range[1] if len(arguments.service_id_range) >= 2 and int(arguments.service_id_range[1]) >= int(arguments.service_id_range[0]) else service_id_range[0])

            subscriber_number_range = []
            subscriber_number_range.append(arguments.subscriber_number_range[0])
            subscriber_number_range.append(arguments.subscriber_number_range[1] if len(arguments.subscriber_number_range) >= 2 and int(arguments.subscriber_number_range[1]) >= int(arguments.subscriber_number_range[0]) else subscriber_number_range[0])

            myxl.buy_packages(service_id_range, subscriber_number_range, threads=arguments.threads)

    except KeyboardInterrupt:
        myxl.stop()
        sys.stdout.write('\r' + '\033[K' + '\033[31;1m' + 'Keyboard Interrupted \n' + '\033[0m' + '  Ctrl-C again if not exiting automaticly \n  Please wait... \n\n')
        sys.stdout.flush()

if __name__ == '__main__':
    main()
