import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any

# 从 prompts.py 模块中导入 Prompt 字符串
from prompts import QUERY_REFINEMENT_PROMPT, INTENT_RECOGNITION_PROMPT

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化客户端，适配 Qwen 模型服务
# 建议从环境变量 `DASHSCOPE_API_KEY` 读取密钥，更安全
client = OpenAI(
    api_key='sk-ea94c8b67bab4e2fbab4adc247690851',
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

def refine_query(query: str) -> str:
    """
    使用 LLM 将模糊查询精炼为精确表达。
    """
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": QUERY_REFINEMENT_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=0.0
        )
        refined_query = response.choices[0].message.content
        return refined_query.strip() if refined_query else ""
    except Exception as e:
        print(f"[LLM Client Error - Refine Query] An error occurred: {e}")
        return f"Error refining query: {e}"

def get_structured_intent(query: str) -> Dict[str, Any]:
    """
    使用 LLM API 分析用户查询，并返回结构化的意图和实体。
    """
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": INTENT_RECOGNITION_PROMPT},
                {"role": "user", "content": query}
            ],
            temperature=0.0
        )
        llm_output_str = response.choices[0].message.content
        if not llm_output_str:
            return {"error": "LLM returned an empty response."}
        
        if llm_output_str.startswith('```json'):
            llm_output_str = llm_output_str[7:-3].strip()

        structured_data = json.loads(llm_output_str)
        return structured_data
    except Exception as e:
        print(f"[LLM Client Error - Get Intent] An error occurred: {e}")
        return {"error": str(e)}
