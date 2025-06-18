import requests
import base64
import os
from dotenv import load_dotenv
import json

load_dotenv()  # 加载.env文件

# 构建Fofa API请求
def fofa_search(query, fields='banner'):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': fields,
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}
    
# 构建Fofa API统计请求
def fofa_stats(query: str, fields: str = 'product1,product5,category1,category5'):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/stats"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'product1,product5,category1,category5',
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

# 构建FOFA API的Host请求
def fofa_host(host):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/host/{host}"
    params = {
        'email': email,
        'key': key,
    }
    url = base_url.format(host=host)
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

# 构建流式查询
def fofa_stream(query):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/stream/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'host,title,header,product',
        'size': 100,  # 设置每次请求的结果数量
    }
    response = requests.get(base_url, params=params, stream=True)
    
    if response.status_code == 200:
        return response.iter_lines()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

# 查询规则标签
def fofa_tags():
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/rule_tags/query"
    params = {
        'email': email,
        'key': key,
        'value': '网络摄像头',
        'field': 'title',
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

# 示例查询
if __name__ == "__main__":
    # query = 'body="js/validator.js" && body="js/mootools.js" && title="IDC/ISP"'
    query = 'banner="KX IV-101"'
    # query = 'body="Aterm WG1200HS3" && title="NEC クイック設定Web | Aterm"'
    result = fofa_search(query)
    # result = fofa_stats(query)
    # result = fofa_host('122.114.56.64')

    # result = fofa_stream(query)
    # for line in result:
    #     if line:  # 确保行不为空
    #         print(line.decode('utf-8'))  # 解码并打印每一行

    # result = fofa_tags()
    print(json.dumps(result, ensure_ascii=False, indent=2))