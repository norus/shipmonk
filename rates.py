#!/usr/bin/env python
import yaml
import json
import argparse
import requests
from pyzipcode import ZipCodeDatabase
import pandas as pd

class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r

class Shipmonk:
    def __init__(self, config=None):
        cfg = yaml.load(open(config, 'r'), Loader=yaml.FullLoader)
        self.bearer = cfg['config']['token']
        self.rates_url = 'https://app.shipmonk.com/api/v1/calculate-rates/bundles'
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            'authority': 'app.shipmonk.com',
            'accept': 'application/json',
            'origin': 'https://app.shipmonk.com',
            'Content-Type': 'application/json'
        }
        #self.json_data = '{"height":1.38,"length":7.87,"type":"residential","shipTo":{"country":"US","state":"NY","postalCode":"11101","residential":true},"weight":0.1,"width":3.54,"carrier":3}'


    def get_rates(self, params):
        res = requests.post(self.rates_url, data=params, auth=BearerAuth(self.bearer), headers=self.headers)
        return res.text


    def translate_carrier(self, carrier_name):
        carrier_name = carrier_name.lower()
        carriers = {
            'fedex': 3,
            'dhl': 5,
            'usps': 6,
            'ups': 8
        }
        return carriers[carrier_name]


    def print_rates(self, json_data):
        rates = json_data['data']['rates']
        #print(rates)
        return sorted(rates, key=lambda k: k['cost'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to get shipping rates')
    parser.add_argument('--config', help='Yaml config')
    parser.add_argument('--carrier')
    parser.add_argument('--height')
    parser.add_argument('--length')
    parser.add_argument('--width')
    parser.add_argument('--weight')
    parser.add_argument('--type')
    parser.add_argument('--country')
    parser.add_argument('--zip')

    args = parser.parse_args()

    if args.config:
        sm = Shipmonk(config=args.config)
        payload = {
            'height': args.height,
            'length':args.length,
            'width':args.width,
            'weight':args.weight,
            'type':args.type,
            'carrier':sm.translate_carrier(args.carrier),
            'shipTo': {
                'country':args.country,
                'postalCode':args.zip,
                'residential': True if args.type == 'residential' else False
            }
        }

        # UPS requires state
        if args.carrier == 'ups':
            zcdb = ZipCodeDatabase()
            zip_to_state = zcdb[int(args.zip)].state
            payload['shipTo'].update({'state': zip_to_state})

        live_rates = sm.get_rates(json.dumps(payload))
        rates = (sm.print_rates(json.loads(live_rates)))
        res = []
        [res.append(i) for i in list(filter(lambda name: name['warehouse']['name'] == 'California', rates))]
        df = pd.DataFrame({'Carrier': [i['service'] for i in res], 'Delivery': [i['delivery_time'] for i in res], 'Cost': [i['cost'] for i in res]})
        print(df)
    else:
        parser.print_help()
