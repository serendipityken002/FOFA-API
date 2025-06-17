import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import requests
import base64
import json

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

def fofa_search(query, fields='banner'):
    """
    使用FOFA API进行搜索内容
    """
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
    
def get_banner_or_title(query):
    """
    根据规则查询FOFA，获取banner或title信息
    """
    banner_query = '(' + query + ') && type="service"'
    result = fofa_search(banner_query)
    if result.get('error'):
        print(f"FOFA查询失败: {result['errmsg']}")
        return []
    # 若result内容不为空
    if result['size'] > 5:
        content = result['results'][:5]
    else:
        result = fofa_search(query, fields='title')
        content = result['results'][:5]
    content.append(f"查询规则: {query}")
    return content

def crawl_website(url):
    """
    爬取指定网站HTML内容
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if len(response.text) > 80000:
            print(f"警告: 爬取的内容过长 ({len(response.text)} 字符)，需要截取前后各30000字符，中间部分省略")
        # 截断内容以避免过长
        if len(response.text) > 80000:
            return response.text[:30000] + response.text[-30000:]  # 截取前后各30000字符，中间部分省略
        else:
            return response.text
    except requests.RequestException as e:
        print(f"爬取网站失败: {str(e)}")
        return None

def check_webside_manufacturer(llm, content, webside, manufacturer):
    """
    使用LLM检查网站和厂商信息
    """
    template = """
    你是一个优秀的厂商信息分析师，你需要根据以下内容判断官方网站和厂商信息是否正确。
    
    参考信息: {content}
    
    网站名： {webside}
    网站内容: {web_html}
    厂商名: {manufacturer}
    
    请结合你的网站数据和行业常识，并根据参考信息，分别判断厂商名和网站内容是否正确，返回判断结果和理由。
    - 首先判断网站内容是否与参考信息一致：第一步思考参考信息的厂商、产品等；第二步思考网站内容是否与参考信息对应；不考虑版本、语言等差异，若一致则返回官方网站正确。
    - 然后判断厂商名，是否与参考信息一致：第一步思考参考信息的厂商；第二步判断参考信息的厂商是否与给定的厂商一致。不考虑版本、语言等差异，若厂商名与参考信息一致，则返回厂商名正确。
    - 注意：厂商名和网站内容之间的关系不用考虑，只需要分别判断厂商名和网站内容是否正确即可。

    """
    
    web_html = crawl_website(webside)

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

def main(query, webside, manufacturer):
    load_environment()
    
    # 初始化LLM
    llm = ChatOpenAI(
        model="qwen",
        openai_api_base="http://211.91.254.226:2440/v1",
        verbose=True,
    )

    content = get_banner_or_title(query)
    print("查询结果:", content)
    res = check_webside_manufacturer(
        llm, 
        content=content, 
        webside=webside, 
        manufacturer=manufacturer
    )
    return res

if __name__ == "__main__":
    query = 'banner="Wisnetworks" && banner="WIS-Q300"'
    webside = 'https://teltonika-networks.com/products/routers/rutm50'
    manufacturer = 'Teltonika Networks UAB.'
    res = main(query, webside, manufacturer)
    print("最终结果:", res)