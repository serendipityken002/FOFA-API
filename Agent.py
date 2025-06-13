import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

from duplicate_check_demo import is_duplicate


def create_duplicate_check_chain(llm, verbose=False):
    """
    创建规则重复检查链
    """
    duplicate_template = """
    你是专业的FOFA规则查重分析专家。根据双向查重数据，严格按照既定逻辑判断规则重复性。
    ## 查重逻辑规则

    ### 1. 正向查重分析 (Forward Check)
    - **目的**: 检查新规则检索资产被老规则覆盖的比例
    - **阈值**: ratio ≥ 0.7 时需要进行反向查重
    - **判断**: ratio < 0.7 时直接判定为"不重复"

    ### 2. 反向查重分析 (Reverse Check) 
    - **前提**: 正向查重ratio ≥ 0.7
    - **目的**: 检查老规则资产被新规则覆盖的比例
    - **判断逻辑**:
    - ratio < 0.5: 新规则是老规则的细分 → "不重复"
    - ratio ≥ 0.5: 新规则与老规则高度重叠 → "重复"

    ## 输入数据
    ```json
    {result}
    ```

    ## 分析步骤
    1. 从输入数据中检查，是否存在error字段，如果存在，直接返回error字段下的错误信息。
    2. 提取forward_check和reverse_check的ratio值
    3. 按照既定逻辑进行判断，只有在正向查重ratio ≥ 0.7的情况下才进行反向查重分析
    4. 生成详细的分析理由

    ## 输出要求
    严格返回以下JSON格式，不要添加任何额外文字：

    ```json
    {{
        "is_duplicate": true/false,
        "top_product": "现有规则的名称",
        "ratio": "给出正向查重ratio和反向查重ratio的值（如果有反向查重）",
        "reason": "基于正向查重ratio和反向查重ratio的详细分析。具体判断逻辑，中文回答"
    }}
    ```

    请现在进行分析："""

    duplicate_prompt = PromptTemplate(
        input_variables=["result"],
        template=duplicate_template
    )

    # 使用新的链式调用方式
    duplicate_chain = duplicate_prompt | llm
    
    return duplicate_chain

def duplicate_check_tool(query: str) -> str:
    """
    规则重复检查工具函数
    """
    try:
        # 检查并修复查询字符串
        if query.count('"') % 2 != 0:  # 如果引号数量不是偶数
            # 检查是否缺少最后的引号
            last_quote_pos = query.rfind('"')
            if last_quote_pos > 0 and query[last_quote_pos-1] != '\\':
                query = query + '"'
        
        # 获取重复检查结果
        print(f"正在检查查询: {query}")
        result = is_duplicate(query)
        
        # 创建LLM实例
        llm = ChatOpenAI(
            base_url="https://api.chatanywhere.tech/v1",
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=500
        )
    
        # 创建分析链
        duplicate_chain = create_duplicate_check_chain(llm, verbose=True)
        
        # 执行分析
        analysis_result = duplicate_chain.invoke({
            "result": json.dumps(result, ensure_ascii=False, indent=2)
        })
            
        # 如果返回的是对象，提取content属性
        if hasattr(analysis_result, 'content'):
            # 去除markdown代码块标记
            content = analysis_result.content
            content = content.replace('```json', '').replace('```', '').strip()
            return content
        else:
            return analysis_result
        
    except Exception as e:
        error_msg = f"重复检查工具执行失败: {str(e)}"
        return json.dumps({
            "is_duplicate": False,
            "reason": error_msg
        }, ensure_ascii=False)

class FOFAAnalysisAgent:
    """FOFA规则分析Agent类"""

    def __init__(self, base_url="https://api.chatanywhere.tech/v1", model="gpt-3.5-turbo", verbose=True):
        self.verbose = verbose

        self.llm = ChatOpenAI(
            base_url=base_url,
            model=model,
            temperature=0.3,
            max_tokens=1500
        )

        self.tools = [
            Tool(
                name="duplicate_check",
                func=duplicate_check_tool,
                description="""
                检查FOFA规则是否与已有规则重复。
                输入: FOFA查询语句 例如: 
                - body="js/validator.js" && body="js/mootools.js"
                - title="beijing"
                - banner="AD" || banner="ADC"
                输出: 简体中文回答，JSON格式的分析结果，包含是否重复、top产品名称和分析理由。
                """
            )
        ]

        # 创建对话记忆
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 系统提示词
        self.system_message = """
        你是专业的FOFA规则分析助手，专门帮助用户分析和优化FOFA搜索规则。

        ## 可用工具
        1. **duplicate_check**: 检查规则是否与已有规则重复

        ## 分析流程
        1. 理解用户的分析需求
        2. 根据需求选择并调用适当的工具
        3. 解读工具返回的JSON数据
        4. 提供专业、清晰的分析报告
        """

        # 初始化Agent
        self.agent = self._create_agent()
        
    def _create_agent(self):
        """创建Agent实例"""
        return initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
            verbose=self.verbose,
            memory=self.memory,
            agent_kwargs={
                "system_message": self.system_message
            },
            max_iterations=3,
            early_stopping_method="generate"
        )

    def analyze(self, query: str) -> str:
        """
        分析用户输入的查询，智能调用相应工具
        """
        try:
            result = self.agent.invoke(query)
            return result
        except Exception as e:
            error_msg = f"分析失败: {str(e)}"
            return error_msg

# 主程序示例
def main():
    """主程序入口"""
    # 创建Agent实例
    fofa_agent = FOFAAnalysisAgent(verbose=True)
    
    # 测试查询
    # test_query = 'banner="aurora" && (banner="AD" || banner="ADC")'
    
    while True:
        user_input = input("\n> ").strip()
        if user_input:
            result = fofa_agent.analyze(user_input)
            output = result['output'] if isinstance(result, dict) else result
            print(f"\n{output}")

if __name__ == "__main__":
    main()