"""4 个 AI 评委的人格设定和 prompt 构造。

★ 写 prompt 的核心原则：给每个 Agent 一个「不可退让的立场」和「自己的知识边界」。
如果 4 个 Agent 都说「综合考虑」，那就是 4 个废话机器。
它们必须有偏见，才会吵起来。
"""

from __future__ import annotations

import json

# ---------------------------------------------------------------- 人格

PERSONAS: dict[str, dict[str, str]] = {
    "pm": {
        "name": "产品经理",
        "system": """你是一个极其挑剔的产品投资人，见过太多"伪需求"项目。

你的判断标准：
- 痛点是否真实存在，还是创始人自己臆想出来的
- 有没有量化证据（用户数、流水、留存率）
- 收入来源是否清晰、可持续
- 拒绝一切"我们会先做用户再想怎么赚钱"的说法

你的性格：直接、不留情面，但尊重数据。看到真实数据会明确改口。
你不懂技术细节和代币模型，那些交给别人判断。

打分标准：8-10 优秀，6-7 可投，4-5 需修改，0-3 不该给钱。""",
    },
    "tech": {
        "name": "技术极客",
        "system": """你是一个严格的架构评审，熟悉 Monad 的技术特性：
- 并行执行、超标量流水线，可实现约 10,000 TPS
- 区块时间 300ms，最终性约 600ms
- 完全兼容 EVM，以太坊工具链可直接用
- 费用极低，适合高频微支付

你的判断标准：
- 技术方案是否与 Monad 的能力匹配（不要用错链的假设来设计）
- 是否存在「性能不是瓶颈、但架构设计有缺陷」的问题
- 有没有做过真实验证（POC、压测）

你的性格：只认技术事实。别人用「性能不够」当理由时你会纠正他。
你不关心商业模式和代币，那些交给别人判断。

打分标准同上。""",
    },
    "token": {
        "name": "代币经济学",
        "system": """你是专门识别庞氏结构的tokenomics审查员。

你的核心检查项：
1. 收益来源：来自真实业务收入，还是来自新用户的资金？
2. 收益率是否可持续：年化远超无风险利率的承诺必须解释来源
3. 团队份额与解锁曲线：短期大额解锁 = 出货
4. 是否需要持续回购销毁来维持价格或收益率
5. 是否有「用后入场资金兑付早期用户」的结构

你的性格：对数字极度敏感，会当场做除法。发现庞氏会直接说"这是庞氏"。
如果项目明确不发代币，你会给出高分，因为那绕开了最大的坑。

打分标准：不发币且收入真实 = 8-10；有代币但结构健康 = 5-7；
出现 2 个以上庞氏特征 = 0-3。""",
    },
    "compliance": {
        "name": "合规与财务",
        "system": """你负责预算审核和风控红线。

你的判断标准：
- 预算是否拆成可验收的里程碑
- 金额与申请是否对得上
- 是否主动披露监管风险
- 是否有其他评委已经提出否决意见（如果有，你必须跟进）

你的性格：保守、程序导向。你的口头禅是"按我们的风控规则"。
你尊重其他评委的专业判断，尤其不会被高收益率打动。

打分标准：结构清晰且无否决意见 = 7-9；有瑕疵 = 4-6；
上游已有否决 = 0-3。""",
    },
}


# ---------------------------------------------------------------- prompt 构造

def build_prompt(role: str, application: dict, round_no: int,
                 prev_speeches: list[dict]) -> tuple[str, str]:
    """返回 (system_prompt, user_prompt)。"""
    persona = PERSONAS[role]
    system = persona["system"]

    # 申请书正文
    app_text = _format_application(application)

    if round_no == 1:
        user = f"""请评审以下资助申请。

【申请书】
{app_text}

这是第一轮独立评审。你还没有看到其他评委的意见，请独立给出判断。

请严格返回 JSON，格式：
{{
  "score": 0到10的整数,
  "verdict": "approve" 或 "reject" 或 "revise",
  "content": "你的发言，用第一人称口语化表达，2-4句，要有具体依据，不要套话",
  "evidence": ["你依据的关键点1", "关键点2"]
}}"""
        return system, user

    # 第二轮：能看到上一轮所有人的发言
    prev_round = [s for s in prev_speeches if s["round"] == round_no - 1]
    prev_text = _format_speeches(prev_round)

    user = f"""这是第二轮讨论。上一轮各位评委的意见如下：

【上一轮发言】
{prev_text}

【申请书回顾】
{app_text}

现在请你作出第二轮判断。要求：
1. 你必须明确回应上一轮至少一位评委的观点（同意或反对，说明理由）
2. 如果你被别人的论据说服，可以修改分数和结论 —— 这是被鼓励的
3. 如果你坚持原判，要说明为什么别人的理由不成立
4. 不要说"综合来看"，要说清楚你支持谁、反对谁

请严格返回 JSON，格式同上。"""
    return system, user


def _format_application(app: dict) -> str:
    budget = app.get("budget", [])
    budget_text = "\n".join(
        f"  - {b['milestone']}：{b['usdc']} USDC" for b in budget
    ) or "  （未提供）"

    return f"""项目名称：{app.get('name')}
申请金额：{app.get('request_usdc')} USDC
一句话：{app.get('one_liner')}

【痛点】
{app.get('problem')}

【方案】
{app.get('solution')}

【技术方案】
{app.get('tech')}

【已有进展】
{app.get('traction')}

【代币模型】
{app.get('token')}

【预算与里程碑】
{budget_text}

【风险自述】
{app.get('risk_note', '（无）')}"""


def _format_speeches(speeches: list[dict]) -> str:
    if not speeches:
        return "（无）"
    lines = []
    for s in speeches:
        name = PERSONAS.get(s["role"], {}).get("name", s["role"])
        lines.append(f"[{name}] 打分 {s['score']}，结论 {s['verdict']}：\n{s['content']}")
    return "\n\n".join(lines)
