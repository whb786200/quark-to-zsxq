import requests
import json

with open('config/settings.json', 'r') as f:
    config = json.load(f)

cookie = config['quark_cookie']
headers = {
    'Cookie': cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://pan.quark.cn/',
}
params = {
    '_input_charset': 'utf-8',
    '_output_charset': 'utf-8',
    '_input_enc': 'UTF-8',
    '_output_enc': 'UTF-8',
    'pdir_fid': '0',
    '_page': '1',
    '_size': '20',
    '_fetch_total': '1',
    '_fetch_sub_dirs': '0',
    '_sort': 'file_type:asc,file_name:asc',
    'pr': 'ucpro',
    'fr': 'pc',
}

resp = requests.get('https://drive-pc.quark.cn/1/clouddrive/file/sort', headers=headers, params=params, timeout=15)
result = resp.json()
print('Code:', result.get('code'))
print('Message:', result.get('message'))
if result.get('code') == 0:
    data = result.get('data', {})
    print('Total files:', data.get('metadata', {}).get('_total'))
    for f in data.get('list', [])[:5]:
        print('  ', f.get('file_type', ''), '-', f.get('file_name', '')[:40])
else:
    print('Full result:', json.dumps(result, ensure_ascii=False)[:500])
