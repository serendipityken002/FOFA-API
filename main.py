import os
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

import json
from openai import OpenAI
import pandas as pd
from datetime import datetime

from duplicate_check_demo import is_duplicate
from check_info import check
from check_rule import rule


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
    print("=============开始执行规则重复性检查============")
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
    print("\n\n=============开始执行规则的厂商、分类、官网网址检查===============\n\n")
    res = check(rule, webside, manufacturer, classification1, classification2)
    return res

def rule_check(guize):
    """
    执行规则检查
    """
    print("\n\n=============开始执行规则检查============\n\n")
    result = rule(guize)
    return result

def rule2excel(query, webside, manufacturer, classification1, classification2):
    """
    将所有规则信息转换为Excel格式
    """
    # 执行规则重复性检查
    result = duplicate_check(query)
    result = json.loads(result)
    print("=============规则重复性检查结果============")
    print(result)

    # 执行规则厂商、分类、官网网址检查
    if not result['error']:
        info_result = info_check(query, webside, manufacturer, classification1, classification2)
        print("=============规则厂商、分类、官网网址检查结果============")
        print(info_result)
        # 确保duplicate_check键存在
        if 'duplicate_check' not in info_result:
            info_result['duplicate_check'] = {}
        info_result['duplicate_check']['result'] = result['is_duplicate']
        info_result['duplicate_check']['reason'] = result['reason']
    else:
        print(f"error: {result['message']}")

    # 执行规则准确性检查
    if not result['error']:
        rule_result = rule_check(query)
        print("=============规则准确性检查结果============")
        print(rule_result)
        # 确保rule_check键存在
        if 'rule_check' not in info_result:
            info_result['rule_check'] = {}
        info_result['rule_check']['result'] = rule_result['result']
        info_result['rule_check']['reason'] = rule_result['reason']

    print("\n\n=============最终结果============")
    print(json.dumps(info_result, indent=4, ensure_ascii=False))

    # 将结果转换为Excel格式
    main_true = False
    if info_result['website_check']['result'] and info_result['manufacturer_check']['result'] and info_result['classification_check']['result'] and info_result['rule_check']['result'] and not info_result['duplicate_check']['result']:
        main_true = True

    # 整合原因信息
    reason_details = []
    if not info_result['website_check']['result']:
        reason_details.append(f"网站检查: {info_result['website_check']['reason']}")
    if not info_result['manufacturer_check']['result']:
        reason_details.append(f"厂商检查: {info_result['manufacturer_check']['reason']}")
    if not info_result['classification_check']['result']:
        reason_details.append(f"分类检查: {info_result['classification_check']['reason']}")
    if not info_result['rule_check']['result']:
        reason_details.append(f"规则检查: {info_result['rule_check']['reason']}")
    if info_result['duplicate_check']['result']:
        reason_details.append(f"重复性检查: {info_result['duplicate_check']['reason']}")
    
    reason_text = "; ".join(reason_details) if reason_details else "所有检查均通过"
    
    # 创建Excel文件
    # 创建数据行
    data = {
        "分类": [classification2],
        "产品URL": [webside],
        "厂商": [manufacturer],
        "规则内容": [query],
        "是否录入": [main_true],
        "原因": [reason_text]
    }
    
    # 创建DataFrame
    excel_file = "rule_check_result.xlsx"
    df_new = pd.DataFrame(data)

    if os.path.exists(excel_file):
        # 读取已有内容
        df_old = pd.read_excel(excel_file)
        # 追加新内容
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new

    # 保存到同一个文件，覆盖写入
    df_all.to_excel(excel_file, index=False)
    print(f"结果已保存到Excel文件: {excel_file}")
    
    return {
        "excel_file": excel_file,
        "main_true": main_true,
        "info_result": info_result
    }

def main():
    # 输入
    query = r'banner="AXIS P1448-LE"'
    webside = 'https://www.axis.com/products/axis-p1448-le/support'
    manufacturer = 'Axis Communications AB.'
    classification1 = '物联网设备'
    classification2 = '视频监控'

    res = rule2excel(query, webside, manufacturer, classification1, classification2)
    print("文件书写完成:", res)

if __name__ == "__main__":
    main()