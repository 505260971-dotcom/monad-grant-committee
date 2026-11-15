"""LLM 适配层：三层降级。

第 1 层：真模型（有 API Key 时）
第 2 层：本地小模型（如果有 Ollama）
第 3 层：规则引擎（断网时的保底，保证 Demo 永远能演）

★ 这是黑客松的铁律：演示绝不能依赖现场网络。
"""

from __future__ import annotations

import json
import os
from typing import Any

from committee.rules import rule_judge


# ---------------------------------------------------------------- 配置

def _api_config() -> dict[str, str] | None:
    """读取 API 配置。支持 DeepSeek / 通义 / OpenAI 兼容接口。"""
    key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        return None
    return {
        "key": key,
        "base": os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    }


MODE = os.getenv("COMMITTEE_MODE", "auto")  # auto / live / offline


# ---------------------------------------------------------------- 主入口

def agent_speak(role: str, system_prompt: str, user_prompt: str,
                application: dict, round_no: int,
                prev_speeches: list[dict]) -> dict[str, Any]:
    """让一个 Agent 发言，返回结构化结果。

    返回值格式固定，方便后面直接 merge 进工单：
    {"role", "round", "score", "verdict", "content", "evidence"}
    """
    if MODE != "offline":
        cfg = _api_config()
        if cfg:
            try:
                return _live_call(role, system_prompt, user_prompt, round_no)
            except Exception as exc:  # noqa: BLE001
                print(f"  [降级] {role} 的真实模型调用失败：{exc}")

    # 保底：规则引擎（永远可用）
    return rule_judge(role, application, round_no, prev_speeches)


def _live_call(role: str, system_prompt: str, user_prompt: str,
               round_no: int) -> dict[str, Any]:
    """真实模型调用。要求返回严格 JSON。"""
    from openai import OpenAI

    cfg = _api_config()
    assert cfg is not None

    client = OpenAI(api_key=cfg["key"], base_url=cfg["base"])
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
        timeout=45,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return {
        "role": role,
        "round": round_no,
        "score": int(data.get("score", 5)),
        "verdict": str(data.get("verdict", "revise")),
        "content": str(data.get("content", "")).strip(),
        "evidence": [str(x) for x in data.get("evidence", [])],
    }
