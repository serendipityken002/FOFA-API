import requests
import base64
import os
from dotenv import load_dotenv
import time

from API import fofa_stats

load_dotenv()  # 加载.env文件

# def fofa_stats(query: str, fields: str = 'product1,product5,category1,category5'):
#     """
#     构建Fofa API统计请求
    
#     Args:
#         query: FOFA查询语句
#         fields: 需要返回的字段
        
#     Returns:
#         API返回的JSON数据
#     """
#     email = os.getenv('FOFA_EMAIL')
#     key = os.getenv('FOFA_KEY')
    
#     if not email or not key:
#         return {"error": "FOFA credentials not found in environment variables"}
    
#     base_url = "https://fofa.info/api/v1/search/stats"
#     params = {
#         'email': email,
#         'key': key,
#         'qbase64': base64.b64encode(query.encode()).decode(),
#         'fields': fields,
#     }
    
#     try:
#         response = requests.get(base_url, params=params)
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         return {"error": f"Request failed: {str(e)}"}
    
def get_top_product(json_data):
    """
    从json数据中获取排名最高的产品名称及其数量
    
    Args:
        json_data: FOFA API返回的JSON数据
        
    Returns:
        (产品名称, 产品数量)的元组，如果无数据则返回(None, None)
    """
    if ('aggs' in json_data and json_data.get('aggs') and 
        'product' in json_data['aggs'] and json_data['aggs']['product']):
        product_data = json_data['aggs']['product'][0]
        product_name = product_data.get('name')
        product_count = product_data.get('count')
        return product_name, product_count
    return None, None
    
def get_size(json_data) -> int:
    """
    获取查询结果的总数量
    
    Args:
        json_data: FOFA API返回的JSON数据
        
    Returns:
        查询结果的总数量
    """
    return json_data.get('size', 0)

def check_duplicate(json_data, direction: str = "forward", 
                   forward_threshold: float = 0.8, reverse_threshold: float = 0.5):
    """
    综合查重函数，支持正向和反向查重
    
    Args:
        json_data: 原始查询的FOFA API返回数据
        direction: 查重方向，"forward"为正向查重，"reverse"为反向查重
        forward_threshold: 正向查重判定阈值
        reverse_threshold: 反向查重判定阈值
    
    Returns:
        包含查重结果的字典
    """
    result = {
        'is_duplicate': False,
        'ratio': 0.0,
        'count': 0,
        'total': 0,
        'product_name': None,
        'threshold_met': False
    }
    
    product_name, product_count = get_top_product(json_data)
    result['product_name'] = product_name
    
    if product_name is None:
        result['error'] = "No product information found in the data"
        return result
    
    if direction == "forward":
        # 正向查重：计算排名最高的产品数量占总数量的比例
        total_count = get_size(json_data)
        if total_count > 0:
            ratio = product_count / total_count
            result.update({
                'ratio': ratio,
                'count': product_count,
                'total': total_count,
                'is_duplicate': ratio >= forward_threshold,
                'threshold_met': ratio >= forward_threshold
            })
    
    elif direction == "reverse":
        # 反向查重：计算新规则的产品数量占现有规则总数量的比例
        query = f'app="{product_name}"'
        new_json_data = fofa_stats(query)
        
        total_count = get_size(new_json_data)
        new_count = get_size(json_data)
        
        if total_count > 0:
            ratio = new_count / total_count
            result.update({
                'ratio': ratio,
                'count': new_count,
                'total': total_count,
                'is_duplicate': ratio >= reverse_threshold,
                'threshold_met': ratio >= reverse_threshold
            })
    
    return result

def is_duplicate(query: str):
    """
    完整的查重流程，综合正向和反向查重的结果
    
    Args:
        query: FOFA查询语句
        
    Returns:
        包含查重结果的字典
    """
    result = {
        'query': query,
        'forward_check': None,
        'reverse_check': None,
        'is_duplicate': False,
        'top_product': None
    }
    
    # 获取查询数据
    json_data = fofa_stats(query)
    
    if json_data['error'] == 'true':
        result['error'] = json_data['errmsg']
        return result
    
    # 正向查重
    forward_result = check_duplicate(json_data, "forward")
    result['forward_check'] = forward_result
    
    # 添加API请求间隔
    time.sleep(3) # 统计聚合每5秒只允许查询一次
    
    # 反向查重
    reverse_result = check_duplicate(json_data, "reverse")
    result['reverse_check'] = reverse_result
    
    # 综合判断
    result['top_product'] = forward_result.get('product_name')
    result['is_duplicate'] = forward_result.get('is_duplicate') or reverse_result.get('is_duplicate')
    
    return result

# 示例查询
if __name__ == "__main__":
    query = 'body="js/validator.js" && body="js/mootools.js" && title="IDC/ISP"'
    # query = 'banner="aurora" && (banner="AD" || banner="ADC")'
    
    # # 单独测试正向和反向查重
    # json_data = fofa_stats(query)
    
    # print("正向查重结果:")
    # forward_result = check_duplicate(json_data, "forward")
    # print(forward_result)
    
    # # 添加API请求间隔
    # time.sleep(5) # 统计聚合每5秒只允许查询一次

    # print("\n反向查重结果:")
    # reverse_result = check_duplicate(json_data, "reverse")
    # print(reverse_result)
    
    # # 添加API请求间隔
    # time.sleep(5) # 统计聚合每5秒只允许查询一次

    # 测试综合查重函数
    print("\n综合查重结果:")
    duplicate_check = is_duplicate(query)
    print(duplicate_check)