# 尝试随机提取部分特征，将其进行聚类。实现一个产品在一块，不同产品不在一块。
# author：chenken

import requests
import base64
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()  # 加载.env文件

def fofa_search(query):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'banner',
        "size": 1000,  # 每次查询返回的结果数量
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

def save_to_file(result, query):
    # Extract the app name from the query for a cleaner filename
    app_name = query.split('app=')[1].split('"')[1] if 'app=' in query else 'query'
    filename = f"check/fofa_result_{app_name}.json"
    
    # Save the result to a file
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result['results'], f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {filename}")

if __name__ == "__main__":
    # 示例查询1
    query = 'app="ZTE-路由器" && type="service"'
    result = fofa_search(query)
    save_to_file(result, query)
    
    time.sleep(1)

    # 示例查询2
    query = 'app="RICOH-Network-Printer" && type="service"'
    result = fofa_search(query)
    save_to_file(result, query)
