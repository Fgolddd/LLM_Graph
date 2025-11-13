import json
import time

# 1. 导入编译好的 LangGraph 应用
# ==============================================================================
# app 实例封装了我们定义的所有节点和流程
from graph_processor import app
from model_output_validator import validate_and_correct

# 2. 主处理函数 (现在调用 LangGraph 应用)
# ==============================================================================

def process_query_with_graph(query: str):
    """
    使用 LangGraph 应用处理用户查询。
    """
    # 定义图的初始输入
    inputs = {"original_query": query}

    # --- 时间测量开始 ---
    start_time = time.time()
    
    # 调用 invoke 方法来执行整个图的流程
    # LangGraph 会自动在节点之间传递状态
    final_state = app.invoke(inputs)

    # --- 时间测量结束 ---
    end_time = time.time()
    duration = end_time - start_time
    
    # 从最终状态中提取所需信息进行格式化输出
    output = {
        "original_query": final_state.get("original_query"),
        "refined_query": final_state.get("refined_query"),
        "structured_intent": final_state.get("structured_intent"),
        "error": final_state.get("error"),
        "duration": f"{duration:.2f}s"  # 添加耗时信息
    }

    # --- 调用验证与轻量纠正模块 ---
    validation_report = validate_and_correct(output)
    output["validation_report"] = validation_report
    # 方便上游直接使用修正后的实体
    corrected_structured = validation_report.get("corrected_output", {}).get("structured_intent")
    if corrected_structured is not None:
        output["corrected_structured_intent"] = corrected_structured

    return output

# 3. 示例用法
# ==============================================================================
if __name__ == '__main__':
    # 在运行前，请确保您已配置好环境和 API 密钥
    
    fuzzy_queries = [
        "我想知道天河派出所药店的具体点位，生成一张地图",
        "我想知道漳州市东山县铜陵镇涉毒场所的分布位置",
        "广州市海珠区警务区内工厂的具体位置"
    ]

    for i, query in enumerate(fuzzy_queries):
        print(f"--- 正在处理查询 {i+1} ---")
        result = process_query_with_graph(query)
        print("--- 最终结构化输出 ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + "="*50 + "\n")
