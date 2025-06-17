from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# 设置API凭证
api_key = "sk-test-3fa85f64b13d4e7b9c8a9dcbb70ad1a9"
base_url = "http://211.91.254.226:2440/v1"

# 初始化LLM
llm = ChatOpenAI(
    model="qwen",
    openai_api_key=api_key,
    openai_api_base=base_url
)

# 创建简单的消息调用
messages = [HumanMessage(content="你好，大模型！")]
response = llm.invoke(messages)

print(response.content)

# import os
# from openai import OpenAI

# client = OpenAI(
#     # 此为默认路径，您可根据业务所在地域进行配置
#     base_url="http://211.91.254.226:2440/v1",
#     # 从环境变量中获取您的 API Key
#     api_key="sk-test-3fa85f64b13d4e7b9c8a9dcbb70ad1a9",
# )

# # Non-streaming:
# print("----- standard request -----")
# completion = client.chat.completions.create(
#     # 指定您创建的方舟推理接入点 ID，此处已帮您修改为您的推理接入点 ID
#     model="qwen",
#     messages=[
#         {"role": "system", "content": "你是人工智能助手"},
#         {"role": "user", "content": "你好"},
#     ],
# )
# print(completion.choices[0].message.content)

# import os
# from openai import OpenAI


# client = OpenAI(
#     # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
#     api_key="sk-test-3fa85f64b13d4e7b9c8a9dcbb70ad1a9",
#     base_url="http://211.91.254.226:2440/v1",
# )

# completion = client.chat.completions.create(
#     # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
#     model="qwen",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "你是谁？"},
#     ],
#     # Qwen3模型通过enable_thinking参数控制思考过程（开源版默认True，商业版默认False）
#     # 使用Qwen3开源版模型时，若未启用流式输出，请将下行取消注释，否则会报错
#     # extra_body={"enable_thinking": False},
# )
# print(completion.model_dump_json())