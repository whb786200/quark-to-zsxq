import requests
import json
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('config/settings.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

cookie = config['quark_cookie']
headers = {
    'Cookie': cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://pan.quark.cn/',
}

FOLDER_ID = 'f19a6bf448314938bf91b308fc4722bb'
ZSXQ_GROUP_ID = config.get('zsxq_group_id', '20629403')

def get_file_list(folder_id, page=1):
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

def create_share(file_id, title):
    url = 'https://drive-pc.quark.cn/1/clouddrive/share'
    params = {
        '_input_charset': 'utf-8',
        '_output_charset': 'utf-8',
    }
    data = {
        'fid_list': [file_id],
        'title': title,
        'url_type': 1,
        'expired_type': 1,
        'expire_time': 0,
    }
    headers_post = headers.copy()
    headers_post['Content-Type'] = 'application/json'
    
    try:
        resp = requests.post(url, headers=headers_post, params=params, json=data, timeout=30)
        result = resp.json()
        
        if result.get('code') != 0:
            return None, result.get('message', 'Unknown error')
        
        # 获取share_id
        task_sync = result.get('data', {}).get('task_sync')
        if task_sync:
            share_id = result.get('data', {}).get('task_resp', {}).get('data', {}).get('share_id')
        else:
            task_id = result.get('data', {}).get('task_id')
            if task_id:
                share_id = poll_async_task(task_id)
            else:
                return None, 'No task_id or sync result'
        
        if not share_id:
            return None, 'No share_id'
        
        # 获取分享URL
        share_info = get_share_url(share_id)
        return share_info, None
        
    except Exception as e:
        return None, str(e)

def poll_async_task(task_id, max_retries=20):
    url = 'https://drive-pc.quark.cn/1/clouddrive/share/task'
    params = {
        '_input_charset': 'utf-8',
        '_output_charset': 'utf-8',
        'task_id': task_id,
    }
    for i in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get('code') == 0:
                data = result.get('data', {})
                if data.get('status') in ('completed', 'done'):
                    return data.get('share_id') or data.get('data', {}).get('share_id')
            time.sleep(1.5)
        except:
            time.sleep(1.5)
    return None

def get_share_url(share_id):
    url = 'https://drive-pc.quark.cn/1/clouddrive/share/password'
    params = {
        '_input_charset': 'utf-8',
        '_output_charset': 'utf-8',
    }
    data = {'share_id': share_id}
    headers_post = headers.copy()
    headers_post['Content-Type'] = 'application/json'
    
    try:
        resp = requests.post(url, headers=headers_post, params=params, json=data, timeout=15)
        result = resp.json()
        if result.get('code') == 0:
            return result.get('data', {})
    except:
        pass
    return {}

# === 主流程 ===
print('=' * 60)
print('扫描文件夹: 自发群')
print('=' * 60)

files = get_file_list(FOLDER_ID)
if not files:
    print('文件夹为空或无法访问')
else:
    print(f'共发现 {len(files)} 个文件:')
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
        print(f'{ftype:<7} {fname:<40} {size_str:<10}')

    print('-' * 70)
    print()
    
    # 批量创建分享
    print('=' * 60)
    print('开始批量创建分享链接...')
    print('=' * 60)
    
    results = []
    for i, f in enumerate(files):
        if f.get('file_type') == 'folder':
            continue  # 跳过文件夹
        
        fname = f.get('file_name', '')
        fid = f.get('fid', '')
        
        print(f'\n[{i+1}/{len(files)}] 分享: {fname}')
        share_info, error = create_share(fid, fname)
        
        if share_info and share_info.get('share_url'):
            share_url = share_info.get('share_url', '')
            share_pwd = share_info.get('share_pwd', '')
            print(f'  成功! URL: {share_url}')
            if share_pwd:
                print(f'  密码: {share_pwd}')
            results.append({
                'title': fname,
                'share_url': share_url,
                'share_pwd': share_pwd,
                'success': True
            })
        else:
            print(f'  失败: {error}')
            results.append({
                'title': fname,
                'success': False,
                'error': error
            })
        
        time.sleep(1.5)
    
    # 汇总
    print('\n' + '=' * 60)
    print('汇总结果')
    print('=' * 60)
    success_count = sum(1 for r in results if r.get('success'))
    print(f'分享成功: {success_count}/{len(results)}')
    for r in results:
        if r.get('success'):
            print(f'  [OK] {r["title"]}: {r["share_url"]}')
        else:
            print(f'  [FAIL] {r["title"]}: {r.get("error", "Unknown")}')
    
    # 保存结果
    with open('share_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n结果已保存到 share_results.json')
