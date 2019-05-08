import requests
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

elk_host = '192.168.100.100:9200'

def send_json2elk(json_obj, elk_index, obj_type, id):
    url = '/'.join(['http://' + elk_host, elk_index, obj_type, id])
    print('Pushing to {}'.format(url))
    r = requests.post(url, data = json_obj)
    print r.status_code
    return r.status_code
