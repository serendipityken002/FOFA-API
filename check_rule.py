"""
正确性检测：
验证生成的规则是否能够正确定位产品
(1) 网站
A 若查询结果少于5页(50条), 需要保证每个IP地址对应的网页应完全相同
B 若查询结果远大于5页, 采用随机抽样法: 
- 对所有页面, 随机采取6页, 共60个IP
- 要求80%的页面是某个厂商的一种产品

(2) 服务
对于服务而言, 其可能错误的地方为关键字冗余, 导致该规则检索的结果较少。
例: banner="ZXR10 Carrier-class High-end Routing Switch of ZTE  Corporation"并不能完全包含中兴的所有交换机。使用banner="ZXR10" && banner="Switch"查询的结果几乎是前者的两倍。

思路：
1. 使用Fofa API进行查询, 获取资产总数
2. 若结果小于50, 检索所有IP地址的body
3. 若结果大于50, 对所有页面, 随机采取6页, 共60个IP
4. 对于服务，一次查询所有60条的内容
5. 对于网站，一次查询3条，依次判断
"""
import random
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json

from API import fofa_search
from check_info import load_environment

def simplify_content_list(llm, header_list):
    """
    使用LLM对header_list进行相似度检测，记录相似的索引
    返回相似header的组，每组包含相似header的索引列表
    """
    if not header_list:
        return []
    
    # 使用LLM进行相似度分析
    template = """
    你是一个HTTP响应头分析专家。我会给你一个包含多个HTTP响应头的列表，你需要分析它们的相似性并将它们分组。
    
    HTTP响应头列表:
    {headers}
    
    请分析这些响应头，并将相似的响应头分组。两个响应头相似意味着它们很可能来自相同或非常相似的web服务器配置。
    
    分析以下内容来判断相似性:
    1. Server字段
    2. Content-Type字段
    3. X-Powered-By字段
    4. Set-Cookie模式
    5. 其他关键HTTP头部信息
    
    以JSON格式返回分组结果，每个组是一个包含索引的数组（索引从0开始）。
    例如: [[0, 2, 5], [1, 4], [3, 6, 7]]
    这表示响应头0、2、5相似，1和4相似，3、6、7相似。
    
    注意:
    - 判断尽可能宽松，只要有明显的相似特征即可，类别控制在五组以内且必须包含所有索引
    - 如果某个响应头与其他响应头都不相似，它应该单独一组
    - 只关注响应头的内容，不考虑其他因素
    - 请只返回JSON格式的分组结果，不要添加任何额外解释
    """
    
    try:
        # 准备传递给LLM的header数据
        headers_text = ""
        for i, header in enumerate(header_list):
            headers_text += f"===== 响应头 {i} =====\n{header}\n\n"
        
        # 创建提示并执行
        prompt = PromptTemplate(
            input_variables=["headers"],
            template=template
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        result = chain.run(headers=headers_text)
        
        # 解析JSON结果
        # 去除可能的前后缀文本，只保留JSON部分
        result = result.strip()
        if not result.startswith('['):
            result = result[result.find('['):]
        if not result.endswith(']'):
            result = result[:result.rfind(']')+1]
            
        similarity_groups = json.loads(result)
        print(f"LLM分析的响应头相似度分组: {similarity_groups}")
        
        return similarity_groups
    except Exception as e:
        print(f"分析响应头相似度时出错: {str(e)}")
        # 如果LLM分析失败，退回到简单分组（每个header单独一组）
        return [[i] for i in range(len(header_list))]
    

def summarize_body_content(llm, body_content_list, header_content_list):
    """
    对body的内容进行llm总结，保留主要特征信息。
    使用header相似度分组来减少重复分析。
    """
    if not body_content_list or not header_content_list:
        return []
    
    # 获取相似header的分组
    similarity_groups = simplify_content_list(llm, header_content_list)
    
    template = """
    你是一个优秀的内容总结员, 你的任务是对以下body内容进行总结，保留主要特征信息。
    body_content: {body_content}

    尽可能多的描述body内容的特征信息, 包括但不限于:
    - 网站的功能
    - 网站的技术栈
    - 网站的主要服务
    - 网站的用户界面特征
    - 网站的厂商、产品信息
    - 网站的类别信息
    """

    prompt = PromptTemplate(
        input_variables=["body_content"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        results = body_content_list.copy()  # 创建结果列表的副本
        
        processed_indices = set()  # 跟踪已处理的索引
        
        # 对每组相似的header，只处理第一个
        for group in similarity_groups:
            if not group:
                continue
                
            # 处理每组的第一个元素
            first_idx = group[0]
            if first_idx not in processed_indices:
                result = chain.run(body_content=body_content_list[first_idx])
                results[first_idx] = result
                processed_indices.add(first_idx)
                print(f"完成第{first_idx+1}条body内容的总结")
                
                # 将结果复制到组内其他索引
                for other_idx in group[1:]:
                    results[other_idx] = result
                    processed_indices.add(other_idx)
                    print(f"复用第{first_idx+1}条结果到第{other_idx+1}条 (相似header)")
        
        # 处理剩余未处理的内容（不在任何相似组中的）
        for i in range(len(body_content_list)):
            if i not in processed_indices:
                result = chain.run(body_content=body_content_list[i])
                results[i] = result
                print(f"完成第{i+1}条body内容的总结")
        
        return results
    except Exception as e:
        return {"error": str(e)}

def get_content(query):
    """
    获取Fofa API的查询结果
    """
    banner_query = '(' + query + ') && type="service"'
    body_query = '(' + query + ') && type!="service"'
    print("开始执行FOFA查询探测")
    banner_result = fofa_search(banner_query, fields='banner', page=1, size=10)
    body_result = fofa_search(body_query, fields='body', page=1, size=10)
    header_result = fofa_search(query, fields='header', page=1, size=10)
    print("FOFA查询探测完成")

    print("==============开始查询banner内容==============")
    # 针对banner查询结果进行处理
    if not banner_result['error']:
        banner_size = banner_result.get('size', 0)
        if banner_size < 50:
            # 获取所有IP地址的banner内容
            banner_result = fofa_search(banner_query, fields='banner', page=1, size=banner_size)
            banner_content = [item for item in banner_result.get('results', [])]
        else:
            # 随机抽样6页，每页10条，共60条
            banner_content = []
            page_numbers = random.sample(range(1, (banner_size // 10) + 2), 6)
            for page in page_numbers:
                page_result = fofa_search(banner_query, fields='banner', page=page, size=10)
                banner_content.extend([item for item in page_result.get('results', [])])
    print(f"banner内容如下: \n {banner_content}")
    

    print("==============开始查询body和header内容==============")
    # 针对body查询结果进行处理
    if not body_result['error']:
        body_size = body_result.get('size', 0)
        if body_size < 20:
            # 获取所有IP地址的body内容
            body_result = fofa_search(body_query, fields='body', page=1, size=body_size)
            header_result = fofa_search(query, fields='header', page=1, size=body_size)
            body_content = [item for item in body_result.get('results', [])]
            header_content = [item for item in header_result.get('results', [])]
        else:
            # 随机抽样3页，每页10条，共30条
            body_content = []
            header_content = []
            page_numbers = random.sample(range(1, (body_size // 10) + 2), 3)
            for page in page_numbers:
                page_result = fofa_search(body_query, fields='body', page=page, size=10)
                header_page_result = fofa_search(query, fields='header', page=page, size=10)
                # body_content.extend([item for item in page_result.get('results', [])])
                for item in page_result.get('results', []):
                    if len(item) < 50000:
                        body_content.append(item)
                    else:
                        body_content.append(item[:25000] + '\n...\n' +item[-25000:])
                for item in header_page_result.get('results', []):
                    header_content.append(item)
    print("==============body内容查询完成==============")
    return banner_content, body_content, header_content

def check_content(llm, banner_content, body_content):
    print("==============开始对banner和body内容进行检测============")
    template = """
    你是一个优秀的内容检测员, 你的任务是检查以下所有内容 (banner或者body) 是否为同一类型。
    banner_content协议内容列表: {banner_content}
    body_content网站body内容列表: {body_content}

    首先，你需要依次分析所有的协议内容，得到最多的同一类型协议占总协议的个数比例。
    其次，你需要依次分析所有的body内容，得到最多的同一类型网站占总body的个数比例。
    最后，你需要判断所有的banner+body内容，得到最多的同一类型内容占总内容的个数比例。

    注意：
    banner或body内容为空时，请返回0。
    你需要返回一个JSON格式的字符串，包含以下字段：
    {{
        "banner_ratio": float,  # banner内容中最多的同一类型协议占总协议的个数比例
        "body_ratio": float,    # body内容中最多的同一类型网站占总body的个数比例
        "total_ratio": float     # banner+body内容中最多的同一类型内容占总内容的个数比例
    }}
    """

    prompt = PromptTemplate(
        input_variables=["banner_content", "body_content"],
        template=template
    )

    try:
        chain = LLMChain(llm=llm, prompt=prompt)
        result = chain.run(banner_content=banner_content, body_content=body_content)
        return result
    except Exception as e:
        return {"error": str(e)}

def return_res_reason(res):
    """
    根据检测结果的比例, 返回最终的结果和理由
    """
    # 处理可能包含markdown格式的JSON字符串
    if isinstance(res, str):
        # 清除可能的markdown格式
        if "```" in res:
            # 提取markdown代码块中的内容
            import re
            json_match = re.search(r'```(?:json)?\n(.*?)\n```', res, re.DOTALL)
            if json_match:
                res = json_match.group(1)
        
        # 尝试解析JSON
        try:
            res = json.loads(res)
        except Exception as e:
            print(f"JSON解析错误: {str(e)}")
            print(f"原始字符串: {res}")
            return {
                "result": False,
                "reason": "结果解析失败，无法判断规则正确性"
            }

    # 提取比例数据
    banner_ratio = res.get('banner_ratio', 0)
    body_ratio = res.get('body_ratio', 0)
    total_ratio = res.get('total_ratio', 0)
    if banner_ratio < 0.7 and body_ratio < 0.7:
        return {
            "result": False,
            "reason": f"规则不正确, 随机抽样60条banner, 最高的同一类型比例: {banner_ratio:.2f}, 随机抽样30条body, 最高的同一类型比例: {body_ratio:.2f}, 总比例: {total_ratio:.2f}。"
        }
    else:
        return {
            "result": True,
            "reason": f"规则正确, 随机抽样60条banner, 最高的同一类型比例: {banner_ratio:.2f}, 随机抽样30条body, 最高的同一类型比例: {body_ratio:.2f}, 总比例: {total_ratio:.2f}。"
        }

def rule(query):
    banner_content, body_content, header_content = get_content(query)
    load_environment()
    
    # 初始化LLM
    llm = ChatOpenAI(
        model="qwen",
        openai_api_base="http://211.91.254.226:2440/v1",
        verbose=True,
    )

    print("开始对body内容进行总结")
    simple_body_content = summarize_body_content(llm, body_content, header_content)
    print("body内容总结完成")
    res = check_content(llm, banner_content, simple_body_content)
    print("内容检测完成")
    res_reason = return_res_reason(res)
    return res_reason

if __name__ == "__main__":
    query = r'banner="AXIS P1344" || title="AXIS P1344"'
    res = rule(query)
    print("检查结果:", res)
