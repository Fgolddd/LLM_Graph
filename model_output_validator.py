"""
model_output_validator.py

用于对大模型（LangGraph 最终状态）产出的结构化结果进行业务规则检查与轻量纠正。
模块化设计：对外仅暴露 validate_and_correct 与 simple_infer_maptype 两个入口。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import copy
import json

# 业务主题与受限取值
ALLOWED_THEMES = [
    "指挥", "禁毒", "治安", "要素管控", "风险统计", "处置态势", "热点巡逻", "专项治理", "勤务管理", "矛盾纠纷"
]

ALLOWED_MAPTYPES = [
    "散点图", "热力图", "聚合点统计分布图", "统计分布图"
]

# 主题 -> maptype 的启发式默认映射（可根据业务继续完善）
THEME_DEFAULT_MAPTYPE = {
    "禁毒": "热力图",
    "热点巡逻": "热力图",
    "风险统计": "统计分布图",
}

# poi 关键词 -> maptype 的启发式
POI_HINTS_TO_MAPTYPE = [
    ("聚合", "聚合点统计分布图"),
    ("点位", "散点图"),
    ("散点", "散点图"),
    ("热点", "热力图"),
]


def _ensure_dict(x: Any) -> Dict[str, Any]:
    """将字符串 JSON 转为字典；若已是字典则原样返回，否则返回空字典。"""
    if isinstance(x, dict):
        return x
    if isinstance(x, str):
        try:
            return json.loads(x)
        except Exception:
            return {}
    return {}


def simple_infer_maptype(entities: Dict[str, Any]) -> Optional[str]:
    """基于 theme 与 poi 关键词进行 maptype 的简单推断。"""
    theme_vals = entities.get("theme") or []
    if isinstance(theme_vals, list):
        for t in theme_vals:
            if t in THEME_DEFAULT_MAPTYPE:
                return THEME_DEFAULT_MAPTYPE[t]
    elif isinstance(theme_vals, str) and theme_vals in THEME_DEFAULT_MAPTYPE:
        return THEME_DEFAULT_MAPTYPE[theme_vals]

    # 关键词启发式
    poi_vals = entities.get("poi") or []
    if isinstance(poi_vals, str):
        poi_vals = [poi_vals]
    for v in poi_vals:
        for kw, mt in POI_HINTS_TO_MAPTYPE:
            if kw in str(v):
                return mt

    return None


def validate_and_correct(model_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    对模型产出的整体结果进行校验与轻量纠正。

    入参 model_output 预期结构（宽松）：
    {
      "original_query": str,
      "refined_query": Optional[str],
      "structured_intent": Union[dict,str],  # 内含 entities 字段
      ...
    }

    返回：
    {
      "is_valid": bool,
      "issues": [ {"code", "message", "severity"} ],
      "corrected_output": Dict,  # 尝试应用轻量修正后的 output
      "suggested_fixes": Dict,   # 仅包含建议修正的差异（如 entities 层面）
    }
    """
    report: Dict[str, Any] = {
        "is_valid": True,
        "issues": [],
        "corrected_output": copy.deepcopy(model_output),
        "suggested_fixes": {},
    }

    # 解析 structured_intent
    structured = _ensure_dict(model_output.get("structured_intent"))
    entities = _ensure_dict(structured.get("entities"))

    if not entities:
        report["is_valid"] = False
        report["issues"].append({
            "code": "NO_ENTITIES",
            "severity": "error",
            "message": "未发现 entities 或解析失败。",
        })
        # 直接返回，无法深入校验
        return report

    suggested_entities = copy.deepcopy(entities)

    # 1) theme 校验
    theme_vals = suggested_entities.get("theme")
    if theme_vals:
        if isinstance(theme_vals, list):
            invalids = [v for v in theme_vals if v not in ALLOWED_THEMES]
            if invalids:
                report["is_valid"] = False
                report["issues"].append({
                    "code": "INVALID_THEME",
                    "severity": "warning",
                    "message": f"存在不在候选内的 theme: {invalids}",
                })
                # 尝试移除非法 theme
                suggested_entities["theme"] = [v for v in theme_vals if v in ALLOWED_THEMES]
                if not suggested_entities["theme"]:
                    suggested_entities.pop("theme", None)
        elif isinstance(theme_vals, str) and theme_vals not in ALLOWED_THEMES:
            report["is_valid"] = False
            report["issues"].append({
                "code": "INVALID_THEME",
                "severity": "warning",
                "message": f"theme 不在候选内: {theme_vals}",
            })
            suggested_entities.pop("theme", None)

    # 2) maptype 校验与推断
    map_vals = suggested_entities.get("maptype")
    def _filter_allowed(vals: List[str]) -> List[str]:
        return [v for v in vals if v in ALLOWED_MAPTYPES]

    need_infer = False
    if map_vals is None:
        need_infer = True
    elif isinstance(map_vals, list):
        kept = _filter_allowed(map_vals)
        if kept != map_vals:
            report["issues"].append({
                "code": "INVALID_MAPTYPE",
                "severity": "warning",
                "message": f"存在非法 maptype: {map_vals}; 已过滤为 {kept}",
            })
        if kept:
            suggested_entities["maptype"] = kept
        else:
            suggested_entities.pop("maptype", None)
            need_infer = True
    elif isinstance(map_vals, str):
        if map_vals not in ALLOWED_MAPTYPES:
            report["issues"].append({
                "code": "INVALID_MAPTYPE",
                "severity": "warning",
                "message": f"maptype 不在候选内: {map_vals}",
            })
            suggested_entities.pop("maptype", None)
            need_infer = True
        else:
            suggested_entities["maptype"] = [map_vals]
    else:
        # 非法类型
        suggested_entities.pop("maptype", None)
        need_infer = True

    if need_infer:
        inferred = simple_infer_maptype(suggested_entities)
        if inferred:
            suggested_entities["maptype"] = [inferred]
            report["issues"].append({
                "code": "INFERRED_MAPTYPE",
                "severity": "info",
                "message": f"未提供或非法 maptype，已根据 theme/poi 推断为: {inferred}",
            })
        else:
            report["is_valid"] = False
            report["issues"].append({
                "code": "MISSING_MAPTYPE",
                "severity": "warning",
                "message": "缺少 maptype，且无法根据 theme/poi 推断。",
            })

    # 3) 关键字段存在性检查（示例：有 maptype 时建议具备 location 或 poi 之一）
    if "maptype" in suggested_entities:
        has_loc = bool(suggested_entities.get("location"))
        has_poi = bool(suggested_entities.get("poi"))
        if not (has_loc or has_poi):
            report["is_valid"] = False
            report["issues"].append({
                "code": "INSUFFICIENT_CONTEXT",
                "severity": "warning",
                "message": "存在 maptype 时建议提供 location 或 poi 至少其一。",
            })

    # 应用建议修正到 corrected_output
    corrected = report["corrected_output"]
    corrected_structured = _ensure_dict(corrected.get("structured_intent"))
    corrected_structured["entities"] = suggested_entities
    corrected["structured_intent"] = corrected_structured

    # suggested_fixes 仅返回 entities 差异
    report["suggested_fixes"] = {"entities": suggested_entities}

    return report

