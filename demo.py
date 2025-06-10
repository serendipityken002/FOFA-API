import requests
import base64
import os
from dotenv import load_dotenv
import json

load_dotenv()  # 加载.env文件

# 构建Fofa API请求
def fofa_search(query):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'host,title,header,product',
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}
    
# 构建Fofa API统计请求
def fofa_stats(query):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/stats"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'fid,icp,server,title'
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

# 示例查询
if __name__ == "__main__":
    query = 'body="js/validator.js" && body="js/mootools.js" && title="IDC/ISP"'
    # result = fofa_search(query)
    result = fofa_stats(query)
    # result = fofa_host('122.114.56.64')
    print(json.dumps(result, ensure_ascii=False, indent=2))