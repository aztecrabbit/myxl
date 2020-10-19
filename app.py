import argparse
import json
import os
import sys

from myxl import MyXL


def real_path(filename):
	return os.path.dirname(os.path.abspath(sys.argv[0])) + '/' + filename


def range_string(value):
	data_range = [int(x) for x in value.split('-') if x]
	data_range = list(set(data_range))
	data_range.sort()

	if not data_range:
		return []

	if len(data_range) == 1:
		data_range.append(data_range[0])

	data_range[1] += 1
	data_range = data_range[:2]

	return range(*data_range)


def get_account():
	account_file = real_path('account.json')

	while True:
		try:
			if not os.path.exists(account_file):
				with open(account_file, 'w') as file:
					json.dump({'msisdn': '', 'session_id': ''}, file, indent='\t')
			with open(account_file) as file:
				return json.load(file)
		except json.decoder.JSONDecodeError:
			os.remove(account_file)


def get_arguments():
	parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=52))
	parser.add_argument(
		'--verbose',
		help='increase output verbosity',
		dest='verbose',
		action='store_true',
	)
	parser.add_argument(
		'--buy',
		help='--buy 8210000-8219999',
		dest='service_id_range',
		type=str,
		required=True,
	)
	parser.add_argument(
		'--price-plan',
		help='--price-plan 513738114',
		dest='price_plan_range',
		type=str,
		default='513738114',
	)
	parser.add_argument(
		'--subscriber-number',
		help='--subscriber-number 1219456xxx',
		dest='subscriber_number_range',
		type=str,
	)
	parser.add_argument(
		'--platform',
		help='--platform 4',
		dest='platform_range',
		type=str,
	)
	parser.add_argument(
		'--threads',
		help='--threads 8',
		dest='threads',
		type=int,
		default=8,
	)

	return parser.parse_args()


def main():
	arguments = get_arguments()
	account = get_account()

	myxl = MyXL(threads=arguments.threads, verbose=arguments.verbose)
	myxl.msisdn = account.get('msisdn')
	myxl.session_id = account.get('session_id')
	myxl.start_threads()

	try:
		while True:
			if myxl.is_signed_in():
				break
			myxl.signin()

		for service_id in range_string(arguments.service_id_range):
			for subscriber_number in range_string(arguments.subscriber_number_range or myxl.default_subscriber_number):
				for price_plan in range_string(arguments.price_plan_range or myxl.default_priceplan):
					for platform in range_string(arguments.platform_range or myxl.default_platform):
						myxl.add_task({
							'type': 'buy_package',
							'payload': {
								'subscriber_number': subscriber_number,
								'service_id': service_id,
								'price_plan': price_plan,
								'platform': f'{platform:0>2}',
							}
						})

		myxl.join()
	except KeyboardInterrupt:
		myxl.keyboard_interrupt()
	finally:
		myxl.complete()


if __name__ == '__main__':
	main()
