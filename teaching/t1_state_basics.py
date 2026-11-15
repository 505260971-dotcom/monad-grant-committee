"""教具 1：为什么有些格子会被冲掉，有些不会。

这个脚本不依赖 langgraph，就是普通的 Python。
跑完你会看到两种合并方式的差别 —— 这就是 state.py 里
那两个「累加格」为什么必须标 Annotated[list, operator.add] 的原因。

跑法：
    <python> teaching/t1_state_basics.py
"""

import operator
from typing import Annotated

# ============================================================
# 实验 A：普通字段（覆盖）
# ============================================================

print("=" * 62)
print("实验 A：4 个 Agent 同时写一个普通字段，会发生什么？")
print("=" * 62)

# 普通列表，没有标注
plain_box = []

# 模拟 4 个 Agent 往同一个格子里写
for agent_name in ["产品经理", "技术极客", "代币经济", "合规财务"]:
    plain_box = [agent_name]          # ← 注意：是「赋值」，不是「追加」

print(f"最后格子里剩下：{plain_box}")
print(f"数量：{len(plain_box)} 个")
print()
print("→ 4 个人都写了，但只有最后一个人留下了。前三个被冲掉了。")
print("→ 这就是「覆盖格」。如果 speeches 这么写，你就只剩一条发言。")


# ============================================================
# 实验 B：标了 operator.add 的字段（累加）
# ============================================================

print()
print("=" * 62)
print("实验 B：标了 Annotated[list, operator.add] 之后呢？")
print("=" * 62)


def merge_add(left: list, right: list) -> list:
    """这就是 operator.add 对两个列表做的事：拼接。"""
    return left + right


accum_box = []
for agent_name in ["产品经理", "技术极客", "代币经济", "合规财务"]:
    # 每个 Agent 只 return 自己那一条
    one_speech = [agent_name]
    # LangGraph 用 operator.add 把新值并进旧值
    accum_box = merge_add(accum_box, one_speech)

print(f"最后格子里剩下：{accum_box}")
print(f"数量：{len(accum_box)} 个")
print()
print("→ 4 个人的发言全在。这才是你想要的圆桌记录。")


# ============================================================
# 实验 C：真实的报错长什么样
# ============================================================

print()
print("=" * 62)
print("实验 C：如果忘了标 add，LangGraph 会怎么骂你")
print("=" * 62)

print("""
实测报错原文（项目里真的撞过）：

    langgraph.errors.InvalidUpdateError:
    At key 'trace': Can receive only one value per step.
    Use an Annotated key to handle multiple values.

翻译：'trace' 这个格子收到了不止一个值。
     请给它加 Annotated 标注，让它能装多个值。

这句话的意思是：你在同一「步」里，4 个 Agent 各写了一次 trace，
LangGraph 不知道该听谁的，于是直接报错 —— 它不敢替你猜。
""")


# ============================================================
# 实验 D：验证 operator.add 对列表真的就是拼接
# ============================================================

print("=" * 62)
print("实验 D：operator.add 到底是什么")
print("=" * 62)

print(f"[1,2] + [3]        = {operator.add([1, 2], [3])}")
print(f"'ab' + 'cd'        = {operator.add('ab', 'cd')!r}")
print(f"5 + 3              = {operator.add(5, 3)}")
print()
print("→ operator.add 就是 Python 里的加号。")
print("→ 对列表是拼接，对字符串是连接，对数字是求和。")
print("→ 所以 Annotated[list, operator.add] 的意思是：")
print("    「这个格子收到新值时，用加号合并，而不是盖掉旧值。」")
