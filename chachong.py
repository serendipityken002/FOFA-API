import requests
import base64
import os
from dotenv import load_dotenv
import time

load_dotenv()  # 加载.env文件

def fofa_stats(query, fields='product1,product5,category1,category5'):
    """
    构建Fofa API统计请求
    """
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/stats"
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
    
def get_top_product(json_data):
    """
    从json数据中获取排名最高的产品名称及其数量
    """
    if 'aggs' in json_data and len(json_data['aggs']) > 0:
        product_name = json_data['aggs']['product'][0]['name']  # 最多的产品名称
        product_count = json_data['aggs']['product'][0]['count']  # 最多的产品数量
        return product_name, product_count
    else:
        return None, None
    
def get_size(json_data):
    """
    获取查询结果的总数量
    """
    if 'size' in json_data:
        return json_data['size']
    return 0

def is_duplicate1(json_data):
    """
    正向查重：
    计算排名最高的产品数量占总数量的比例
    """
    total_count = get_size(json_data)
    product_name, product_count = get_top_product(json_data)
    if total_count > 0:
        ratio = product_count / total_count
        return ratio, product_count, total_count
    return 0

def is_duplicate2(json_data):
    """
    反向查重：
    计算新规则的产品数量占现有规则总数量的比例
    """
    product_name, product_count = get_top_product(json_data)
    query = f'app="{product_name}"'
    new_json_data = fofa_stats(query)
    total_count = get_size(new_json_data)
    new_count = get_size(json_data)
    if total_count > 0:
        ratio = new_count / total_count
        return ratio, new_count, total_count
    return 0

# 示例查询
if __name__ == "__main__":
    query = 'body="js/validator.js" && body="js/mootools.js" && title="IDC/ISP"'
    json_data = fofa_stats(query)
    res = is_duplicate1(json_data)
    time.sleep(5)  # 避免请求过快
    res2 = is_duplicate2(json_data)
    print(res)
    print(res2)