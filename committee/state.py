"""工单结构：所有 Agent 共享的一份会议纪要。

这就是 LangGraph 里的 State。你可以把它理解成一张 Excel：
每个 Agent 只能往自己的格子里写，但所有人都在看同一张表。

三个要点：
1. 普通字段 = 覆盖格（后写的盖掉先写的）
2. 标了 operator.add 的字段 = 累加格（谁写都往后追加，不会覆盖）
3. 忘了标 add 的列表字段 -> 第二个 Agent 写的时候会把第一个的发言冲掉
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class Speech(TypedDict):
    """一条发言。"""

    role: str          # 谁的发言：pm / tech / token / compliance
    round: int         # 第几轮
    score: int         # 打分 0-10
    verdict: str       # 结论：approve / reject / revise
    content: str       # 发言正文
    evidence: list[str]  # 引用了什么（RAG 来源 / 计算依据）


class WorkOrder(TypedDict, total=False):
    """整场评审的工单。"""

    # ---- 输入（invoke 时传进来，之后不再变）----
    application: dict[str, Any]     # 申请书全文
    max_rounds: int                 # 最多辩论几轮
    pass_threshold: float           # 平均分达到多少算通过

    # ---- 累加格：每一轮的发言全部保留 ----
    # Annotated[list, operator.add] 的意思是：
    # 节点 return 这个字段时，是「追加」而不是「覆盖」
    speeches: Annotated[list[Speech], operator.add]

    # ---- 覆盖格：永远只保留最新值 ----
    current_round: int
    consensus: bool                 # 是否已达成共识
    final_verdict: str              # approve / reject / revise
    final_score: float
    release_plan: list[dict[str, Any]]  # 放款计划（里程碑）
    payouts: list[dict[str, Any]]   # 链上放款记录

    # ★ 这个字段被 4 个并行 Agent 同时写，也必须是累加格。
    # 如果不标 operator.add，运行时会报：
    #   InvalidUpdateError: At key 'trace': Can receive only one value per step
    # 这是并行图最典型的一个坑，记下来。
    trace: Annotated[list[str], operator.add]


def new_work_order(application: dict, max_rounds: int = 2,
                   pass_threshold: float = 6.0) -> WorkOrder:
    """初始化一张干净的工单。

    注意：累加格必须初始化成空列表 []，否则 operator.add 会报错。
    """
    return WorkOrder(
        application=application,
        max_rounds=max_rounds,
        pass_threshold=pass_threshold,
        speeches=[],
        current_round=1,
        consensus=False,
        final_verdict="pending",
        final_score=0.0,
        release_plan=[],
        payouts=[],
        trace=[],
    )
