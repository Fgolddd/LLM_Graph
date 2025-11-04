import json
from typing import Dict, Any

# 1. 导入 LLM 客户端的两个核心功能
# ==============================================================================
from llm_client import refine_query, get_structured_intent

# 2. 主处理函数 (采用两步流程)
# ==============================================================================

def process_query(query: str) -> Dict[str, Any]:
    """
    处理用户查询的完整流程：
    1. 将模糊查询精炼为精确表达。
    2. 从精确表达中提取结构化的意图和实体。
    """
    if not query:
        return {"error": "查询不能为空。"}

    # --- 步骤 1: 查询精炼 ---
    print(f"[步骤 1] 正在精炼模糊查询...\n  原始查询: '{query}'")
    refined_query = refine_query(query)
    if "Error refining query" in refined_query or not refined_query:
        return {"original_query": query, "error": refined_query or "精炼查询时返回为空。"}
    print(f"  精确表达: '{refined_query}'")

    # --- 步骤 2: 意图识别 ---
    print(f"[步骤 2] 正在从精确表达中提取意图与实体...")
    recognition_result = get_structured_intent(refined_query)

    # --- 封装最终结果 ---
    final_output = {
        "original_query": query,
        "refined_query": refined_query,
        **recognition_result
    }

    return final_output

# 3. 示例用法
# ==============================================================================
if __name__ == '__main__':
    # 在运行前，请确保您已经在 .env 文件中配置了 DASHSCOPE_API_KEY
    
    # 使用您提供的模糊查询作为测试用例
    fuzzy_queries = [
        "制作一张康美村涉毒警情分布图，只显示一类警情的具体点位",
        "我想知道铜陵镇涉毒场所的分布位置，在地图上显示",
        "漳州市钟法路警务区内工厂的具体位置"
    ]

    for i, query in enumerate(fuzzy_queries):
        print(f"--- 正在处理查询 {i+1} ---")
        result = process_query(query)
        print("--- 最终结构化输出 ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
