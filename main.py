import os
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

import json
from openai import OpenAI

from duplicate_check_demo import is_duplicate

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

def main():
    rule = 'banner="aurora" && (banner="AD" || banner="ADC")'
    result = duplicate_check(rule)
    result = json.loads(result)
    print(result)

if __name__ == "__main__":
    main()