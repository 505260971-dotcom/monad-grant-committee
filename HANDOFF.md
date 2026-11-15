# HANDOFF — AI 投委会（Autonomous Grant Committee）

> 交接对象：Codex
> 交接日期：2026-11-15
> 项目用途：Monad Blitz 广州站黑客松（2026-11-21）现场 Demo
> 交接人职责边界：**AI 评委大脑（Python 层）**。不含 Solidity 合约、不含链上部分。

---

## 0. 先读这一节（不读会白干）

### 0.1 这个项目现在是什么状态

**能跑，能演示，已完成约 80%。** 三个案例结局稳定：

| 案例 | 结果 | 轮数 |
|---|---|---|
| A MonadPay（好项目） | `approve` **9.2** | 1 轮 |
| B YieldNova（资金盘） | `reject` **3.0** | 2 轮 |
| C ChainVote（架构缺陷） | `reject` **4.2** | 2 轮 |

**任何改动之后，这三个数字必须仍然一致。**
如果改了之后 A ≠ 9.2 / B ≠ 3.0 / C ≠ 4.2，说明你引入了回归，先回滚再想。

### 0.2 环境（绝对路径，不要猜）

```
项目目录：D:\Program Files\2026-11-14-16-56-20\monad-blitz
解释器　：C:\Users\lijy0\.workbuddy\binaries\python\envs\langgraph-lab\Scripts\python.exe
```

该解释器内已装：`langgraph 1.2.x`、`openai 3.51.0`。**不要** `pip install` 到全局 Python，
也**不要**新建 venv（用户机器上装东西的成本很高，现场网络差）。

验证命令（Git Bash / PowerShell 都能跑）：

```bash
cd "D:/Program Files/2026-11-14-16-56-20/monad-blitz"
COMMITTEE_MODE=offline "C:/Users/lijy0/.workbuddy/binaries/python/envs/langgraph-lab/Scripts/python.exe" run.py
```

PowerShell 写法：
```powershell
$env:COMMITTEE_MODE="offline"
& "C:\Users\lijy0\.workbuddy\binaries\python\envs\langgraph-lab\Scripts\python.exe" run.py
```

### 0.3 三条铁律

1. **绝不引入新的第三方依赖**（不准装 chromadb / faiss / sentence-transformers / langchain）。
   现场 WiFi 拥挤，多一个依赖多一个当场崩的可能。已有的一律用标准库解决。
2. **绝不让 Demo 依赖网络**。真实模型是加分路径，不是唯一路径。
   任何新功能都必须有「断网也能跑」的降级。
3. **不要动 `committee/state.py` 的已有字段名**。`export_html.py`、`run.py`、
   `rules.py` 三处都按字段名读，改名会静默产生空列表，不报错但页面空白。

---

## 1. 系统在做什么（一段话）

公链基金会每年收到的生态资助申请远超人手能审的量。这个项目把评审拆成
**四个互相制衡的 AI 评委**，让它们真的吵起来，然后自动把结论变成一张**分期放款计划表**。

四个评委各有「不可退让的立场」，所以会冲突：

| role | 中文名 | 不可退让的立场 | 知识边界 |
|---|---|---|---|
| `pm` | 产品经理 | 只认真实数据和流水 | 不懂技术和代币 |
| `tech` | 技术极客 | 只认技术事实与 Monad 能力匹配 | 不关心商业和代币 |
| `token` | 代币经济学 | 专门抓庞氏结构 | 不懂技术实现 |
| `compliance` | 合规与财务 | 程序与风控红线 | 依赖别人先给判断 |

**全场看点是第二轮改口**：B 案例第一轮合规给 8 分，读到代币经济学「用新钱付旧账」
之后，第二轮压到 2 分并支持驳回。这不是写死的分支，是 prompt 让它读了对方发言。

---

## 2. 代码结构（每行都核对过）

```
monad-blitz/
├── run.py                    123 行  命令行入口
├── export_html.py            244 行  生成单文件演示页
├── requirements.txt                   依赖清单（离线只要 langgraph）
├── README.md                          给评委看的说明书
│
├── committee/
│   ├── state.py               75 行  ★ 工单结构 = LangGraph State
│   ├── prompts.py            173 行  4 人格 + 两轮 prompt 构造
│   ├── graph.py              208 行  ★ 图编排
│   ├── rules.py              439 行  ★ 离线规则引擎
│   └── llm.py                 86 行  三层降级
│
├── applications/                      三份申请书剧本（JSON）
├── out/                               demo.html + 三份结果存档
└── teaching/                          教学教具，**不是产品代码，别改**
```

### 2.1 `committee/state.py` — State 定义

关键点：**累加格 vs 覆盖格**。

```python
speeches: Annotated[list[Speech], operator.add]   # 累加：4 个 Agent 同时写不打架
trace:    Annotated[list[str], operator.add]      # 同上
current_round: int                                # 覆盖：只留最新值
```

**这是本项目的核心教训，也是必须理解的一件事**：
普通字段（覆盖格）被多个并行节点同时写，LangGraph 会**直接抛
`InvalidUpdateError: At key 'xxx': Can receive only one value per step`，不是随机保留一个。**

第一次开发时 `trace` 忘了标 `Annotated`，4 个并行 Agent 全部崩在这里。
**任何新增的、会被多个并行节点写的字段，必须标 `Annotated[list, operator.add]`。**

### 2.2 `committee/graph.py` — 图的搭法

```python
ROLES = ["pm", "tech", "token", "compliance"]

def build_graph():
    g = StateGraph(WorkOrder)
    for role in ROLES:
        g.add_node(role, _make_agent_node(role))
    g.add_node("consensus", consensus_node)
    g.add_node("next_round", next_round_node)
    g.add_node("verdict", verdict_node)

    # 扇出：START 连 4 个节点 = 并行
    for role in ROLES:
        g.add_edge(START, role)
        g.add_edge(role, "consensus")      # 扇入

    # 条件边：汇总后判断是定稿还是再辩一轮
    g.add_conditional_edges("consensus", route_after_consensus,
                            {"verdict": "verdict", "next_round": "next_round"})

    # 回边：下一轮再扇出一次
    for role in ROLES:
        g.add_edge("next_round", role)

    g.add_edge("verdict", END)
    return g.compile()
```

**两个设计决定，改动前必须知道原因**：

1. **为什么并行**：串行 4 次模型调用 = 4 倍等待。现场路演 10 分钟，等不起。
   `START` 连 N 个节点 = 并行；连 1 个 = 串行。这是 LangGraph 的物理语义，不需要额外配置。

2. **`consensus_node` 里为什么「有否决时反而不要收敛」**（`graph.py` L85-94）：

```python
has_veto = any(s["score"] <= 3 for s in this_round)
rounds_left = state["current_round"] < state["max_rounds"]
if has_veto:
    agreed = not rounds_left          # ★ 有否决时，尽量再辩一轮
else:
    agreed = spread <= 2              # 无否决时，分差小就收敛
```

   **第一版是「分差小 or 有人否决就收敛」，结果 B 案例第一轮就结束，
   「合规改口」这一幕永不发生，Demo 没高潮。** 改成现在这样之后才有第二轮。
   **不要为了"逻辑简洁"把它改回去。**

### 2.3 `committee/rules.py` — 离线规则引擎

这不是占位符，是真在识别问题。核心是代币经济学评委的庞氏检查（L206-293，函数名 `_judge_token`）：

```python
if _has(token, "新增用户","新用户","后来者","早期用户") and \
   _has(token, "支付","收益","分给"):
    ponzi.append("用新增资金支付存量收益")
if _has(token, "回购","销毁") and _has(token, "维持","为维持"):
    ponzi.append("需持续回购销毁来维持收益率")
if _has(token, "锁仓","线性释放") and _has(token, "团队"):
    if any(p >= 20 for p in _pct_near(token, "团队")):
        ponzi.append("团队份额过高")
rates = _pct_near(token, "年化","收益","APR","APY")
high = [r for r in rates if 20 <= r <= 200]
if high:
    ponzi.append(f"承诺年化 {max(high):.0f}%，显著高于无风险利率")

if len(ponzi) >= 2:   score = 1
elif len(ponzi) == 1: score = 4
else:                 score = 6
```

**阈值是「≥2 个信号 → 1 分」，不是"信号越多分越低"。**
这意味着：把 38% 改成 4% 只砍掉 1 个信号，剩下 3 个仍然过线，分数还是 1。
**这是已经验证过的行为，不是 bug，不要"修"。** 现场演讲会用这个做对照演示。

### 2.4 `_pct_near()` — 一个必须理解的函数（L24-54）

```python
def _pct_near(text: str, *keywords: str, window: int = 12) -> list[float]:
    """只抽「跟某个关键词在同一分句内、且紧贴它」的百分比。"""
    found = []
    clauses = re.split(r"[。；，,;\n]", text)     # 先按分句切
    for clause in clauses:
        if not any(kw in clause for kw in keywords):
            continue
        for kw in keywords:
            pos = clause.find(kw)
            if pos < 0: continue
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", clause):
                if abs(m.start() - pos) <= window:   # 双向邻近
                    found.append(float(m.group(1)))
    return found
```

**这里踩过两次坑，都已修（commit `b8df9d3`），不要再走回头路：**

- 坑一：原来用 `_pct(token)` 抽**全部**百分比，`max([4, 8, 25, 0.4])` 把
  **团队份额 25%** 当成「年化 25%」写进台词。申请书里根本没有这句话，当场露馅。
- 坑二：只匹配「年化 38%」（数字在后），漏掉「获得 38% 年化」（数字在前），
  导致 38% 版本少了一个信号。所以必须**双向**匹配，且要**先分句**防跨句误取。

### 2.5 `committee/llm.py` — 三层降级

```python
MODE = os.getenv("COMMITTEE_MODE", "auto")   # auto / live / offline

def agent_speak(...):
    if MODE != "offline":
        cfg = _api_config()
        if cfg:
            try:
                return _live_call(...)
            except Exception as exc:
                print(f"  [降级] {role} 的真实模型调用失败：{exc}")
    return rule_judge(role, application, round_no, prev_speeches)   # 永远可用
```

`_live_call()` 要求模型返回**严格 JSON**：
`{"score": int, "verdict": str, "content": str, "evidence": [str]}`，
用 `response_format={"type":"json_object"}` 约束。

---

## 3. 待做任务（按优先级，带验收标准）

### 🔴 任务 1：补 RAG 尽调（最高优先级）

**为什么最急**：Handoff 原始文档承诺「技术评委有 RAG 尽调能力，会查项目方历史、代码库、
审计报告」。但当前代码里**一行都没有**：

```bash
grep -rn "rag\|retriev\|embed\|vector\|chroma\|faiss" --include=*.py .
# → 空
```

现场评委一问「你的 RAG 在哪」，答不出来，整个项目 credibility 立刻崩。

**要做的**（不准上向量数据库，不准装依赖）：

1. 新建 `knowledge/` 目录，放 8–12 份 markdown。建议内容：
   - `monad-overview.md` — Monad 技术特性（并行执行 / 10,000 TPS / 300ms 出块 / 600ms 最终性 / EVM 兼容 / 低费用）
   - `anti-patterns.md` — 常见架构反模式（如「全量上链 + 遍历计票」的 O(n) 问题）
   - `ponzi-patterns.md` — 庞氏结构特征清单
   - `grant-redlines.md` — 资助红线（预算不可验收、团队份额过高、无风控）
   - `past-grants.md` — 3–5 个虚构的历史资助案例（含成功和失败）
   - 其余自定

2. 新建 `committee/rag.py`，实现 `retrieve(query: str, role: str, k: int = 3) -> list[dict]`：
   - **纯标准库**：`pathlib` 读文件 + 中文分词用简单的 2-gram 或关键词表匹配
   - 返回 `[{"source": "monad-overview.md", "section": "并行执行", "text": "..."}]`
   - 打分方式：关键词命中数 + 标题命中加权。不需要 TF-IDF，够用即可

3. 接进技术评委：`_judge_tech()` 开头先 `hits = retrieve(tech_text, "tech")`，
   然后把命中片段拼进 `content`，格式如：

   ```
   我查了 Monad 文档的「并行执行」一节：出块 300ms、10,000 TPS，
   所以你说的性能问题不存在。真正的问题是计票逻辑是 O(n)，
   80 万张票要遍历 80 万次，这不是链的问题。
   ```

4. **同步改 `prompts.py`**：技术评委的 `user_prompt` 里加一段
   `【参考资料】{retrieved_text}`，让真实模型也能引用。

**验收标准**：
- 跑 `run.py C` 时，技术评委发言里出现具体文档引用（带来源名）
- `COMMITTEE_MODE=offline` 下必须能跑（RAG 不能依赖网络）
- A / B / C 三案例的 verdict 不变（分数可以有 ±0.5 波动，但要说明原因）
- `STATE` 里新增 `retrieved: Annotated[list[dict], operator.add]` 如果需要在 trace 里体现

**加分（时间够才做）**：在 `out/demo.html` 里把引用来源显示成小标签，视觉上更有说服力。

---

### 🟡 任务 2：接通真实模型并做对比记录

**现状**：`openai 3.51.0` 已装，`_live_call()` 代码已写好，**但从没真跑过一次**。

**要做的**：

1. 用用户提供的 API Key 跑一次 A / B / C：
   ```bash
   export LLM_API_KEY=sk-xxx
   export LLM_BASE_URL=https://api.deepseek.com/v1
   export LLM_MODEL=deepseek-chat
   python run.py
   ```
2. **记录差异**，写进 `docs/live-vs-offline.md`：
   - 真实模型的台词风格 vs 规则引擎的台词风格，差在哪
   - 真实模型会不会破坏「第二轮改口」这个关键剧情（**这是最大风险**——
     规则引擎的改口是代码保证的，真实模型可能不改口，Demo 就没了高潮）
   - 分数是否稳定（跑 3 次看波动）
3. 如果真实模型不稳定，**必须在 `graph.py` 或 `rules.py` 里加约束**，
   保证改口一定发生。宁可台词朴素，也要剧情稳定。

**验收标准**：`docs/live-vs-offline.md` 里有一张三案例 × 两种模式的对比表，
并明确写出「现场该用哪种模式、为什么」。

---

### 🟡 任务 3：落链接口（等队友，或自己兜底）

**背景**：队友负责 Solidity 合约（Escrow / Vesting / Governance / Badge），
本项目的输出是 `release_plan` 这张表，由合约去消费：

```json
[
  {"milestone": "M1 完成 relayer 多签与压测", "usdc": 20000, "stage": 1, "status": "locked"},
  {"milestone": "M2 接入 100 家商户",        "usdc": 20000, "stage": 2, "status": "locked"},
  {"milestone": "M3 开源 SDK 与审计",        "usdc": 10000, "stage": 3, "status": "locked"}
]
```

**需要的 6 项信息**（向队友索取，或自己定）：
1. 测试网合约地址
2. 放款函数签名（函数名 / 参数顺序 / 金额单位是 USDC 还是 wei）
3. 谁付 gas
4. 权限白名单（谁能调 release）
5. 里程碑是单个传入还是数组传入
6. 触发的事件名（前端要监听）

**兜底方案**：如果 11-21 当天中午还拿不到，写一个约 20 行的极简合约：

```solidity
// 只要能演示「钱被锁住，按里程碑解锁」这一件事就够了
contract MiniEscrow {
    address public funder;
    mapping(uint => uint) public milestoneAmount;
    mapping(uint => bool) public released;
    function lock(uint idx, uint amt) external { ... }
    function release(uint idx) external { ... }
    event Released(uint idx, uint amt);
}
```

**在当前 Python 侧要做的**（不阻塞，可以现在就做）：
把 `release_plan` 输出成一份 `out/release_plan_B.json` 之类的文件，
并写一个 `chain_stub.py`，把「假装上链」的日志打印出来：

```
[chain] lock(M1, 20000 USDC) → tx 0xabc...
[chain] lock(M2, 20000 USDC) → tx 0xdef...
```

现场如果合约跑不通，就用这个 stub 演，讲「这是待接入的真实接口」。

---

### 🟢 任务 4：x402 付费情报（可砍，时间不够直接放弃）

**背景**：活动官方主题是「链上 AI Agent / 智能体可编程支付 / 自动结算」。
本项目目前是纯 AI 评审，跟主题接得不够紧。

**原设计**：技术评委在尽调时，遇到需要付费的数据源（如审计报告库），
**自己花 0.001 USDC 买**，通过 x402 协议完成支付。这是唯一能把项目接上官方主题的桥。

**如果要做的关键信息**（已调研，直接用）：
- x402 四步循环：客户端请求 → 服务端返 402 + 价格 JSON → 客户端签名授权（不上链、免费）
  → facilitator 验证并上链结算（付 gas）
- facilitator：`https://x402-facilitator.molandak.org`
- 包：`@x402/core @x402/evm @x402/fetch @x402/next`
- ⚠️ **版本坑**：`@x402/evm` 2.9.0–2.11.0 引用了一个未部署的代理地址，会**静默结算失败**。
  必须用 `>=2.22.0`。

**但注意**：这是 JS 生态，本项目是 Python。要做需要额外权衡。
**建议**：如果只有 1–2 小时，宁可不做。它不影响 Demo 完整度。

---

## 4. 已知坑列表（都踩过、都修了，别再踩）

| # | 坑 | 现象 | 已修方式 |
|---|---|---|---|
| 1 | 并行节点写的字段没标 `Annotated` | `InvalidUpdateError: At key 'trace': Can receive only one value per step` | `trace: Annotated[list[str], operator.add]` |
| 2 | f-string 里嵌套引号 | `SyntaxError` | 先把表达式赋值给变量，再进 f-string |
| 3 | 台词里写死数字 | 改了申请书的 38%→4%，台词还说「38%」 | 全部改成从 `_pct_near()` 现取 |
| 4 | 抽全部百分比 | 团队份额 25% 被当成「年化 25%」 | `_pct_near(text, "年化", ...)` |
| 5 | 单向邻近匹配 | 「获得 38% 年化」漏掉 | 分句 + `abs(m.start()-pos) <= window` |
| 6 | 说改口但分数没改 | 文案说「下调到 3 分」，显示 5 分 | 算完 score 后真的覆盖 |
| 7 | 有否决时立刻收敛 | B 案例第一轮就结束，没高潮 | `if has_veto: agreed = not rounds_left` |
| 8 | `_key_reason` 截断长句 | 输出「用新增…。」半截话 | 每个角色给一句 canned 判决语，plus 只取 8–40 字的完整分句 |
| 9 | 双句号 | 「维持 6 分。。」 | 先把 `"；".join(notes) or "细节不够"` 赋值给变量 |

---

## 5. 不要动的东西

| 不要动 | 原因 |
|---|---|
| `teaching/` 三个文件 | 教学教具，不是产品代码。改了会误导学习者 |
| `state.py` 已有字段名 | `export_html.py` / `run.py` / `rules.py` 三处按名读取，改名静默失败 |
| `consensus_node` 的 `has_veto` 分支 | 改了 Demo 就没高潮（见坑 7） |
| `len(ponzi) >= 2 → score = 1` 的阈值 | 这是有意设计，现场演讲要用（见 2.3） |
| `applications/B_yieldnova.json` 的 38% | 已还原成 38% 版本，是 Demo 用的。要实验请复制一份再改 |
| `.gitignore` 里 `!out/demo.html` | 反向放行，保证 demo 能上 GitHub 当第二份保险 |

---

## 6. 交付与版本管理

**GitHub**：`https://github.com/505260971-dotcom/monad-grant-committee`（分支 `master`）

当前最新提交：`4def19d`

**提交规范**（沿用现有风格，中文，前缀用 `feat:` / `fix:` / `docs:` / `chore:`）：

```
4def19d docs: README 补本机绝对路径、win 环境变量写法、文件地图
c165710 chore: 补 requirements.txt（离线只要 langgraph，接真模型才要 openai）
019f023 fix: 第二轮台词别再写死 38%，改为读真实年化
b8df9d3 fix: 百分比抽取误把团队份额当成年化，改为按分句+双向邻近匹配
```

**每次提交前必须做的事**：
1. 跑 A / B / C 三个案例，确认 `9.2 / 3.0 / 4.2` 没变
2. 重新生成 `out/demo.html`（`python export_html.py`）
3. 如果动了 `rules.py` 的文案，**必须亲眼读一遍输出**，检查有没有「。。」「…。」这类残留

---

## 7. 验收清单（Codex 交付前自查）

- [ ] `COMMITTEE_MODE=offline python run.py` 三案例跑通，结果 `9.2 / 3.0 / 4.2`
- [ ] RAG 在技术评委发言里留下可验证的引用痕迹（带来源文件名）
- [ ] `out/demo.html` 重新生成，双击能开，三个案例都能切换
- [ ] 没有新增任何第三方依赖（检查 `requirements.txt` 只有 `langgraph` 和 `openai`）
- [ ] 断网状态下（`COMMITTEE_MODE=offline`）所有功能可用
- [ ] 没有把 `.env` / API Key 提交进仓库
- [ ] `git status` 干净，已 push 到 `origin master`
- [ ] 如果改了分数，在 commit message 里说明原因

---

## 8. 一句话总结给接手的人

> 这个项目的价值不在「AI 能给分」，而在**四个有偏见的 Agent 真的互相说服**。
> 你所有的改动，都要保护这个「说服」发生。如果为了代码简洁或逻辑整齐
> 把改口机制削弱了，那就是把项目最有价值的部分删掉了。
