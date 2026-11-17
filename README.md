# AI 投委会 · Autonomous Grant Committee

> 4 个 AI 评委并行开会，识破资金盘，自动生成放款计划。
> Monad Blitz 广州站 · 2026-11-21

---

## 一句话

公链基金会每年收到的生态资助申请远超人手能审的量。这个项目把评审拆成
四个互相制衡的 AI 评委，让它们真的吵起来，然后自动把结论变成链上的分期放款。

## 为什么"4 个 Agent 吵架"比"1 个 Agent 打分"有意义

我们希望通过分角色评审发现不同维度的风险；尚未完成与单模型的系统对比实验。

我们让它变成四个**有偏见、有立场、会互相说服**的角色：

| 角色 | 不可退让的立场 | 会怎么反驳别人 |
|---|---|---|
| 产品经理 | 只认真实数据和流水 | "产品再好，经济模型崩了也救不了" |
| 技术极客 | 只认技术事实与 Monad 能力匹配 | "你以为瓶颈在性能，其实在架构" |
| 代币经济学 | 专门抓庞氏结构 | "用户越喜欢它，崩得越快" |
| 合规与财务 | 程序与风控红线 | "有一个维度不可持续，这轮就不放款" |

**真正的看点是第二轮的改口**：第一轮合规给了 8 分，看到代币经济学指出
"用新钱付旧账"之后，第二轮压到 2 分并支持驳回。离线模式由复议规则触发分数调整；真实模型需要单独验证。

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
| `out/pitch.html` | **上台讲的那个，8 幕，空格推进** | 路演时投屏 |
| `out/pitch.pdf` | 同上，8 页 PDF（投影仪不认浏览器时用） | 备胎 |
| `out/demo.html` | 结果回放页，全部铺开 | 评委来查细节时 |
| `out/*_result.json` | 三个案例的运行结果存档 | 查历史输出 |
| `teaching/t1~t3` | 教学教具，不是产品代码 | 学 LangGraph 时 |

## 上台讲用哪个

两个页面，两种用途，别搞混：

| 文件 | 用途 | 特点 |
|---|---|---|
| `out/pitch.html` | **讲故事** | 一屏一幕，8 幕，制造悬念 |
| `out/demo.html` | **被追问** | 全部铺开，给评委自己翻 |

生成：

```bash
python export_pitch.py          # -> out/pitch.html
python export_pitch.py --pdf    # -> out/pitch.html + out/pitch.pdf
python export_pitch.py --check  # 只核对台词数字，不生成
python export_html.py           # -> out/demo.html
```

**`--check` 是干什么的**：`pitch.html` 里的台词是手写的口语句子
（JSON 里的原文带 `[申请者自述·未独立核验]` 这种前缀，投到屏幕上后排看不清）。
手写就有写错的可能，所以生成前会拿台词里的分数跟 `out/*.json` 逐个对一遍，
对不上直接报错退出——**不让你带着错的数字上台**。

现场操作：空格 / → / PageDown 前进，← / PageUp 后退，Home / End 首尾，
点屏幕右侧 70% 前进、左侧 30% 后退（翻页笔也能用）。
`out/pitch.html#5` 直接跳到第 5 幕。

## 接真模型

```bash
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://api.deepseek.com/v1
export LLM_MODEL=deepseek-chat
python run.py
```

auto 模式支持真实模型 → 规则引擎降级，并标记来源；live 模式失败时报错。尚未实现本地模型。
现场 WiFi 抽风、API 限流、Key 失效，可切换到离线规则或回放；实时链上操作仍需要网络。

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
├── out/              结果存档 + pitch.html（上台用）+ demo.html（查数据用）
├── run.py            命令行运行器
├── export_pitch.py   导出上台版 8 幕 HTML / PDF
└── export_html.py    导出结果回放页
```

## 现场演示的三层保险

按「越往下越兜底」排：

1. **`out/pitch.html`** —— 主用。纯静态，双击就开，断网也能演。
2. **`out/pitch.pdf`** —— 投影仪不认浏览器、或者只能插 U 盘拷文件时用。8 页，16:9。
3. **`review_service.py --serve`** —— 只有在评委问「能不能现场给一份新申请书跑一遍」时才启动。
   纯标准库，`http://127.0.0.1:8765`，`POST /review`。不起服务完全不影响前两层。

```bash
# 第三层才用，平时不要开
python review_service.py --serve
```

**为什么不做成前后端分离的 Web 应用**：`fastapi` / `uvicorn` 本机都没装，
现场 WiFi 也不可靠。能静态就静态——7 小时的黑客松，不要给自己多一个能翻车的环节。

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
- 离线模式无需模型 API，仍需 langgraph


## AI 侧加固与联调

新增输入和模型输出校验、来源标记和本机评审接口。详见 [docs/AI_INTEGRATION.md](docs/AI_INTEGRATION.md)。
拨款计划仅为建议，未接链、不签名、不锁资。


## 官方资料与本地模型
- 六份官方文档快照：`knowledge/official/`，来源及 SHA-256 清单为 `manifest.json`。
- 检索为本地词法检索，官方原文与自编策略分别标记；原文不能证明申请方的事实陈述。
- Ollama 通过兼容接口接入，模型为本机已有的 `qwen2.5:7b`，无需另装模型。
- 本地推理默认串行；延迟实测见 `out/ollama_7b_benchmark/`，不能沿用远程四路并行的耗时假设。
- `scripts/sync_monad_docs.py` 可重新抓取六份官方资料；更新后应核对清单并运行测试。
- `scripts/pilot_ollama.py` 可重跑小规模测试；注意会产生本机推理负载。


## AI 侧交付与证据校验

当前交付状态、文件位置和未完成职责见 `docs/AI_DELIVERY_STATUS.md`；接口说明见 `docs/AI_INTEGRATION.md`。证据编号校验不代表语义真实性核验，建议拨款计划尚未上链。
