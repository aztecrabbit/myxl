import os
import sys
import src
import json
import argparse


def realpath(file):
    return os.path.dirname(os.path.abspath(__file__)) + file


def main():
    parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=52))
    parser.add_argument('--verbose', help='increase output verbosity', dest='verbose', action='store_true')
    parser.add_argument('--signin', help='--signin 628xx', dest='msisdn', type=str)
    parser.add_argument('--buy', help='--buy 8210000-8219999', dest='service_id_range', type=str)
    parser.add_argument('--sub', help='--sub 20647200-20647299', dest='subscriber_number_range', type=str)
    parser.add_argument('--sub-file', help='--sub-file', dest='subscriber_number_file', action='store_true')
    parser.add_argument('--platform', help='--platform 1,2,3,4', dest='platform', type=str)
    parser.add_argument('--platform-range', help='--platform-range 1-4', dest='platform_range', type=str)
    parser.add_argument('--threads', help='--threads 32', dest='threads', type=int)
    parser.add_argument('--silent', help='--silent', dest='silent', action='store_true')
    parser.add_argument('--signout', help='--signout', dest='signout', action='store_true')

    arguments = parser.parse_args()
    arguments.threads = arguments.threads if arguments.threads else 16
    arguments.service_id_range = arguments.service_id_range.split('-') if arguments.service_id_range else []
    arguments.subscriber_number_range = arguments.subscriber_number_range.split('-') if arguments.subscriber_number_range else [20647244]

    arguments.platform = arguments.platform.split(',') if arguments.platform else ['2']
    arguments.platform_range = arguments.platform_range.split('-') if arguments.platform_range else []

    if not os.path.exists(realpath('/account.json')):
        with open(realpath(f"/account.json"), 'w', encoding='UTF-8') as file:
            json.dump({'msisdn': '', 'session_id': ''}, file, indent=4, ensure_ascii=False)

    try:
        account = json.loads(open(realpath('/account.json')).read())

        myxl = src.myxl()
        myxl.verbose = arguments.verbose
        myxl.silent = arguments.silent
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

            service_id_list = []
            subscriber_number_list = []

            for service_id in range(int(service_id_range[0]), int(service_id_range[1]) + 1):
                service_id_list.append(service_id)

            for subscriber_number in range(int(subscriber_number_range[0]), int(subscriber_number_range[1]) + 1):
                subscriber_number_list.append(f"{subscriber_number:0<10}")

            if arguments.subscriber_number_file:
                if os.path.exists(realpath('/storage/subscriber_number.txt')):
                    subscriber_number_list = open(realpath('/storage/subscriber_number.txt')).readlines()
                    subscriber_number_list = [x.strip() for x in subscriber_number_list if x.strip()]
                    subscriber_number_list.sort()

                else:
                    myxl.log(f"File {realpath('/storage/subscriber_number.txt')} not exists, using default subscriber number")

            platform_list = [int(x.strip()) for x in arguments.platform if x.strip()]
            if len(arguments.platform_range) == 2:
                for platform in range(int(arguments.platform_range[0]), int(arguments.platform_range[1]) + 1):
                    if not platform:
                        continue
                    platform_list.append(platform)
            platform_list = list(set(platform_list))

            myxl.buy_packages(service_id_list, subscriber_number_list, platform_list, threads=arguments.threads)

    except KeyboardInterrupt:
        myxl.stop()
        sys.stdout.write('\r' + '\033[K' + '\033[31;1m' + 'Keyboard Interrupted \n' + '\033[0m' + '  Ctrl-C again if not exiting automaticly \n  Please wait... \n\n')
        sys.stdout.flush()
    finally:
        myxl.update_file(realpath('/storage/database.txt'))
        myxl.update_file(realpath('/storage/service_id.txt'))
        myxl.update_file(realpath('/storage/service_id_info.txt'))
        myxl.update_file(realpath('/storage/subscriber_number.txt'))


if __name__ == '__main__':
    main()
