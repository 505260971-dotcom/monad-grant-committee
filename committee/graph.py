"""LangGraph 编排：4 个 Agent 并行开圆桌。

图结构：

        ┌── pm ───────┐
        ├── tech ─────┤
START ──┤              ├──> 汇总 ──> 是否还需要再辩一轮？
        ├── token ────┤              │
        └── compliance┘              是 → 回到四个 Agent（第二轮）
                                     否 → 定稿 → 放款计划

★ 为什么用「并行」而不是让 4 个 Agent 依次发言：
  串行 4 次模型调用 = 4 倍等待。现场 10 分钟路演，你等不起。
  并行之后，一轮的耗时 ≈ 一次调用的耗时。
"""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.graph import END, START, StateGraph

from committee.llm import agent_speak
from committee.prompts import build_prompt
from committee.state import WorkOrder, new_work_order

ROLES = ["pm", "tech", "token", "compliance"]


# ---------------------------------------------------------------- 节点

def _make_agent_node(role: str):
    """生成一个 Agent 节点。每个角色一份，闭包里记住自己是谁。"""

    def node(state: WorkOrder) -> dict[str, Any]:
        rnd = state["current_round"]
        prev = state.get("speeches", [])

        system_prompt, user_prompt = build_prompt(
            role=role,
            application=state["application"],
            round_no=rnd,
            prev_speeches=prev,
        )

        speech = agent_speak(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            application=state["application"],
            round_no=rnd,
            prev_speeches=prev,
        )

        # ★ 注意这里：speeches 标了 operator.add，
        # 所以返回列表是「追加」，4 个 Agent 同时写不会互相覆盖。
        return {
            "speeches": [speech],
            "trace": [f"R{rnd} {role} 发言：{speech['score']}分 {speech['verdict']}"],
        }

    return node


def consensus_node(state: WorkOrder) -> dict[str, Any]:
    """汇总节点：算平均分，判断是否已达成共识。"""
    rnd = state["current_round"]
    this_round = [s for s in state["speeches"] if s["round"] == rnd]
    if not this_round:
        return {}

    avg = sum(s["score"] for s in this_round) / len(this_round)
    scores = [s["score"] for s in this_round]
    spread = max(scores) - min(scores)

    # ★ 达成共识的判定（这里的设计直接决定 Demo 好不好看）
    #
    # 规则：意见高度一致（分差 ≤2）时收敛。
    # 但出现「一票否决」时，不立刻收敛 —— 反而要再辩一轮，
    # 让其他评委有机会跟进或反驳。这才是真实圆桌的样子，
    # 也是全场最抓人的地方：「合规评委因为代币评委的一句话改了结论」。
    #
    # 如果轮数已经用满，就交给 verdict 节点定稿。
    has_veto = any(s["score"] <= 3 for s in this_round)
    rounds_left = state["current_round"] < state["max_rounds"]

    if has_veto:
        agreed = not rounds_left          # 有否决时，尽量再辩一轮
    else:
        agreed = spread <= 2              # 无否决时，分差小就收敛

    note = "存在一票否决，需再辩一轮" if (has_veto and rounds_left) else (
        "已收敛" if agreed else "仍需辩论")

    return {
        "final_score": round(avg, 1),
        "consensus": agreed,
        "trace": [f"R{rnd} 汇总：均分 {avg:.1f}，分差 {spread}，{note}"],
    }


def next_round_node(state: WorkOrder) -> dict[str, Any]:
    """进入下一轮辩论。"""
    return {
        "current_round": state["current_round"] + 1,
        "trace": [f"—— 进入第 {state['current_round'] + 1} 轮辩论 ——"],
    }


def verdict_node(state: WorkOrder) -> dict[str, Any]:
    """定稿：给出最终结论和放款计划。"""
    rnd = state["current_round"]
    this_round = [s for s in state["speeches"] if s["round"] == rnd]
    avg = sum(s["score"] for s in this_round) / len(this_round) if this_round else 0
    has_veto = any(s["score"] <= 3 for s in this_round)

    # 决策优先级：一票否决 > 平均分阈值
    if has_veto:
        verdict = "reject"
        vetoers = [s for s in this_round if s["score"] <= 3]
        reason = f"被 {vetoers[0]['role']} 一票否决"
    elif avg >= state["pass_threshold"]:
        verdict = "approve"
        reason = f"平均分 {avg:.1f} 达到阈值 {state['pass_threshold']}"
    elif avg >= state["pass_threshold"] - 1.5:
        verdict = "revise"
        reason = f"平均分 {avg:.1f} 未达标但接近，建议修改后重提"
    else:
        verdict = "reject"
        reason = f"平均分 {avg:.1f} 显著低于阈值"

    # 通过才生成放款计划，否则为空
    plan: list[dict[str, Any]] = []
    if verdict == "approve":
        for i, m in enumerate(state["application"].get("budget", []), start=1):
            plan.append({
                "milestone": m["milestone"],
                "usdc": m["usdc"],
                "stage": i,
                "status": "locked",
            })

    return {
        "final_verdict": verdict,
        "final_score": round(avg, 1),
        "release_plan": plan,
        "trace": [f"定稿：{verdict}（{reason}）"],
    }


# ---------------------------------------------------------------- 路由

def route_after_consensus(state: WorkOrder) -> str:
    """汇总之后往哪走。"""
    if state.get("consensus"):
        return "verdict"
    if state["current_round"] >= state["max_rounds"]:
        return "verdict"
    return "next_round"


# ---------------------------------------------------------------- 建图

def build_graph():
    g = StateGraph(WorkOrder)

    for role in ROLES:
        g.add_node(role, _make_agent_node(role))

    g.add_node("consensus", consensus_node)
    g.add_node("next_round", next_round_node)
    g.add_node("verdict", verdict_node)

    # 扇出：START 同时连到 4 个 Agent，它们并行执行
    for role in ROLES:
        g.add_edge(START, role)
        g.add_edge(role, "consensus")   # 扇入：等 4 个都完成才进汇总

    g.add_conditional_edges(
        "consensus",
        route_after_consensus,
        {"verdict": "verdict", "next_round": "next_round"},
    )

    # 下一轮：回到 4 个 Agent，再扇出一次
    for role in ROLES:
        g.add_edge("next_round", role)

    g.add_edge("verdict", END)

    return g.compile()


# ---------------------------------------------------------------- 对外接口

async def run_committee(application: dict, max_rounds: int = 2,
                        pass_threshold: float = 6.0) -> WorkOrder:
    """跑完一场评审，返回完整工单。"""
    graph = build_graph()
    init = new_work_order(application, max_rounds, pass_threshold)
    return await graph.ainvoke(init)


def run_committee_sync(application: dict, max_rounds: int = 2,
                       pass_threshold: float = 6.0) -> WorkOrder:
    """同步版本，方便脚本里直接调。"""
    return asyncio.run(run_committee(application, max_rounds, pass_threshold))
