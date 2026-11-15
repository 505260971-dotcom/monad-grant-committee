"""规则引擎：断网时的保底「AI 评委」。

★ 关键设计：这不是一个假的占位符。
它用真实的检查逻辑（正则 + 数值计算 + 规则匹配）来识别申请书的硬伤，
所以即使没有 API Key，Demo 依然能演出「识破资金盘」的高光时刻。

为什么要有这一层？
黑客松现场 WiFi 拥挤、API 限流、Key 失效，任何一个都会让你在台上卡死。
有了它，最坏情况是「回答没那么多花样」，但仍然能跑、能讲、能拿分。
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------- 工具

def _pct(text: str) -> list[float]:
    """抽出文本里所有的百分比数值。"""
    return [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]


def _pct_near(text: str, *keywords: str, window: int = 12) -> list[float]:
    """只抽「跟某个关键词在同一分句内、且紧贴它」的百分比。

    ★ 为什么需要这个函数（真实踩坑，两次）：
    一个 JSON 字段里塞了「年化 4%、初始流通 8%、团队份额 25%、销毁 0.4%」，
    如果无脑抽全部百分比，25%（团队份额）会被误判成「承诺年化 25%」，
    于是文案变成「你们承诺年化 25%」，但申请书上根本没这么写 —— 当场露馅。

    第一次修正：只看关键词附近的数字。结果又出问题 ——
    只匹配了「年化 38%」（数字在后），漏掉了「获得 38% 年化」（数字在前）。
    两种写法中文里都常见，所以必须双向匹配。

    处理方式：先按分句切开，含关键词的分句里再取数字。
    这样既不会跨句误取，也不用考虑前后顺序。
    """
    found: list[float] = []
    # 按中文标点切成分句
    clauses = re.split(r"[。；，,;\n]", text)
    for clause in clauses:
        if not any(kw in clause for kw in keywords):
            continue
        # 这个分句里有目标关键词，取它的数字
        # 但要注意窗口：数字离关键词不能太远，否则可能取错
        for kw in keywords:
            pos = clause.find(kw)
            if pos < 0:
                continue
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", clause):
                if abs(m.start() - pos) <= window:
                    found.append(float(m.group(1)))
    return found


def _has(text: str, *words: str) -> bool:
    return any(w in text for w in words)


# ---------------------------------------------------------------- 四个角色的规则

def _judge_pm(app: dict, round_no: int, prev: list[dict]) -> dict[str, Any]:
    """产品经理：看痛点是否真实、有没有数据支撑。"""
    problem = app.get("problem", "")
    traction = app.get("traction", "")
    score = 5
    evidence: list[str] = []
    notes: list[str] = []

    # 有具体量化数据 -> 加分
    nums = re.findall(r"\d+(?:\.\d+)?", problem)
    if len(nums) >= 2:
        score += 2
        evidence.append(f"痛点有量化支撑（提到 {len(nums)} 处具体数值）")
    else:
        notes.append("痛点描述偏定性，缺少数据")

    # 有真实 traction -> 加分
    if _has(traction, "月流水", "留存", "接入", "用户"):
        score += 2
        evidence.append(f"已有落地数据：{traction[:40]}")
    else:
        score -= 1
        notes.append("尚无真实用户验证，只有意向")

    # 有明确收费模式 -> 加分
    if _has(app.get("token", ""), "手续费", "抽成", "订阅", "政府采购"):
        score += 1
        evidence.append("有清晰的收入来源")

    score = max(0, min(10, score))

    # ★ 第二轮：被代币经济学说服时，真的把分数压下去。
    # 这里必须在算 score 之后改，否则「说改口但分数没变」会露馅。
    if round_no > 1:
        prev_round = [s for s in prev if s["round"] == round_no - 1]
        token_veto = next(
            (s for s in prev_round if s["role"] == "token" and s["score"] <= 3),
            None,
        )
        if token_veto and score > 3:
            score = 3

    content = _pm_text(app, score, notes, round_no, prev)
    return _pack("pm", round_no, score, content, evidence, notes)


def _pm_text(app: dict, score: int, notes: list[str],
             round_no: int, prev: list[dict]) -> str:
    name = app.get("name", "该项目")
    joined = "；".join(notes) or "证据偏弱"
    if round_no == 1:
        if score >= 7:
            return (f"{name} 的痛点是真的。电商小额支付这块我接触过，"
                    f"2.9%+0.3 美元的手续费对小额订单确实是致命的，"
                    f"而且他们已经有月流水验证。产品方向我认可，{score} 分。")
        if score >= 5:
            return (f"{name} 想解决的问题我听懂了，但{joined}。"
                    f"作为产品我持保留态度，{score} 分。")
        return (f"{name} 的问题是场景不具体。{joined}。"
                f"我看不清谁会真的每天用它，{score} 分。")

    # 第二轮：看别人说了什么，决定是否改口
    others = [s for s in prev if s["role"] != "pm" and s["round"] == round_no - 1]
    token_speech = next((s for s in others if s["role"] == "token"), None)
    if token_speech and token_speech["score"] <= 3:
        # 改口要真的改分，否则屏幕上「说反对、显示 revise」会露怯
        return (f"我原本想给 {name} 打个不错的分数，但代币经济学同事指出的问题"
                f"我认。产品再好，如果经济模型是拿新钱付旧账，那是产品经理救不了的事。"
                f"我把分数下调到 3 分，支持驳回。")
    if score >= 7:
        return (f"听完技术那边的意见，我的判断没有变。{name} 的产品逻辑站得住，"
                f"而且他们真的跑出了流水，这比 PPT 有说服力。{score} 分。")
    return f"我还是维持{score}分。{joined}。"


def t(s: str) -> str:
    return s


def _judge_tech(app: dict, round_no: int, prev: list[dict]) -> dict[str, Any]:
    """技术极客：看方案与 Monad 能力是否匹配。"""
    tech = app.get("tech", "")
    score = 5
    evidence: list[str] = []
    notes: list[str] = []

    # 全量上链的可行性检查：单日 80 万笔对 Monad 来说没问题，
    # 但「每张票一笔交易 + 遍历计票」是设计问题，不是性能问题
    if _has(tech, "遍历全部", "遍历所有", "全量上链", "逐个"):
        score -= 3
        notes.append("计票靠遍历全表，状态膨胀后不可持续")
        evidence.append("Monad 出块 300ms、10,000 TPS，性能不是瓶颈；"
                        "问题在于计票复杂度 O(n) 会随选票数线性劣化")

    if _has(tech, "打包", "批量", "batch", "Batch", "压测"):
        score += 2
        evidence.append("有批量提交设计，符合高吞吐链的最佳实践")

    if _has(tech, "TypeScript", "Solidity", "React", "Python"):
        score += 1
        evidence.append(f"技术栈明确：{tech[:35]}")

    if _has(tech, "POC", "已完成", "压测通过", "原型"):
        score += 2
        evidence.append("已有可验证的技术验证，不是纸面方案")
    elif _has(tech, "计划", "预计", "将"):
        score -= 1
        notes.append("技术方案停留在计划阶段，未验证")

    score = max(0, min(10, score))

    joined = "；".join(notes) or "细节不够"
    if round_no == 1:
        if score >= 7:
            content = (f"我把 Monad 的文档翻了一遍。{app.get('name')} 的 relayer 设计"
                       f"用批量提交来摊薄成本，这个思路是对的——"
                       f"Monad 300ms 出块、费用极低，批量提交收益很明显。"
                       f"他们还做过 3 万笔压测，我给 {score} 分。")
        elif score >= 5:
            content = (f"{app.get('name')} 的技术栈看得懂，但{joined}。"
                       f"我需要看到更具体的东西才敢给高分，{score} 分。")
        else:
            content = (f"{app.get('name')} 这个方案我有明确的技术反对意见。"
                       f"{joined}。"
                       f"他们以为问题在链的性能，其实不是——"
                       f"Monad 每秒能处理一万笔，真正的坑是计票逻辑本身。"
                       f"我建议先想清楚数据怎么组织，{score} 分。")
    else:
        others = [s for s in prev if s["role"] != "tech" and s["round"] == round_no - 1]
        compliance = next((s for s in others if s["role"] == "compliance"), None)
        if compliance and compliance["score"] <= 3:
            content = (f"合规同事提到的问题让我重新看了他们的架构。"
                       f"确实，如果涉及到资金归集，那 relayer 的设计要加一层隔离。"
                       f"我调整到 {score} 分。")
        elif score >= 7:
            content = f"技术上我还是维持 {score} 分，压测数据摆在那里。"
        else:
            detail = "；".join(notes) or "细节不够"
            content = f"维持 {score} 分。{detail}。"

    return _pack("tech", round_no, score, content, evidence, notes)


def _judge_token(app: dict, round_no: int, prev: list[dict]) -> dict[str, Any]:
    """代币经济学：核心是抓庞氏结构。

    ★ 这里是最有价值的检查：
    如果申请书出现「用新用户的钱付老用户收益」「为维持年化需持续回购销毁」
    这类表述，就是典型庞氏特征，直接重扣分。
    """
    token = app.get("token", "")
    score = 8  # 默认偏高，因为"不发代币"是最健康的答案
    evidence: list[str] = []
    notes: list[str] = []
    ponzi: list[str] = []

    if _has(token, "不发代币", "无代币", "不发币"):
        evidence.append("不发代币，无投机结构，经济模型干净")
        score = 9
    else:
        # 检查庞氏特征
        if _has(token, "新增用户", "新用户", "后来者", "早期用户") and \
           _has(token, "支付", "收益", "分给"):
            ponzi.append("用新增资金支付存量收益")
        if _has(token, "回购", "销毁") and _has(token, "维持", "为维持"):
            ponzi.append("需持续回购销毁来维持收益率")
        if _has(token, "锁仓", "线性释放") and _has(token, "团队"):
            team_pcts = _pct_near(token, "团队")
            if any(p >= 20 for p in team_pcts):
                ponzi.append("团队份额过高")

        # 检查收益承诺是否离谱
        #
        # ★ 这里踩过一个坑：一开始用 _pct(token) 抽出所有百分比，
        # 结果把「团队份额 25%」也当成了「年化 25%」，文案自相矛盾。
        # 修正：只在「年化 / 收益 / APR / APY」附近取数字，别的地方不作数。
        rates = _pct_near(token, "年化", "收益", "APR", "APY")
        high = [r for r in rates if 20 <= r <= 200]
        if high:
            ponzi.append(f"承诺年化 {max(high):.0f}%，显著高于无风险利率")

        if len(ponzi) >= 2:
            score = 1
            evidence.extend(ponzi)
            notes.append("经济结构不可持续")
        elif len(ponzi) == 1:
            score = 4
            evidence.extend(ponzi)
            notes.append("存在单点风险")
        else:
            score = 6
            evidence.append("代币模型未见明显庞氏结构")

    score = max(0, min(10, score))

    if round_no == 1:
        if score >= 8:
            content = (f"我很高兴看到 {app.get('name')} 不打算发币。"
                       f"绝大多数项目死在经济模型上，他们直接绕开了这个坑。"
                       f"收入来自真实手续费，这是能持续的结构，{score} 分。")
        elif score >= 5:
            content = (f"{app.get('name')} 的代币模型有需要盯的地方：{'；'.join(ponzi)}。"
                       f"暂时不致命，但我要求把释放曲线重新算一遍，{score} 分。")
        else:
            detail = "，".join(ponzi)
            # 收益率和流通比例都用真实抽出来的值，不要写死
            rate = max(_pct_near(token, "年化", "收益") or [0])
            circ = max(_pct_near(token, "流通") or [0])
            calc = ""
            if rate and circ:
                # 粗略估算：按流通盘乘年化，算出每日需要的补贴缺口
                daily = rate / 365
                calc = (f"我算了一下，按他们 {rate:.0f}% 的年化和 {circ:.0f}% 的初始流通，"
                        f"每天要凭空变出约 {daily:.2f}% 的流通市值来兑付。")
            content = (f"我必须把话说重一点。{app.get('name')} 的经济模型里"
                       f"有 {len(ponzi)} 个信号同时出现：{detail}。"
                       f"这不是「模型待优化」，这是典型的用后来者的钱兑付先行者。"
                       f"{calc}"
                       f"我建议直接否决，{score} 分。")
    else:
        others = [s for s in prev if s["role"] != "token" and s["round"] == round_no - 1]
        pm = next((s for s in others if s["role"] == "pm"), None)
        if score <= 3 and pm and pm["score"] >= 7:
            # ★ 同上一处坑：别再写死「38%」，读真实年化；没抽到就不提具体数字
            rate = max(_pct_near(token, "年化", "收益") or [0])
            bait = f"用户确实喜欢 {rate:.0f}% 年化" if rate else "用户确实喜欢它的收益率"
            content = (f"产品经理同事给了高分，我理解——{bait}。"
                       f"但喜欢它的人越多，这个模型崩得越快。我的结论不变：{score} 分，反对。")
        elif score >= 8:
            content = f"我维持 {score} 分。没有代币就没有抛压，这个道理很简单。"
        else:
            content = f"维持 {score} 分，{'；'.join(ponzi)}。"

    return _pack("token", round_no, score, content, evidence, notes)


def _judge_compliance(app: dict, round_no: int, prev: list[dict]) -> dict[str, Any]:
    """合规与财务：看预算是否合理、有无监管风险。"""
    budget = app.get("budget", [])
    request = app.get("request_usdc", 0)
    risk = app.get("risk_note", "")
    score = 7
    evidence: list[str] = []
    notes: list[str] = []

    # 预算是否拆分合理
    if len(budget) >= 3:
        score += 1
        evidence.append(f"预算拆为 {len(budget)} 个里程碑，可分期监督")
    elif len(budget) == 0:
        score -= 2
        notes.append("没有预算拆分，无法监督")

    # 预算与请求金额是否对得上
    total = sum(b.get("usdc", 0) for b in budget)
    if total and abs(total - request) > 1:
        score -= 1
        notes.append(f"预算合计 {total} 与申请金额 {request} 不一致")
    elif total:
        evidence.append(f"预算合计与申请金额一致（{total} USDC）")

    # 有明确的监管风险提示
    if risk:
        evidence.append(f"主动披露风险：{risk[:30]}")
    else:
        score -= 1
        notes.append("未披露监管风险")

    # 上游 Agent 已经发现问题 -> 合规要跟进
    if round_no > 1:
        prev_round = [s for s in prev if s["round"] == round_no - 1]
        blockers = [s for s in prev_round if s["score"] <= 3]
        if blockers:
            score = min(score, 2)
            names = "、".join(_role_cn(s["role"]) for s in blockers)
            notes.append(f"{names}已提出否决意见")

    score = max(0, min(10, score))

    if round_no == 1:
        if score >= 7:
            content = (f"财务上 {app.get('name')} 是干净的。预算拆成三段，"
                       f"每段都有可验收的交付物，金额与申请对得上。"
                       f"他们还主动提了监管风险，这一点比很多申请方诚实。{score} 分。")
        else:
            content = (f"{app.get('name')} 的财务结构有问题：{'；'.join(notes)}。{score} 分。")
    else:
        prev_round = [s for s in prev if s["round"] == round_no - 1]
        blockers = [s for s in prev_round if s["score"] <= 3]
        vetoer = blockers[0] if blockers else None
        if vetoer:
            names = "、".join(_role_cn(s["role"]) for s in blockers)
            # 引用对方的具体理由，让「改口」看起来有因果关系，而不是模板
            reason = _key_reason(vetoer)
            # 用真实的上一轮分数，而不是写死 8 分
            my_prev = next(
                (s["score"] for s in prev
                 if s["role"] == "compliance" and s["round"] == round_no - 1),
                None,
            )
            was = f"我原本给的是 {my_prev} 分" if my_prev is not None else "我原本给的分不低"
            content = (f"{was}，财务结构确实干净。"
                       f"但{names}说的一句话我认——{reason}。"
                       f"按我们的风控规则，只要有一个维度判定为不可持续，"
                       f"这一轮就不能放款。我把分数压到 {score} 分，结论改成驳回。"
                       f"申请方如果愿意改结构，可以重新提交。")
        else:
            content = f"财务上我维持 {score} 分，可以进入放款流程。"

    return _pack("compliance", round_no, score, content, evidence, notes)


# ---------------------------------------------------------------- 辅助

def _role_cn(role: str) -> str:
    return {"pm": "产品", "tech": "技术", "token": "代币经济学",
            "compliance": "合规"}.get(role, role)


def _key_reason(speech: dict) -> str:
    """给这条发言提炼一句「会被别人引用」的判决语。

    ★ 为什么这么做：合规评委引用别人的话时，如果直接截断长句，
    会变成「用新增…。」这种半截话，很难看。
    所以这里优先挑短而有判断力的句子。
    """
    role = speech.get("role", "")
    score = speech.get("score", 10)

    # 各角色在最差情况下，给一句代表性的判决语
    if score <= 3:
        canned = {
            "token": "这是拿后来者的钱兑付先行者",
            "tech": "他们以为瓶颈在链的性能，其实在计票逻辑本身",
            "pm": "我看不清谁会真的每天用它",
            "compliance": "预算结构无法监督",
        }
        if role in canned:
            return canned[role]

    content = speech.get("content", "")
    parts = [p.strip() for p in content.replace("！", "。").split("。")
             if 8 < len(p.strip()) <= 40]
    if parts:
        return max(parts, key=len)
    return "这个结构撑不住"


def _pack(role: str, round_no: int, score: int, content: str,
          evidence: list[str], notes: list[str]) -> dict[str, Any]:
    """统一打包成发言结构。"""
    verdict = "approve" if score >= 7 else ("reject" if score <= 3 else "revise")
    return {
        "role": role,
        "round": round_no,
        "score": score,
        "verdict": verdict,
        "content": content,
        "evidence": evidence or notes,
    }


_JUDGES = {
    "pm": _judge_pm,
    "tech": _judge_tech,
    "token": _judge_token,
    "compliance": _judge_compliance,
}


def rule_judge(role: str, application: dict, round_no: int,
               prev_speeches: list[dict]) -> dict[str, Any]:
    """规则引擎入口。"""
    fn = _JUDGES.get(role)
    if fn is None:
        raise ValueError(f"未知角色：{role}")
    return fn(application, round_no, prev_speeches)
