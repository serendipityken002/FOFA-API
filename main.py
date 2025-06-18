import os
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

import json
from openai import OpenAI

from duplicate_check_demo import is_duplicate
from check_info import check

def duplicate_check(rule):
    """
    执行FOFA规则重复性检查
    Args:
        rule (str): FOFA规则
    Returns:
        error (bool): 是否有错误
        is_duplicate (bool): 是否重复
        reason (str): 重复性检查的理由
        product (str): 已有的产品名称
    """
    result = is_duplicate(rule)

    # 返回错误原因
    if 'error' in result:
        return json.dumps({
            'error': True,
            'message': result['error']
        })

    # 返回重复性检查结果
    duplicate = result.get('is_duplicate', False)

    if not duplicate:
        return json.dumps({
            'error': False,
            'is_duplicate': duplicate,
            'reason': '当前规则不重复',
            'product': '无记录'
        })

    f_ratio = result.get('forward_check', {}).get('ratio', 0)
    r_ratio = result.get('reverse_check', {}).get('ratio', 0)
    product_name = result.get('top_product', '无记录')
    reason = f"现有规则 \"{product_name}\" 占当前规则的比例为 {f_ratio:.2f}。并且反向查重比例为 {r_ratio:.2f}。" if f_ratio or r_ratio else "无相关数据"

    return json.dumps({
        'error': False,
        'is_duplicate': duplicate,
        'reason': reason,
        'product': product_name
    })

def info_check(rule, webside, manufacturer, classification1, classification2):
    """
    根据规则内容，判断厂商、分类、官网网址是否准确
    """
    res = check(rule, webside, manufacturer, classification1, classification2)
    return res

def main():
    query = r'body="var modelName=\"EX1110\"" || cert="EX1110"'
    webside = 'https://service-provider.tp-link.com/wifi-router/ex1110/'
    manufacturer = 'TP-Link Systems Inc.'
    classification1 = '网络交换设备'
    classification2 = '路由器'

    result = duplicate_check(query)
    result = json.loads(result)
    if not result['error']:
        info_result = info_check(query, webside, manufacturer, classification1, classification2)
        # 确保duplicate_check键存在
        if 'duplicate_check' not in info_result:
            info_result['duplicate_check'] = {}
        info_result['duplicate_check']['result'] = result['is_duplicate']
        info_result['duplicate_check']['reason'] = result['reason']
        print(info_result)
    else:
        print(f"Error: {result['message']}")

if __name__ == "__main__":
    main()