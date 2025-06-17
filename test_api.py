import os
import traceback  # 添加用于错误追踪
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.utilities.serpapi import SerpAPIWrapper

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

def create_search_tool():
    """创建搜索工具，增强错误处理"""
    try:
        # 检查API密钥是否存在
        if not os.getenv("SERPAPI_API_KEY"):
            return lambda query: "搜索引擎API密钥未设置，无法执行搜索"
            
        search = SerpAPIWrapper()
        
        # 包装搜索函数，增强错误处理
        def safe_search(query):
            if not query or len(query.strip()) == 0:
                return "搜索查询为空，请提供有效的搜索词"
            
            try:
                result = search.run(query)
                if not result:
                    return "搜索未返回结果，请尝试其他关键词"
                return result
            except Exception as e:
                error_msg = f"搜索执行失败: {str(e)}"
                print(error_msg)
                return error_msg
        
        return safe_search
    except Exception as e:
        print(f"初始化搜索工具失败: {str(e)}")
        return lambda query: f"搜索引擎初始化失败: {str(e)}"

def create_page_analyzer(llm):
    """创建网页分析工具"""
    def analyze_page_content(input_str=None, title=None, header=None, body=None):
        # 如果input_str不为空但参数为空，尝试使用input_str
        if input_str and not (header or body):
            # 这里可以添加解析input_str的逻辑
            # 简单起见，直接作为body使用
            body = input_str
        
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
            return chain.run(header=header or "未提供头部信息", 
                           body=body[:2000] if body else "未提供正文内容")
        except Exception as e:
            error_msg = f"分析网页内容失败: {str(e)}"
            print(error_msg)
            return error_msg
    
    return analyze_page_content

def create_agent(header, body, model="deepseek-v3-250324", base_url="https://ark.cn-beijing.volces.com/api/v3"):
    """创建并配置分析Agent"""
    try:
        # 确保API密钥已设置
        if not os.getenv("OPENAI_API_KEY"):
            print("错误: OPENAI_API_KEY未设置")
            return None
            
        # 初始化LLM
        llm = ChatOpenAI(
            base_url=base_url,
            model=model,
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 创建分析工具
        page_analyzer = create_page_analyzer(llm)
        
        # 创建搜索工具
        search_tool = create_search_tool()
        
        # 定义工具集
        tools = [
            Tool(
                name="AnalyzePageContent",
                func=lambda input_str: page_analyzer(input_str, None, header, body),
                description="分析网页的header、body内容，提取产品和可能的厂商信息"
            ),
            Tool(
                name="SearchForManufacturer",
                func=search_tool,
                description="使用搜索引擎查找产品厂商信息，输入为“相关信息”的厂商是什么？例如：zftal-ui-v5的厂商是什么？"
            )
        ]
        
        # 创建Agent
        agent = initialize_agent(
            tools, 
            llm, 
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
            verbose=True,
            handle_parsing_errors=True  # 添加此参数以处理解析错误
        )
        
        return agent
    except Exception as e:
        error_msg = f"创建Agent失败: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())  # 打印完整堆栈
        return None

def analyze_webpage(header, body):
    """网页分析主函数"""
    # 加载环境变量
    load_environment()
    
    # 创建Agent
    agent = create_agent(header, body)
    if not agent:
        return "Agent创建失败，请检查配置和API密钥"
    
    # 运行agent
    try:
        result = agent.run(
            """
            我需要你帮我确定网页内容中的产品厂商。
            
            首先，使用AnalyzePageContent工具分析网页内容，提取产品信息。
            然后，如果有明确的线索，使用SearchForManufacturer工具搜索确认真正的厂商。
            最后，返回一个完整的报告，包含：厂商名称以及确认的原因。
            
            网页内容已经准备好供你分析。
            """
        )
        return result
    except Exception as e:
        error_msg = f"分析过程出错: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())  # 打印完整堆栈
        return error_msg

def test_api():
	"""测试API功能"""
	query = 'banner="DeskJet 2800" || header="DeskJet 2800"的厂商是什么？回答最可能的厂商名称。'
	llm = ChatOpenAI(
		model="deepseek-v3-250324", 
		base_url="https://ark.cn-beijing.volces.com/api/v3"
	)

	res =  llm.invoke(query)
	print("API测试结果:", res)

# 示例调用
if __name__ == "__main__":
#     # 示例数据 - 实际使用时应从网页抓取
#     sample_body = """<!DOCTYPE html>
# <html>

# 	<head>
# 		<meta charset="UTF-8">
# <meta content="webkit" name="renderer" />
# <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
# <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
# <meta name="viewport" content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no">
# <meta name="Copyright" content="版权所有&copy Copyright 1999-2017 中国" />
# <link rel="icon" href="/assets/logo/favicon.ico" type="image/x-icon" />
# <link rel="shortcut icon" href="/assets/logo/favicon.ico" type="image/x-icon" />
# <title>新一代集成平台后台</title>
# 		<link rel="stylesheet" type="text/css" href="/webjars/zftal-ui-v5/plugins/bootstrap/css/bootstrap.min.css?ver=55a744078cead3c7bc4d4ce04ff65a1f" />
# 		<link rel="stylesheet" href="/assets/css/login.css?ver=55a744078cead3c7bc4d4ce04ff65a1f" />
# 		<script type="text/javascript">
# 			//全局变量
# 			var _path = "";
# 		</script>	
# 	</head>

# 	<body>
# 		<div class="login-page">
# 			<div class="login-form-wrap col-lg-3 col-md-5 col-sm-6 col-xs-12 pull-right p-lr0">
# 				<div class="login-form">
# 					<div class="tabs-icon">
# 						<!-- <img class="active" src="/assets/images/tab_one.png"> -->
# 						<img src="/assets/images/tab_two.png">
# 					</div>
# 					<div class="text-center title">
# 						<h3>用户登录</h3>
# 					</div>
# 					<div class="login-cont">
# 						 <form class="form-horizontal" role="form" action="/authz/login/slogin" method="post" autocomplete="off">
# 						  	<!-- 防止浏览器自动填充密码 -->
# 							<input type="text" style="display: none;" />
# 							<input type="password" style="display: none;" />
# 							<!-- 防止浏览器自动填充密码 end -->
# 						    <div class="form-group"><p style="display: none;" id="tips" class="bg bg-warning"></p></div>
# 							<div class="form-group">
# 								<div class="input-group">
# 									<div class="input-group-addon"><img src="/assets/images/login_user.png"></div>
# 									<input type="text" class="form-control user-input" name="yhm" id="yhm" placeholder="用户名" autocomplete="off">
# 								</div>
# 							</div>
# 							<div class="form-group">
# 								<div class="input-group">
# 									<div class="input-group-addon"><img src="/assets/images/login_pwd.png"></div>
# 									<input type="password" class="form-control pwd-input" name="mm" id="mm" placeholder="密码" autocomplete="off"/>
# 								</div>
# 							</div>
# 							<!--<div class="form-group">
# 								<div class="col-lg-12 col-md-12 col-sm-12 col-xs-12 p-lr0 forget-me">
# 									<input id="rememberMe" class="default-checkbox" type="checkbox" name="rememberMe" />
# 									<label for="rememberMe">记住密码（一周内无需再次输入账号密码）</label>
# 								</div>
# 							</div>-->
# 							<div class="form-group login-btn-wrap">
# 								<button type="button" id="btn-login" class="btn btn-block btn-primary login-btn">登 录</button>
# 							</div>
# 						</form>
						
# 						<div class="form-group">
# 							<!--<a href="">统一身份认证登录</a>-->
# 							<a href="/user/regist/" class="pull-right">注册账号</a>
# 						</div>
# 					</div>
# 					<div class="qrcode-cont">
# 						<div class="scanning-info">
# 							<div class="form-group"><img src="/assets/images/qrcode.png"></div>
# 							<div class="form-group"><span>手机扫描</span><span class="pull-right">安全登录</span></div>
# 						</div>
# 					</div>
# 				</div>
# 			</div>
# 		</div>
		
# <!--jQuery核心框架库 -->
# <script type="text/javascript" src="/webjars/zftal-ui-v5/js/jquery-min.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type="text/javascript" src="/webjars/zftal-ui-v5/js/jquery-migrate-1.4.1.min.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type="text/javascript" src="/webjars/zftal-ui-v5/js/utils/jquery.utils.commons.min.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type="text/javascript" src="/assets/js/zftal-ui-ajax.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script><!-- RSA加密 -->
# <script type='text/javascript' src="/webjars/zftal-ui-v5/plugins/crypto/rsa/jsbn.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type='text/javascript' src="/webjars/zftal-ui-v5/plugins/crypto/rsa/prng4.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type='text/javascript' src="/webjars/zftal-ui-v5/plugins/crypto/rsa/rng.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type='text/javascript' src="/webjars/zftal-ui-v5/plugins/crypto/rsa/rsa.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# <script type='text/javascript' src="/webjars/zftal-ui-v5/plugins/crypto/rsa/base64.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# 		<script type="text/javascript">
# 			var isEncrypt = 'true';
# 		</script>
# 		<script type="text/javascript" src="/assets/js/login.js?ver=55a744078cead3c7bc4d4ce04ff65a1f"></script>
# 	</body>

# </html>"""
#     sample_header = """
# 	HTTP/1.1 200
# 	Connection: close
# 	Content-Length: 4946
# 	Content-Language: zh-CN
# 	Content-Type: text/html;charset=utf-8
# 	Date: Wed, 11 Jun 2025 22:20:22 GMT
# 	Set-Cookie: smpId=94EA90187D946D375E217947A69D0456; Path=/; HttpOnly
# 	X-Content-Type-Options: nosniff
# 	X-Frame-Options: SAMEORIGIN
# 	X-Xss-Protection: 1; mode=block
# 	"""
    
#     result = analyze_webpage(sample_header, sample_body)
#     print("\n最终结果:")
#     print(result)
	test_api()