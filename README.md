# AI 投委会 · Autonomous Grant Committee

> 4 个 AI 评委并行开会，识破资金盘，自动生成放款计划。
> Monad Blitz 广州站 · 2026-11-21

---

## 一句话

公链基金会每年收到的生态资助申请远超人手能审的量。这个项目把评审拆成
四个互相制衡的 AI 评委，让它们真的吵起来，然后自动把结论变成链上的分期放款。

## 为什么"4 个 Agent 吵架"比"1 个 Agent 打分"有意义

单模型评审的问题是**它永远给出温和的中间分**，因为在它的训练里"综合考虑"是最安全的回答。

我们让它变成四个**有偏见、有立场、会互相说服**的角色：

| 角色 | 不可退让的立场 | 会怎么反驳别人 |
|---|---|---|
| 产品经理 | 只认真实数据和流水 | "产品再好，经济模型崩了也救不了" |
| 技术极客 | 只认技术事实与 Monad 能力匹配 | "你以为瓶颈在性能，其实在架构" |
| 代币经济学 | 专门抓庞氏结构 | "用户越喜欢它，崩得越快" |
| 合规与财务 | 程序与风控红线 | "有一个维度不可持续，这轮就不放款" |

**真正的看点是第二轮的改口**：第一轮合规给了 8 分，看到代币经济学指出
"用新钱付旧账"之后，第二轮压到 2 分并支持驳回。这不是写死的分支，
而是因为它真的读到了对方那句话。

## 三个准备好的案例

| 案例 | 项目 | 设计意图 | 结果 |
|---|---|---|---|
| A | MonadPay 电商结算 SDK | 痛点真实、有流水、不发币 | 全票通过，生成 3 期放款 |
| B | YieldNova 聚合收益 | 38% 年化 + 新钱付旧账 | 代币经济学否决，合规跟进，驳回 |
| C | ChainVote 链上投票 | "全量选票上链 + 遍历计票" | 技术指出架构缺陷，驳回 |

## 快速开始

**本机路径**（换电脑要改）：
```
项目目录：D:\Program Files\2026-11-14-16-56-20\monad-blitz
解释器　：C:\Users\lijy0\.workbuddy\binaries\python\envs\langgraph-lab\Scripts\python.exe
```

```bash
# 0. 先进目录（Windows PowerShell 或 Git Bash 都行）
cd "D:\Program Files\2026-11-14-16-56-20\monad-blitz"

# 1. 离线模式（不需要任何 API Key，用的是规则引擎）
COMMITTEE_MODE=offline python run.py

# 2. 只看 B 案例，辩 2 轮
COMMITTEE_MODE=offline python run.py B 2

# 3. 生成演示页（单文件 HTML，双击可开）
python export_html.py
```

Windows 上没有 `COMMITTEE_MODE=xxx` 这种写法，PowerShell 里要这么写：

```powershell
$env:COMMITTEE_MODE="offline"
& "C:\Users\lijy0\.workbuddy\binaries\python\envs\langgraph-lab\Scripts\python.exe" run.py B
```

## 文件都在哪

| 路径 | 是什么 | 什么时候看 |
|---|---|---|
| `run.py` | 命令行入口 | 每次改完代码跑它验证 |
| `committee/state.py` | 工单结构（LangGraph State） | 想加字段时改这里 |
| `committee/prompts.py` | 4 个评委的人格和 prompt | 想改评委说话风格时 |
| `committee/graph.py` | 图的搭法（扇出/扇入/回边） | 想加评委、改轮数时 |
| `committee/rules.py` | 离线规则引擎 | 想改打分逻辑时 |
| `committee/llm.py` | 三层降级 | 想接新模型时 |
| `applications/*.json` | 三份申请书剧本 | 想造新案例时 |
| `out/demo.html` | **单文件演示页，双击就能看** | 给评委看的那个 |
| `out/*_result.json` | 三个案例的运行结果存档 | 查历史输出 |
| `teaching/t1~t3` | 教学教具，不是产品代码 | 学 LangGraph 时 |

## 接真模型

```bash
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat
python run.py
```

代码里做了**三层降级**：真模型 → 本地模型 → 规则引擎。
现场 WiFi 抽风、API 限流、Key 失效，都不会让 Demo 卡死。

## 图结构

```
        ┌── 产品经理 ────┐
        ├── 技术极客 ────┤
START ──┤                ├──> 汇总 ──> 再辩一轮？
        ├── 代币经济学 ──┤              │
        └── 合规与财务 ──┘              ├─ 是 → 回到四个 Agent
                                        └─ 否 → 定稿 → 放款计划
```

4 个 Agent 是**并行**执行的。串行 4 次模型调用 = 4 倍等待，现场等不起。

## 踩过的坑（写下来，免得你重踩）

**1. 并行节点写的字段必须标 `operator.add`**

```
InvalidUpdateError: At key 'trace': Can receive only one value per step
```

4 个 Agent 同时写 `trace`，如果它是普通字段（覆盖格），LangGraph 会直接报错。
必须写成 `Annotated[list[str], operator.add]`。`speeches` 同理。

**2. 有否决时要强制再辩一轮，不要立刻收敛**

第一版逻辑是"分差小或有人否决就收敛"，结果 B 案例第一轮就结束了，
"合规改口"这一幕永远不会发生。改成"有否决且还有轮数时，继续辩"，
Demo 才有高潮。

**3. 说改口就要真的改分**

一开始文案说"我把分数下调到 3 分"，但分数还是 5 分，屏幕上
"说反对、显示 revise"会立刻露馅。分数必须在算完之后真的被改掉。

## 目录

```
monad-blitz/
├── committee/
│   ├── state.py      工单结构（LangGraph State）
│   ├── prompts.py    4 个评委的人格与 prompt
│   ├── rules.py      规则引擎（离线保底）
│   ├── llm.py        三层降级的模型调用
│   └── graph.py      图编排
├── applications/     3 份申请书（Demo 剧本）
├── out/              结果存档 + demo.html
├── run.py            命令行运行器
└── export_html.py    导出单文件演示页
```

## 待接（队友的合约）

需要向合约侧确认这 6 项，缺一项胶水代码就写不了：

- [ ] 合约在 Monad 测试网的地址
- [ ] 放款函数名、参数顺序、金额单位
- [ ] 谁付 gas（后端私钥代付 / 申请方自签）
- [ ] 放款函数的权限白名单
- [ ] 里程碑是单次放款还是数组传多期
- [ ] 放款成功 emit 什么事件

## 环境

- Python 3.13
- langgraph 1.2.15
- 离线模式无需任何第三方依赖
