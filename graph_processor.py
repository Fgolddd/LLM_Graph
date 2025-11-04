from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END

# 导入我们现有的 LLM 客户端功能
from llm_client import refine_query, get_structured_intent

# 1. 定义图的状态 (State)
# ==============================================================================
class GraphState(TypedDict):
    """
    定义了在图中流动的数据结构。

    Attributes:
        original_query: 用户最开始的输入。
        refined_query: 经过第一步 LLM 精炼后的查询。
        structured_intent: 经过第二步 LLM 分析后的结构化 JSON。
        error: 用于记录流程中任何步骤发生的错误。
    """
    original_query: str
    refined_query: str
    structured_intent: Dict[str, Any]
    error: str

# 2. 定义图的节点 (Nodes)
# ==============================================================================

def refine_query_node(state: GraphState) -> GraphState:
    """
    第一个节点：接收原始查询，调用 LLM 进行精炼。
    """
    print("[节点 1: 精炼查询] 正在运行...")
    original_query = state.get('original_query', '')
    
    refined_query = refine_query(original_query)
    
    if "Error refining query" in refined_query or not refined_query:
        print(f"  [错误] 精炼查询失败: {refined_query}")
        return {**state, "error": refined_query or "精炼查询时返回为空。"}
    
    print(f"  [成功] 精确表达: '{refined_query}'")
    return {**state, "refined_query": refined_query}

def get_intent_node(state: GraphState) -> GraphState:
    """
    第二个节点：接收精炼后的查询，调用 LLM 提取意图和实体。
    """
    print("[节点 2: 意图识别] 正在运行...")
    refined_query = state.get('refined_query', '')

    structured_intent = get_structured_intent(refined_query)

    if structured_intent.get("error"):
        print(f"  [错误] 意图识别失败: {structured_intent.get('error')}")
        return {**state, "error": structured_intent.get('error')}

    print(f"  [成功] 已提取结构化意图。")
    return {**state, "structured_intent": structured_intent}

# 3. 构建并编译图 (Graph)
# ==============================================================================

# 创建一个工作流图
workflow = StateGraph(GraphState)

# 将节点添加到图中
workflow.add_node("refine_query", refine_query_node)
workflow.add_node("get_intent", get_intent_node)

# 定义边的连接关系
workflow.set_entry_point("refine_query")
workflow.add_edge("refine_query", "get_intent")
workflow.add_edge("get_intent", END)

# 编译图，生成可执行的应用
app = workflow.compile()

print("LangGraph 应用已成功编译。")

