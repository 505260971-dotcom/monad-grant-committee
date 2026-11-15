"""教具 3：给投委会加第五个评委（法务）。

★ 这是最值得做的练习，因为它逼你看清「一个 Agent 是由几块拼起来的」。

加一个新评委，一共要动 3 个文件、5 个地方：
  1. prompts.py  → PERSONAS 加人格
  2. rules.py    → 加 _judge_legal 规则 + 注册进 _JUDGES
  3. graph.py    → ROLES 列表加 'legal'
  4. export_html.py → ROLE_CN / ROLE_ORDER 加中文名和排序
  (state.py 不用改！因为 speeches 是通用结构)

跑法：
    <python> teaching/t3_add_fifth_judge.py
"""

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

# ============================================================
# 这里把「加评委」简化成最小形态，让你看清本质
# ============================================================

class SimpleState(TypedDict, total=False):
    opinion: Annotated[list[str], operator.add]


# 原来的 4 个评委，每人一个规则函数
def judge_pm(app: dict) -> tuple[int, str]:
    return 7, "痛点真实，有流水验证"


def judge_tech(app: dict) -> tuple[int, str]:
    return 8, "架构与 Monad 能力匹配"


def judge_token(app: dict) -> tuple[int, str]:
    return 9, "不发代币，结构干净"


def judge_compliance(app: dict) -> tuple[int, str]:
    return 7, "预算拆分合理"


# ★ 新加的第五个评委
def judge_legal(app: dict) -> tuple[int, str]:
    return 4, "资金归集涉及当地牌照，需要额外合规意见"


JUDGES = {
    "产品": judge_pm,
    "技术": judge_tech,
    "代币": judge_token,
    "合规": judge_compliance,
    "法务": judge_legal,        # ← 只加这一行就注册进系统了
}


def make_node(name: str):
    def node(state: SimpleState) -> dict:
        score, text = JUDGES[name]({})
        return {"opinion": [f"[{name}] {score}分：{text}"]}
    return node


# ============================================================
# 建图：注意 ROLES 是遍历来的，加人不用改图结构
# ============================================================

ROLES = ["产品", "技术", "代币", "合规", "法务"]   # ← 这里加一项

print("=" * 66)
print("五个评委同时开会")
print("=" * 66)

g = StateGraph(SimpleState)
for r in ROLES:
    g.add_node(r, make_node(r))
    g.add_edge(START, r)
    g.add_edge(r, END)

app = g.compile()
res = app.invoke({"opinion": []})

for line in res["opinion"]:
    print(f"  {line}")

print()
print("=" * 66)
print("关键观察")
print("=" * 66)
print(f"""
  图结构一行没改。
  第 177-178 行那个 for 循环自动把新评委接进了扇出扇入：

      for role in ROLES:
          g.add_edge(START, role)
          g.add_edge(role, "consensus")

  所以「加评委」本质是「往 ROLES 列表里加个字符串」，
  图会自己长出新的分支。这就是用循环建图的好处。
""")

# ============================================================
# 顺便演示：新评委拉低了均分
# ============================================================

scores = [7, 8, 9, 7, 4]
print("=" * 66)
print("但加人会影响结论")
print("=" * 66)
print(f"  4 人时均分：{(7+8+9+7)/4:.2f}  → 达到阈值 6.0，通过")
print(f"  5 人时均分：{sum(scores)/len(scores):.2f}  → 仍然通过，但被拉低了")
print()
print("  法务给了 4 分，没到否决线（≤3），所以只是拉低均分。")
print("  如果它给 3 分以下，就会触发一票否决，结论直接变 reject。")
print()
print("  → 这就是为什么 verdict_node 里有这一行：")
print("       has_veto = any(s['score'] <= 3 for s in this_round)")
