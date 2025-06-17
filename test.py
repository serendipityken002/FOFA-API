import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import requests
import base64

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

def analyze_page_content(llm, header=None, body=None):
    if not body:
        return "错误: 没有提供网页内容进行分析"
        
    template = """
    你现在的任务是：  
    **从给定的网页内容、HTTP响应头、HTML源码、JS/CSS路径、图片路径、文本内容等所有信息中，尽可能全面、详细地提取与系统厂商、开发公司、产品品牌、开发团队、制作方等相关的所有信息。**

    已知的信息有：
    头部(Header): {header}
    正文摘要(Body): {body}
    
    ---
    
    请按如下要求操作：

    1. **直接列举所有与厂商有关的内容**，包括但不限于：
    - 版权声明（如meta标签、页面底部、注释等）
    - 页面标题、描述、Logo图片、favicon图标路径
    - 任何出现的公司名、品牌名、产品名、开发团队名
    - JS、CSS、图片等静态资源路径中包含的公司/产品/品牌标识
    - Cookie名、URL路径、参数等隐含公司/产品特征
    - 界面语言、专有术语、字段命名习惯
    - 页面中的任何联系方式、备案号、官方链接
    - 其他可能暗示厂商身份的任何线索

    2. **每条信息请注明其具体来源位置或路径**（如"meta标签"、"favicon路径"、"js文件名"、"表单字段名"）。

    3. **不要进行厂商归属推测，只做信息客观罗列。**
    """
    
    prompt = PromptTemplate(
        input_variables=["header", "body"],
        template=template
    )
    
    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        if not header or not body:
            print("警告: header或body为空，可能导致分析不完整")
        return chain.run(header=header, body=body[:2000])
    except Exception as e:
        error_msg = f"分析网页内容失败: {str(e)}"
        print(error_msg)
        return error_msg
    
def analyze_webpage(llm, inference_info):
    template = """
    {inference_info}的最可能的厂商是什么？请给出相应理由
    """
    prompt = PromptTemplate(
        input_variables=["inference_info"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run(inference_info=inference_info)
    except Exception as e:
        error_msg = f"分析厂商信息失败: {str(e)}"
        print(error_msg)
        return error_msg

def check_result(llm, inference_info, result):
    """
    检查分析结果是否符合预期
    """
    template = """
    你是一个优秀的厂商信息分析师，你需要检查给定的分析结果是否符合预期。
    
    推断信息: {inference_info}
    分析结果: {result}
    
    请判断分析结果是否准确，并给出理由及其你认为的准确的信息。
    """
    
    prompt = PromptTemplate(
        input_variables=["inference_info", "result"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run(inference_info=inference_info, result=result)
    except Exception as e:
        error_msg = f"检查分析结果失败: {str(e)}"
        print(error_msg)
        return error_msg

def get_official_website(llm, info):
    """
    从分析结果中提取官方网站
    """
    template = """
    你是一个优秀的厂商信息分析师，你需要从给定的信息中提取官方网站。
    
    信息内容: {info}
    
    请结合你的网站数据，返回最有可能的官方网站URL，及其判断原因。
    """
    
    prompt = PromptTemplate(
        input_variables=["info"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        return chain.run(info=info)
    except Exception as e:
        error_msg = f"提取官方网站失败: {str(e)}"
        print(error_msg)
        return error_msg

# 构建Fofa API请求
def fofa_search(query):
    email = os.getenv('FOFA_EMAIL')
    key = os.getenv('FOFA_KEY')
    base_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': base64.b64encode(query.encode()).decode(),
        'fields': 'title,banner',
    }
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}"}

def main():
    load_environment()
    llm = ChatOpenAI(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        model="deepseek-v3-250324"
    )
    # inference_info = analyze_page_content(llm, header=header, body=body)
    inference_info = """
    banner="ARRIS CHP Max SNMP agent"
    """
    print("分析结果:", inference_info)
    analyze_webpage_result = analyze_webpage(llm, inference_info=inference_info)
    print("厂商信息分析结果:", analyze_webpage_result)

    # get_official_website_result = get_official_website(llm, info="banner=KX IV-101 040300")
    # print("提取的官方网站:", get_official_website_result)

if __name__ == "__main__":
    main()