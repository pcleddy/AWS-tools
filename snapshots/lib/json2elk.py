import requests
import json
import pprint
pp = pprint.PrettyPrinter(indent=4)

m_elk_host = '192.168.100.100:9200'

def send_json2elk(m_json_obj, m_elk_index, m_obj_type, m_id):
    m_url = '/'.join(['http://' + m_elk_host, m_elk_index, m_obj_type, m_id])
    print('Pushing to {}'.format(m_url))
    r = requests.post(m_url, data = m_json_obj)
    print r.status_code
    return r.status_code
