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

def get_file_list(folder_id='0', page=1):
    params = {
        '_input_charset': 'utf-8',
        '_output_charset': 'utf-8',
        '_input_enc': 'UTF-8',
        '_output_enc': 'UTF-8',
        'pdir_fid': folder_id,
        '_page': str(page),
        '_size': '50',
        '_fetch_total': '1',
        '_fetch_sub_dirs': '0',
        '_sort': 'file_type:asc,file_name:asc',
        'pr': 'ucpro',
        'fr': 'pc',
    }
    resp = requests.get('https://drive-pc.quark.cn/1/clouddrive/file/sort', headers=headers, params=params, timeout=15)
    result = resp.json()
    if result.get('code') == 0:
        return result.get('data', {}).get('list', [])
    return []

# 获取根目录
files = get_file_list('0')
print('根目录文件/文件夹:')
print('-' * 70)
for f in files:
    ftype = '[DIR]' if f.get('file_type') == 'folder' else '[FILE]'
    fname = f.get('file_name', '')
    size = f.get('size', 0)
    fid = f.get('fid', '')
    if size > 1024*1024:
        size_str = f'{size/1024/1024:.1f}MB'
    elif size > 1024:
        size_str = f'{size//1024}KB'
    else:
        size_str = f'{size}B'
    print(f'{ftype:<7} {fname:<35} {size_str:<10} fid={fid}')

print('-' * 70)
print(f'共 {len(files)} 个项目')
