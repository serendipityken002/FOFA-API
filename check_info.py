import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import requests
import base64
import json

from API import fofa_search

def load_environment():
    """加载环境变量"""
    load_dotenv()
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
    os.environ['SERPAPI_API_KEY'] = os.getenv("SERPAPI_API_KEY", "")
    
    # 检查关键环境变量
    if not os.environ["SERPAPI_API_KEY"]:
        print("警告: SERPAPI_API_KEY 未设置")
    if not os.environ["OPENAI_API_KEY"]:
        print("警告: OPENAI_API_KEY 未设置")
  
def get_banner_or_body(query):
    """
    根据规则查询FOFA，获取banner或title信息
    """
    print(f"=============开始获取banner和body信息================")
    banner_query = '(' + query + ') && type="service"'
    body_query = '(' + query + ') && type!="service"'
    banner_result = fofa_search(banner_query, fields='banner')
    body_result = fofa_search(body_query, fields='body')
    if banner_result.get('error') and body_result.get('error'):
        print(f"FOFA查询失败: {banner_result.get('error', '')} {body_result.get('error', '')}")
        return []
    
    # 若result内容不为空
    body_result = body_result.get('results', [])[:3]
    banner_result = banner_result.get('results', [])[:5]

    # 简化body的内容
    # body_result = simplify_content(body_result)


    # 合并banner和body内容
    content = []
    if banner_result:
        content.append("查询到的Banner信息:")
        for item in banner_result:
            content.append(f"Banner: {item}")
    if body_result:
        content.append("查询到的Body信息:")
        for item in body_result:
            if len(item) > 20000:
                content.append(f"Body: {item[:10000]}...{item[-10000:]}")
            else:
                content.append(f"Body: {item}")

    content.append(f"查询规则: {query}")
    return content

def crawl_website(url):
    """
    爬取指定网站HTML内容
    """
    print(f"============开始爬取网站 {url} 的html内容================")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # 调用简化内容函数
        # response = simplify_content(response.text)
        
        # 截断内容以避免过长
        if len(response.text) > 80000:
            print(f"警告: 爬取的内容过长 ({len(response.text)} 字符)")
            return response.text[:25000] + response.text[-25000:]  # 截取前后各30000字符，中间部分省略
        else:
            return response.text
    except requests.RequestException as e:
        print(f"爬取网站失败: {str(e)}")
        return None

def check_webside_manufacturer(llm, content, webside, manufacturer):
    """
    使用LLM检查网站和厂商信息
    """
    print("================开始检查厂商和网站信息准确性===================\n")
    template = """
    你是一个优秀的厂商信息分析师，你需要根据以下内容判断官方网站和厂商信息是否正确。
    
    参考信息: {content}
    
    网站名： {webside}
    网站内容: {web_html}
    厂商名: {manufacturer}
    
    请结合你的网站数据和行业常识，并根据参考信息，分别判断厂商名和网站内容是否正确，返回判断结果和理由。
    - 首先判断网站内容是否与参考信息一致：第一步思考参考信息的厂商、产品等；第二步思考网站内容是否与参考信息对应；不考虑版本、语言等差异，若一致则返回官方网站正确。
    - 然后判断厂商名，是否与参考信息一致：第一步思考参考信息中的厂商相关线索（如域名、产品名称等）；第二步判断给定的厂商名是否与这些线索匹配。即使参考信息中没有直接出现完整的厂商名称，只要有足够的间接证据（如域名、产品特征等）表明厂商一致，也应判定为正确。
    
    注意：
    1. 厂商名和网站内容之间的关系不用考虑，只需要分别判断厂商名和网站内容是否正确即可。
    2. 对于厂商名的判断，不要过于严格要求参考信息中必须出现完整的厂商名称。如果参考信息中的域名、产品型号等间接证据指向该厂商，应判定为正确。
    3. 若参考信息为空，厂商名和网站名都返回不确定
    4. 若网站内容为空，则网站名返回不确定，厂商名仍然判断是否正确

    """
    
    web_html = crawl_website(webside)
    print(f"爬取网站 {webside} 的HTML内容完毕\n")

    prompt = PromptTemplate(
        input_variables=["content", "webside", "web_html", "manufacturer"],
        template=template
    )
    
    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run(content=content, webside=webside, web_html=web_html, manufacturer=manufacturer)
    except Exception as e:
        error_msg = f"检查厂商信息失败: {str(e)}"
        print(error_msg)
        return error_msg

def check_classification(llm, content, classification1, classification2):
    """
    基于参考信息，判断分类是否准确
    """
    print("\n\n================开始检查分类信息准确性===============")
    # 可选的分类结果
    classification = {}
    f = open('classification.json', 'r', encoding='utf-8')
    try:
        classification = json.load(f)
        print("加载所有分类信息成功")
    except json.JSONDecodeError as e:
        print(f"加载所有分类信息失败: {str(e)}")

    template = """
    你是一个优秀的网络信息分类专家，你需要根据以下内容判断分类是否准确，先判断大类再判断小类。

    参考信息: {content}

    所有分类信息：{classification}
    请判断以下两个分类是否准确：

    大类: {classification1}
    小类: {classification2}

    请结合你的专业知识和行业常识，结合给定的所有分类信息，判断这两个分类是否准确，并给出理由。
    - 首先思考参考信息的内容和特点，结合所有分类信息，思考最可能的一级分类名称，判断是否属于大类的内容
    - 然后类似的，结合所有分类信息，进一步判断是否属于小类的内容

    注意：小类必须在对应的大类下面，所以你主要关注小类划分与参考信息是否一致。
    若参考信息为空，返回不确定

    """

    prompt = PromptTemplate(
        input_variables=["content", "classification", "classification1", "classification2"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run(content=content, classification=classification, classification1=classification1, classification2=classification2)
    except Exception as e:
        error_msg = f"检查分类信息失败: {str(e)}"
        print(error_msg)
        return error_msg

def summarize_content(llm, content):
    """
    根据大模型分析的信息，格式化输出为json格式
    """
    print("================开始格式化输出为JSON格式=================")
    template = """
    你是一个优秀的FOFA规则信息审核师，我会提供给你某条规则的厂商、官网地址、分类信息的审核过程，你需要按照给定json格式进行输出。

    审核信息：{content}

    请将审核信息格式化为以下json格式，确保输出是有效的JSON：
    {{
        "website_check": {{
            "result": "True/False",
            "reason": "判断理由"
        }},
        "manufacturer_check": {{
            "result": "True/False",
            "reason": "判断理由"
        }},
        "classification_check": {{
            "result": "True/False",
            "reason": "判断理由"
        }}
    }}

    请注意：
    1. 仅输出JSON格式，不要添加任何其他文本、解释或代码块标记
    2. 使用双引号而不是单引号
    3. result值必须是True或False（不带引号的布尔值）
    4. 确保JSON格式正确，没有多余的逗号或缺少的括号
    """

    prompt = PromptTemplate(
        input_variables=["content"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        if not content:
            return {"error": "内容为空，无法进行总结", 
                   "website_check": {"result": False, "reason": "内容为空"},
                   "manufacturer_check": {"result": False, "reason": "内容为空"},
                   "classification_check": {"result": False, "reason": "内容为空"}}
        
        result = chain.run(content=content)
        
        if not result:
            return {"error": "总结内容为空，无法进行格式化输出",
                   "website_check": {"result": False, "reason": "无法获取结果"},
                   "manufacturer_check": {"result": False, "reason": "无法获取结果"},
                   "classification_check": {"result": False, "reason": "无法获取结果"}}
        
        # 尝试解析为JSON格式
        try:
            # 清理可能导致JSON解析错误的字符
            result = result.strip()
            # 如果结果被包裹在```json和```中，去掉这些标记
            if result.startswith('```json'):
                result = result.replace('```json', '', 1)
            if result.endswith('```'):
                result = result[:-3]
            result = result.strip()
            
            json_result = json.loads(result)
            
            # 确保所有必要的字段都存在
            if "website_check" not in json_result:
                json_result["website_check"] = {"result": False, "reason": "缺少网站检查结果"}
            if "manufacturer_check" not in json_result:
                json_result["manufacturer_check"] = {"result": False, "reason": "缺少厂商检查结果"}
            if "classification_check" not in json_result:
                json_result["classification_check"] = {"result": False, "reason": "缺少分类检查结果"}
                
            return json_result
        except json.JSONDecodeError as e:
            print(f"格式化输出失败: {str(e)}")
            print(f"原始输出: {result}")
            # 返回默认结构而不是错误
            return {
                "error": f"格式化输出失败: {str(e)}",
                "website_check": {"result": False, "reason": "JSON解析失败"},
                "manufacturer_check": {"result": False, "reason": "JSON解析失败"},
                "classification_check": {"result": False, "reason": "JSON解析失败"}
            }
    except Exception as e:
        error_msg = f"总结内容失败: {str(e)}"
        print(error_msg)
        return {
            "error": f"总结内容失败: {str(e)}",
            "website_check": {"result": False, "reason": "处理失败"},
            "manufacturer_check": {"result": False, "reason": "处理失败"},
            "classification_check": {"result": False, "reason": "处理失败"}
        }

def check(query, webside, manufacturer, classification1, classification2):
    load_environment()
    
    # 初始化LLM
    llm = ChatOpenAI(
        model="qwen",
        openai_api_base="http://211.91.254.226:2440/v1",
        verbose=False,
    )

    content = get_banner_or_body(query)
    print("banner和body内容查询完毕\n")

    res = check_webside_manufacturer(
        llm, 
        content=content, 
        webside=webside, 
        manufacturer=manufacturer
    )
    print("="*60)
    print("厂商网站信息检查结果如下:\n", res) 

    res2 = check_classification(
        llm, 
        content=content, 
        classification1=classification1, 
        classification2=classification2
    )
    print("="*60)
    print("\n分类信息检查结果如下:\n", res2)
    
    # 将结果合并并格式化为JSON
    content = res + "\n" + res2
    res_json = summarize_content(llm, content)

    return res_json

if __name__ == "__main__":
    query = r'body="var modelName=\"EX1110\"" || cert="EX1110"'
    webside = 'https://service-provider.tp-link.com/wifi-router/ex1110/'
    manufacturer = 'TP-Link Systems Inc.'
    classification1 = '网络交换设备'
    classification2 = '路由器'
    res = check(query, webside, manufacturer, classification1, classification2)
    print("检测结果如下:\n", res)