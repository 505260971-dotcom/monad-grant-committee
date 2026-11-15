"""教具 2：节点 return 的东西，是怎么进到工单里的。

这个脚本故意分两段：
第一段让你看到「多个并行节点写同一个覆盖格」会报错，
第二段修好它，看到正常运行。

这个「先撞墙再修」的顺序是故意的。记住报错长什么样，
比记住正确写法更有用 —— 因为在真实项目里你总是先看到报错。

跑法：
    <python> teaching/t2_graph_basics.py
"""

import operator
from typing import Annotated, TypedDict

from langgraph.errors import InvalidUpdateError
from langgraph.graph import END, START, StateGraph


# ============================================================
# 第一段：故意写错，看报错
# ============================================================

class BadBox(TypedDict, total=False):
    notes: Annotated[list[str], operator.add]
    last_speaker: str        # ← 覆盖格，但三个节点都要写它


def make_bad_node(name: str):
    def node(state: BadBox) -> dict:
        return {"notes": [f"{name}"], "last_speaker": name}
    return node


print("=" * 64)
print("第一段：三个并行节点都去写一个覆盖格，会发生什么？")
print("=" * 64)

g1 = StateGraph(BadBox)
for n in ["甲", "乙", "丙"]:
    g1.add_node(n, make_bad_node(n))
    g1.add_edge(START, n)
    g1.add_edge(n, END)
app1 = g1.compile()

try:
    app1.invoke({"notes": [], "last_speaker": ""})
    print("居然没报错？")
except InvalidUpdateError as e:
    print("\n报错了：")
    print(f"  {e}")
    print()
    print("→ 重点理解：它不是「随便挑一个留下」，而是直接拒绝执行。")
    print("→ LangGraph 宁可报错，也不替你猜谁该赢。")
    print("→ 这是好事：错误当场暴露，而不是埋成线上 bug。")


# ============================================================
# 第二段：修好它
# ============================================================

class GoodBox(TypedDict, total=False):
    notes: Annotated[list[str], operator.add]
    # 没有 last_speaker 了 —— 三个节点共用的字段只能放累加格


def make_good_node(name: str):
    def node(state: GoodBox) -> dict:
        return {"notes": [f"{name} 的发言"]}
    return node


print()
print("=" * 64)
print("第二段：把那个字段去掉，只留累加格")
print("=" * 64)

g2 = StateGraph(GoodBox)
for n in ["甲", "乙", "丙"]:
    g2.add_node(n, make_good_node(n))
    g2.add_edge(START, n)
    g2.add_edge(n, END)
app2 = g2.compile()

res = app2.invoke({"notes": []})
print(f"\nnotes = {res['notes']}")
print(f"→ {len(res['notes'])} 条，三个人的都在。")

print()
print("=" * 64)
print("那覆盖格还要不要用？要，但只给「一个写入者」用")
print("=" * 64)
print("""
  你项目里的实际情况：

  speeches  ← 4 个 Agent 同时写  → 必须累加  ✓ 已标 operator.add
  trace     ← 4 个 Agent 同时写  → 必须累加  ✓ 已标 operator.add
  final_score ← 只有 consensus 节点算  → 覆盖格，没问题
  final_verdict ← 只有 verdict 节点写   → 覆盖格，没问题

  判断口诀：
    同一轮里有几个节点写它？
      1 个  → 覆盖格，正常
      多个  → 必须 Annotated[..., operator.add]，否则报错
""")
