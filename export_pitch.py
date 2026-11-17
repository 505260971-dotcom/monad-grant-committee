"""把评审结果导出成「上台讲」用的单文件 HTML —— 8 幕，空格推进。

★ 和 export_html.py 的区别：
  export_html.py  ->  out/demo.html   结果回放，全部铺开，给人查数据用
  export_pitch.py ->  out/pitch.html  一屏一幕，制造悬念，上台讲用

★ 为什么台词要精简：
  out/*.json 里的 content 是给机器看的（带 [申请者自述·未独立核验] 这类前缀、
  规则引擎的完整推理链）。直接铺到大屏上，后排一个字都看不清。
  这里改成口语句子，但每个数字都跟 JSON 里的一致 —— main() 会做一次核对，
  不一致就报警。

★ 为什么必须纯静态：
  现场断网、端口被占、Python 环境不对，任何一个都能让人在台上翻车。
  这个文件双击就开，从 U 盘拷到别人电脑也能开。

用法：
  python export_pitch.py            # 生成 out/pitch.html
  python export_pitch.py --check    # 只核对数字，不生成

深链（截图/救场用）：out/pitch.html#5  直接跳到第 5 幕
键盘：空格 / → / PageDown 前进    ← / PageUp 后退    Home / End 首尾
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
OUT = BASE / "out"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------- 台词
# 手写口语句子。数字必须与 out/*.json 一致，main() 会核对。
# 第一轮 4 条必须同时出现在同一帧里（见场景 3 的注释）。
SPEECH = {
    ("B", 1, "pm"): "痛点全是定性的，一个数都没有。进展只有内测 TVL，没有留存、没有收入。",
    ("B", 1, "tech"): "技术栈讲得清楚，但审计没提，再平衡的滑点保护也没提。",
    ("B", 1, "token"): "38% 年化靠新用户的钱付老用户，还要每天回购销毁 0.4% 流通量。这是庞氏结构。",
    ("B", 1, "compliance"): "预算拆成 3 期可以监督，合计 8 万和申请额对得上，还主动披露了收益风险。",
    ("B", 2, "pm"): "代币那条已经定性了，我跟着降。",
    ("B", 2, "tech"): "技术判断不变。这个问题跟我的维度无关。",
    ("B", 2, "token"): "结论不变。结构性问题不会因为再辩一轮就消失。",
    ("B", 2, "compliance"): "预算本身没问题。但代币经济学已经被判定是庞氏，我修正自己的评分。",
    ("A", 1, "pm"): "痛点有 5 处具体数值。已接入 12 家商户，月流水 42 万美元，留存 78%。",
    ("A", 1, "tech"): "批量提交把多笔结算打包，正好吃到 Monad 的 300ms 出块和低费率。",
    ("A", 1, "token"): "申请声明不发代币。没有激励，就没有旁氏结构的空间。",
    ("A", 1, "compliance"): "预算与申请额一致，涉及资金归集也主动提示了牌照要求。",
}

# 第一轮那 4 条必须同帧出现；第二轮的改动要能被指出来。
ROLE_CN = {"pm": "产品经理", "tech": "技术极客", "token": "代币经济学", "compliance": "合规与财务"}
ROLE_MARK = {"pm": "◆", "tech": "●", "token": "▲", "compliance": "■"}


def load(code: str) -> dict:
    p = OUT / f"{code}_result.json"
    if not p.exists():
        raise SystemExit(f"缺 {p.name}，先跑 run.py")
    return json.loads(p.read_text(encoding="utf-8"))


def index(case: dict) -> dict:
    """(role, round) -> speech"""
    return {(s["role"], s["round"]): s for s in case["speeches"]}


def check(a: dict, b: dict) -> list[str]:
    """核对台词里手写的数字与 JSON 是否一致。"""
    problems = []
    ba, bb = index(a), index(b)

    expect = {
        ("B", 1): {"pm": 5, "tech": 6, "token": 1, "compliance": 8},
        ("B", 2): {"pm": 3, "tech": 6, "token": 1, "compliance": 2},
        ("A", 1): {"pm": 10, "tech": 10, "token": 9, "compliance": 8},
    }
    store = {"A": ba, "B": bb}
    for (code, rnd), want in expect.items():
        for role, score in want.items():
            got = store[code].get((role, rnd))
            if got is None:
                problems.append(f"缺发言 {code} r{rnd} {role}")
            elif got["score"] != score:
                problems.append(f"{code} r{rnd} {role}: 台词写 {score}，实际 {got['score']}")

    if a["final_verdict"] != "approve" or abs(a["final_score"] - 9.2) > 0.01:
        problems.append(f"A 定稿 {a['final_verdict']} {a['final_score']}，台词写 approve 9.2")
    if b["final_verdict"] != "reject" or abs(b["final_score"] - 3.0) > 0.01:
        problems.append(f"B 定稿 {b['final_verdict']} {b['final_score']}，台词写 reject 3.0")

    plan_total = sum(x["usdc"] for x in a.get("release_plan") or [])
    if plan_total != a["application"]["request_usdc"]:
        problems.append(f"A 放款计划合计 {plan_total} != 申请额 {a['application']['request_usdc']}")
    if b.get("release_plan"):
        problems.append("B 被否决却生成了放款计划")

    for key in [("B", 1, "token"), ("B", 2, "compliance")]:
        if key not in SPEECH:
            problems.append(f"缺台词 {key}")
    return problems


# ---------------------------------------------------------------- 模板
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 投委会 · 路演</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{height:100%;overflow:hidden;background:#0a0c11}
  body{
    color:#e8ebf2;
    font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .num{font-variant-numeric:tabular-nums}

  /* ---------- 骨架 ---------- */
  #bar{position:fixed;top:0;left:0;height:2px;background:#5b8cff;z-index:99;
       transition:width .35s cubic-bezier(.22,.61,.36,1);box-shadow:0 0 12px #5b8cff88}
  #pg{position:fixed;right:2.2vw;bottom:1.9vh;font-size:12px;color:#4a5162;z-index:99;
      letter-spacing:.14em}
  .scene{position:absolute;inset:0;display:none;padding:5.4vh 6.2vw 7.5vh}
  /* ★ 整体垂直居中：否则内容少的幕（分歧 / 边界）下半屏全是空的，投影时重心飘在上面 */
  .scene.on{display:flex;flex-direction:column;justify-content:center}
  .spacer{flex:1}

  /* ---------- 动画 ---------- */
  @keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
  @keyframes fade{from{opacity:0}to{opacity:1}}
  .an{opacity:0}
  .scene.on .an{animation:rise .55s cubic-bezier(.22,.61,.36,1) both}
  .scene.on .af{animation:fade .6s ease both}
  /* 只有需要错开层次的地方才用 delay。★ 场景 3 的四列一律不设 delay。 */
  .d1{animation-delay:.10s!important}
  .d2{animation-delay:.20s!important}
  .d3{animation-delay:.30s!important}
  .d4{animation-delay:.44s!important}

  /* ---------- 字 ---------- */
  .kicker{font-size:clamp(12px,1vw,14px);letter-spacing:.26em;color:#5b8cff;
          text-transform:uppercase;margin-bottom:2.4vh}
  .h1{font-size:clamp(42px,6vw,92px);line-height:1.06;font-weight:600;letter-spacing:-.02em}
  .h2{font-size:clamp(26px,2.7vw,42px);line-height:1.25;font-weight:600;letter-spacing:-.01em}
  .lead{font-size:clamp(16px,1.5vw,24px);line-height:1.75;color:#a6aec2}
  .p{font-size:clamp(14px,1.16vw,19px);line-height:1.8;color:#b9c0d0}
  .sm{font-size:clamp(12px,.94vw,15px);line-height:1.7;color:#767f94}
  .dim{color:#5c6478}
  .blue{color:#7fb0ff}.green{color:#6ee7a0}.amber{color:#f0c06a}.violet{color:#c9a0ff}
  .red{color:#ff8f9c}
  .mono{font-family:ui-monospace,"SF Mono",Consolas,monospace;font-size:.92em}

  /* ---------- 场景 0 封面 ---------- */
  .cover{justify-content:center}
  .cover .h1 span{color:#5b8cff}
  .cover .lead{margin-top:3vh;max-width:44em}
  .cover .foot{margin-top:6vh;display:flex;gap:2.6vw;flex-wrap:wrap;font-size:clamp(12px,1vw,14px);
               color:#5c6478;align-items:center}
  .cover .foot b{color:#a6aec2;font-weight:500}

  /* ---------- 场景 1 问题 ---------- */
  .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:1.6vw;margin-top:4vh}
  .card{border:1px solid #1e2431;border-radius:12px;padding:3vh 1.7vw;background:#0e1118}
  .card .n{font-size:clamp(34px,4vw,68px);font-weight:600;line-height:1;color:#ff8f9c}
  .card .t{margin-top:2vh;font-size:clamp(17px,1.5vw,25px);color:#e8ebf2;font-weight:500}
  .card .d{margin-top:1.2vh;font-size:clamp(13px,1.05vw,17px);color:#8d95a8;line-height:1.75}
  .punch{margin-top:5vh;font-size:clamp(24px,2.6vw,42px);line-height:1.5;font-weight:500}
  .punch em{font-style:normal;color:#6ee7a0}

  /* ---------- 场景 2 申请书 ---------- */
  .app{display:grid;grid-template-columns:1.2fr .8fr;gap:3.2vw;margin-top:3.4vh;
       align-items:start}
  .fields{display:flex;flex-direction:column;gap:2.4vh}
  .f{border-left:2px solid #232b3a;padding:.5vh 0 .5vh 1.1vw}
  .f .k{font-size:clamp(11px,.88vw,14px);letter-spacing:.1em;color:#5c6478;margin-bottom:.6vh}
  .f .v{font-size:clamp(14px,1.16vw,19px);line-height:1.75;color:#c6ccda}
  /* ★ 经济模型这一格是全场证据最硬的地方：
     把「新钱付老钱」那一句单独放大，其余降为小字。
     整段铺上去会变成一大片红，观众反而抓不住重点。 */
  .scam{border:1px solid #5c2530;background:#1a0d11;border-radius:8px;
        padding:1.8vh 1.2vw;font-size:clamp(16px,1.5vw,25px);line-height:1.55;
        color:#ff8f9c;font-weight:500}
  .kv{margin-top:1.6vh;display:flex;flex-direction:column;gap:.7vh;
      font-size:clamp(12px,.94vw,15px);line-height:1.6;color:#8d95a8}
  .kv i{font-style:normal;color:#ff8f9c;margin-right:.6em}
  .f.hot{border-left-color:#ff5c72;background:linear-gradient(90deg,#ff5c7212,transparent 70%)}
  .f.hot .v{color:#ffd9de}
  .f.hot .v mark{background:#ff5c7233;color:#ff8f9c;padding:.1em .18em;border-radius:3px;
                 font-weight:500;box-shadow:inset 0 -.5em 0 #ff5c7222}
  .ask{border:1px solid #1e2431;border-radius:12px;background:#0e1118;padding:3vh 1.8vw;
       display:flex;flex-direction:column;justify-content:center;height:fit-content}
  .ask .amt{font-size:clamp(34px,4.2vw,68px);font-weight:600;line-height:1;color:#fff}
  .ask .unit{font-size:clamp(13px,1.1vw,17px);color:#767f94;margin-top:1vh}
  .ask .who{margin-top:2.6vh;padding-top:2vh;border-top:1px solid #1a2029;
            font-size:clamp(12px,.95vw,15px);color:#8d95a8;line-height:1.8}
  .ask .who b{color:#e8ebf2;font-weight:500;display:block;margin-bottom:.4vh}

  /* ---------- 场景 3 四评委 ---------- */
  /* ★ 卡片高度不撑满：内容自适应，整排再在剩余空间里垂直居中。
     撑满会让卡片中间拉出一大片空白，内容反而显得更小。 */
  .judges{display:grid;grid-template-columns:repeat(4,1fr);gap:1.5vw;
          margin-top:3.4vh;flex:1;align-content:center;align-items:start}
  .j{border:1px solid #1e2431;border-radius:12px;background:#0e1118;padding:2.4vh 1.4vw;
     display:flex;flex-direction:column;position:relative;overflow:hidden}
  .j::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;background:var(--c)}
  .j .top{display:flex;align-items:center;gap:.55em;font-size:clamp(13px,1.05vw,17px);
          color:var(--c);letter-spacing:.04em}
  .j .top .m{font-size:.85em}
  .j .sc{font-size:clamp(40px,4.6vw,76px);font-weight:600;line-height:1;margin-top:1.8vh;color:#fff}
  .j .sc s{font-size:.34em;font-weight:400;color:#5c6478;text-decoration:none;margin-left:.35em}
  .j .vd{margin-top:1vh;font-size:clamp(12px,.92vw,15px);letter-spacing:.06em;
         color:var(--c);opacity:.85}
  /* 发言是这一格的主角，字号往大里给 —— 投影时后排要看得清 */
  .j .say{margin-top:2.2vh;padding-top:2vh;border-top:1px solid #1a2029;
          font-size:clamp(14px,1.28vw,22px);line-height:1.8;color:#c6ccda}
  .j .meta{margin-top:2vh;font-size:clamp(11px,.8vw,13px);
           color:#4a5162;letter-spacing:.06em}
  .fan{margin-top:auto;padding-top:2.2vh;border-top:1px solid #1a2029;
       display:flex;align-items:center;gap:1.2vw;flex-wrap:wrap;
       font-size:clamp(13px,1.05vw,17px);color:#8d95a8}
  .fan b{color:#6ee7a0;font-weight:500}

  /* ---------- 场景 4 分歧 ---------- */
  .split{display:flex;align-items:flex-end;gap:1.4vw;margin-top:4vh;flex-wrap:wrap}
  .split .big{font-size:clamp(64px,9vw,160px);font-weight:600;line-height:.9;
              letter-spacing:-.03em;color:#ff8f9c}
  .split .vs{font-size:clamp(16px,1.6vw,26px);color:#5c6478;
             padding-bottom:clamp(24px,2.6vw,44px)}
  .split .min{font-size:clamp(64px,9vw,160px);font-weight:600;line-height:.9;
              letter-spacing:-.03em;color:#6ee7a0}
  .split .lbl{font-size:clamp(12px,.95vw,15px);color:#767f94;margin-top:1.2vh}
  .rule{margin-top:4vh;display:flex;flex-direction:column;gap:1.6vh;max-width:60em}
  .step{display:flex;gap:1.4vw;align-items:flex-start}
  .step .i{flex:0 0 auto;width:2.5em;height:2.5em;border-radius:50%;border:1px solid #2a3344;
           display:flex;align-items:center;justify-content:center;font-size:clamp(11px,.9vw,14px);
           color:#5c6478}
  .step .x{font-size:clamp(15px,1.3vw,23px);line-height:1.75;color:#b9c0d0}
  .step .x b{color:#fff;font-weight:500}
  .step.stop .i{border-color:#ff5c7255;color:#ff8f9c}
  .step.stop .x b{color:#ff8f9c}

  /* ---------- 场景 5 改口 ---------- */
  .flip{display:flex;align-items:center;gap:2.2vw;margin-top:5vh;flex-wrap:wrap}
  .flip .old{font-size:clamp(52px,7.5vw,132px);font-weight:600;line-height:1;color:#3d4657;
             position:relative;letter-spacing:-.03em}
  .flip .old::after{content:"";position:absolute;left:-3%;right:-3%;top:52%;height:3px;
                    background:#ff5c72;transform:rotate(-8deg);opacity:.75;border-radius:2px}
  .flip .arr{font-size:clamp(24px,3vw,52px);color:#4a5162;font-weight:300}
  .flip .new{font-size:clamp(52px,7.5vw,132px);font-weight:600;line-height:1;color:#ff8f9c;
             letter-spacing:-.03em}
  .quote{margin-top:4.4vh;border-left:3px solid #c9a0ff;padding:1.4vh 0 1.4vh 1.6vw;max-width:52em}
  .quote .who{font-size:clamp(11px,.88vw,13px);letter-spacing:.14em;color:#c9a0ff;margin-bottom:1.2vh}
  .quote .txt{font-size:clamp(18px,1.9vw,30px);line-height:1.6;color:#e8ebf2;font-weight:400}
  .after{margin-top:4vh;font-size:clamp(13px,1.1vw,17px);line-height:1.8;color:#8d95a8;max-width:52em}
  .after b{color:#6ee7a0;font-weight:500}
  .why{margin-top:2.4vh;display:flex;gap:.8vw;flex-wrap:wrap}
  .tag{font-size:clamp(11px,.85vw,13px);padding:.45em .9em;border-radius:99px;
       border:1px solid #2a3344;color:#8d95a8}

  /* ---------- 场景 6 定稿对照 ---------- */
  .two{display:grid;grid-template-columns:1fr 1fr;gap:2.2vw;margin-top:3vh;flex:1;min-height:0}
  .col{border:1px solid #1e2431;border-radius:12px;padding:2.6vh 1.6vw;background:#0e1118;
       display:flex;flex-direction:column}
  .col.no{border-color:#3a1f26;background:#120d10}
  .col.yes{border-color:#1c3527;background:#0b1410}
  .col .hd{display:flex;align-items:center;justify-content:space-between;gap:1vw;
           padding-bottom:1.8vh;border-bottom:1px solid #1a2029}
  .badge{font-size:clamp(11px,.9vw,14px);letter-spacing:.1em;padding:.42em .9em;border-radius:6px}
  .badge.no{background:#33161b;color:#ff8f9c;border:1px solid #5c2530}
  .badge.yes{background:#15321f;color:#6ee7a0;border:1px solid #235c36}
  .col .fin{font-size:clamp(30px,3.4vw,56px);font-weight:600;line-height:1}
  .col .nm{margin-top:1.6vh;font-size:clamp(13px,1.05vw,17px);color:#e8ebf2}
  .col .on{margin-top:.5vh;font-size:clamp(11px,.88vw,13.5px);color:#767f94}
  .col .body{margin-top:2.4vh;flex:1;min-height:0}
  .pl{display:flex;flex-direction:column;gap:0}
  .pl .r{display:flex;justify-content:space-between;gap:1vw;padding:1.1vh 0;
         border-bottom:1px solid #1a2029;font-size:clamp(12px,.98vw,15.5px);color:#b9c0d0}
  .pl .r:last-child{border-bottom:none}
  .pl .r .a{color:#6ee7a0;white-space:nowrap}
  .pl .r.sum{color:#e8ebf2}
  .pl .r.sum .a{color:#fff;font-weight:600}
  .note{margin-top:1.8vh;font-size:clamp(11px,.86vw,13.5px);line-height:1.7;color:#5c6478}

  /* ---------- 场景 7 边界 ---------- */
  .layer{display:grid;grid-template-columns:1fr auto 1fr;gap:1.6vw;align-items:stretch;
         margin-top:4vh}
  .lb{border:1px solid #1e2431;border-radius:12px;padding:3vh 1.7vw;background:#0e1118}
  .lb.mine{border-color:#2a3f66;background:#0b1020}
  .lb .who{font-size:clamp(11px,.86vw,13px);letter-spacing:.16em;color:#5c6478;margin-bottom:1.6vh}
  .lb.mine .who{color:#7fb0ff}
  .lb .ttl{font-size:clamp(22px,2.1vw,34px);font-weight:600;color:#fff;line-height:1.2}
  .lb .lst{margin-top:2.4vh;display:flex;flex-direction:column;gap:1.3vh;
           font-size:clamp(13px,1.08vw,18px);color:#9aa3b6;line-height:1.6}
  .lb .lst i{font-style:normal;color:#4a5162;margin-right:.5em}
  /* 中间那条缝：竖排中文在投影上会糊成一团，改成横排小标签 + 交接物 */
  .seam{display:flex;flex-direction:column;align-items:center;justify-content:center;
        gap:1.4vh;min-width:10vw}
  .seam .ln{width:1px;flex:1;min-height:3vh;
            background:linear-gradient(#1e2431,#5b8cff55,#1e2431)}
  .seam .lb2{font-size:clamp(11px,.82vw,13px);color:#5b8cff;letter-spacing:.22em;
             white-space:nowrap}
  .seam .box{border:1px dashed #34507f;border-radius:8px;padding:1.3vh 1.1vw;text-align:center;
             background:#0b1020;white-space:nowrap}
  .seam .box .k{font-size:clamp(10px,.8vw,12px);color:#5b8cff;letter-spacing:.1em}
  .seam .box .v{font-size:clamp(11px,.88vw,13.5px);color:#c6ccda;margin-top:.5vh;
                font-family:ui-monospace,Consolas,monospace}
  .pins{margin-top:3.4vh;display:flex;gap:1vw;flex-wrap:wrap}
  .pin{font-family:ui-monospace,Consolas,monospace;font-size:clamp(12px,.92vw,15px);
       padding:.65em 1em;border-radius:8px;border:1px solid #2a3344;color:#8d95a8;background:#0e1118}
  .pin b{color:#6ee7a0;font-weight:500}
  .closing{margin-top:3.6vh;font-size:clamp(20px,2vw,32px);line-height:1.6;
           color:#e8ebf2;font-weight:500;max-width:54em}
  .closing em{font-style:normal;color:#7fb0ff}

  /* ---------- 底部提示 ---------- */
  #hint{position:fixed;left:2.2vw;bottom:1.9vh;font-size:11px;color:#3d4657;letter-spacing:.1em;
        z-index:99;transition:opacity .4s}
  #hint.hide{opacity:0}

  @media (max-width:900px){
    .cards,.judges{grid-template-columns:1fr 1fr}
    .app,.two,.layer{grid-template-columns:1fr}
  }

  /* ---------- 截图/导出专用 ----------
     ★ 为什么不用 @media print 做 PDF：
       这套排版字号全用 vw（跟着窗口宽度变）。打印引擎给的是一个固定宽度的
       视口，vw 会算错，结果字被挤成一根竖条、一页溢成两页 —— 实测过。
       所以 PDF 走「逐幕截图再合成」，见 export_pitch.py --pdf。
       这里的 .flat 就是给截图脚本用的：把 8 幕都摊开、去掉动画初始态。 */
  body.flat{overflow:visible}
  body.flat .scene{position:relative;inset:auto;display:flex;
                  height:100vh;page-break-after:always}
  body.flat .an,body.flat .af{opacity:1;animation:none;transform:none}
  body.flat #bar,body.flat #hint,body.flat #pg{display:none}
</style>
</head>
<body>
<div id="bar"></div>
<div id="hint">空格 / → 继续</div>
<div id="pg"></div>

<!-- ============ 0 封面 ============ -->
<section class="scene cover">
  <div class="kicker an">Monad Blitz · 广州 · 2026</div>
  <h1 class="h1 an d1">让 4 个 Agent<br><span>替你先吵一遍</span></h1>
  <p class="lead an d2">AI 投委会是一套自主的生态资助决策系统。<br>
     4 个不同视角的评审 Agent 并行开庭，就同一份申请书辩论，达成结论，<br>
     然后把一个可被合约执行的拨款计划交出去。</p>
  <div class="foot af d3">
    <span><b>并行评审</b> · 4 个节点同时跑</span>
    <span><b>多轮辩论</b> · 分歧不消解就重开</span>
    <span><b>可追溯</b> · 每条结论挂着证据编号</span>
    <span><b>不碰私钥</b> · 只产出建议，不签名</span>
  </div>
</section>

<!-- ============ 1 问题 ============ -->
<section class="scene">
  <div class="kicker an">问题</div>
  <h2 class="h2 an d1">一次生态资助，卡在三个地方</h2>
  <div class="cards">
    <div class="card an d1">
      <div class="n num">2-6 周</div>
      <div class="t">评审周期</div>
      <div class="d">申请要排期、等评委有空、凑齐一次会。钱在账上躺着等。</div>
    </div>
    <div class="card an d2">
      <div class="n num">4</div>
      <div class="t">视角彼此看不见</div>
      <div class="d">产品、技术、代币、合规各看一遍，相互之间没有对话。有人看出问题，别人不知道。</div>
    </div>
    <div class="card an d3">
      <div class="n num">0</div>
      <div class="t">可复核的推导</div>
      <div class="d">最后只有一句「通过了」。为什么通过、哪句话支撑了结论，没有留痕。</div>
    </div>
  </div>
  <p class="punch an d4">我们要做的不是把评审加速。是让它<em>可以被检查</em>。</p>
</section>

<!-- ============ 2 申请书 ============ -->
<section class="scene">
  <div class="kicker an">第一份申请书</div>
  <h2 class="h2 an d1">先不看 AI。你自己当一次评委。</h2>
  <div class="app">
    <div class="fields">
      <div class="f an d1">
        <div class="k">一句话</div>
        <div class="v">聚合 Monad 生态各类收益策略，用户质押 NOVA 代币即可获得稳定年化 38%。</div>
      </div>
      <div class="f an d1">
        <div class="k">已有进展</div>
        <div class="v" id="f-traction"></div>
      </div>
      <div class="f hot an d2" style="border-left-color:#ff5c72">
        <div class="k">经济模型 · 申请方自述原文</div>
        <div class="scam" id="f-scam"></div>
        <div class="kv" id="f-kv"></div>
      </div>
      <div class="f an d2">
        <div class="k">预算</div>
        <div class="v" id="f-budget"></div>
      </div>
    </div>
    <div class="ask an d2">
      <div class="amt num" id="f-amt"></div>
      <div class="unit">USDC · 请求资助</div>
      <div class="who">
        <b id="f-name"></b>
        <span class="mono dim" id="f-applicant"></span>
      </div>
    </div>
  </div>
</section>

<!-- ============ 3 四评委 ============ -->
<section class="scene">
  <div class="kicker an">开庭</div>
  <h2 class="h2 an d1">四个视角，同一帧。</h2>
  <div class="judges" id="judges"></div>
  <div class="fan an">
    <span id="fan-a"></span>
    <span style="flex:1"></span>
    <span id="fan-b"></span>
  </div>
</section>

<!-- ============ 4 分歧 ============ -->
<section class="scene">
  <div class="kicker an">分歧</div>
  <h2 class="h2 an d1">分差 7 分。系统没有取平均。</h2>
  <div class="split">
    <div class="an d1">
      <div class="big num" id="s-max"></div>
      <div class="lbl">最高分 · 合规与财务</div>
    </div>
    <div class="vs an d1">vs</div>
    <div class="an d1">
      <div class="min num" id="s-min"></div>
      <div class="lbl">最低分 · 代币经济学</div>
    </div>
  </div>
  <div class="rule">
    <div class="step an d2">
      <div class="i num">1</div>
      <div class="x">四条发言落进 State。均分 <b class="num" id="s-avg"></b>，分差 <b class="num" id="s-gap"></b>。</div>
    </div>
    <div class="step an d2">
      <div class="i num">2</div>
      <div class="x">有一个评委给了否决意见。按规则，<b>有否决时不判收敛</b> —— 哪怕均分已经过线。</div>
    </div>
    <div class="step stop an d3">
      <div class="i">✕</div>
      <div class="x"><b>不通过。回边重开一轮。</b>把「有人强烈反对」这件事，交回给辩论本身去处理。</div>
    </div>
  </div>
</section>

<!-- ============ 5 改口 ============ -->
<section class="scene">
  <div class="kicker an">第二轮</div>
  <h2 class="h2 an d1">然后有人改了主意。</h2>
  <div class="flip">
    <div class="old num an d1">8</div>
    <div class="arr an d1">→</div>
    <div class="new num an d2">2</div>
  </div>
  <div class="quote an d3">
    <div class="who">合规与财务 · 复述上一轮的反对意见之后</div>
    <div class="txt" id="q-flip"></div>
  </div>
  <p class="after an d4">这不是我们写死的分支。是<b>第二轮拿到了第一轮的否决理由</b>，
    在新上下文里重新判断，自己把分数降了下去。</p>
  <div class="why an d4">
    <div class="tag">上一轮 8 分</div>
    <div class="tag">按复议规则调整</div>
    <div class="tag">参考风险角色：token</div>
    <div class="tag">本轮 2 分</div>
  </div>
</section>

<!-- ============ 6 定稿 ============ -->
<section class="scene">
  <div class="kicker an">定稿</div>
  <h2 class="h2 an d1">同一套代码，两个走向。</h2>
  <div class="two">
    <div class="col no an d1">
      <div class="hd">
        <span class="nm" id="c-b-name"></span>
        <span class="badge no">驳回</span>
      </div>
      <div class="fin num" style="margin-top:2.2vh;color:#ff8f9c" id="c-b-score"></div>
      <div class="on" id="c-b-on"></div>
      <div class="body">
        <div class="note" style="margin-top:2.4vh">被一票否决。不进放款流程。</div>
        <div class="note" style="margin-top:1.6vh;color:#8d95a8">
          <span class="mono">release_plan = []</span><br>
          没有计划可执行，合约那边什么都收不到。
        </div>
      </div>
    </div>
    <div class="col yes an d2">
      <div class="hd">
        <span class="nm" id="c-a-name"></span>
        <span class="badge yes">通过</span>
      </div>
      <div class="fin num" style="margin-top:2.2vh;color:#6ee7a0" id="c-a-score"></div>
      <div class="on" id="c-a-on"></div>
      <div class="body">
        <div style="margin-top:2.4vh">
          <div class="sm" style="margin-bottom:1vh">生成的分期放款计划</div>
          <div class="pl" id="c-a-plan"></div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ============ 7 边界 ============ -->
<section class="scene">
  <div class="kicker an">边界</div>
  <h2 class="h2 an d1">它不签字。它让签字之前那 40 秒有据可查。</h2>
  <div class="layer">
    <div class="lb mine an d1">
      <div class="who">决策层 · 我们</div>
      <div class="ttl">Python + LangGraph</div>
      <div class="lst">
        <span><i>—</i>并行扇出 4 个评审节点</span>
        <span><i>—</i>State 累加，四条发言互不覆盖</span>
        <span><i>—</i>条件回边，分歧未消就重开</span>
        <span><i>—</i>产出 review JSON</span>
      </div>
    </div>
    <div class="seam an d1">
      <div class="ln"></div>
      <div class="lb2">唯一交接物</div>
      <div class="box">
        <div class="k">release_plan</div>
        <div class="v" id="seam-v"></div>
      </div>
      <div class="ln"></div>
    </div>
    <div class="lb an d2">
      <div class="who">执行层 · 合约</div>
      <div class="ttl">Solidity</div>
      <div class="lst">
        <span><i>—</i>托管资金</span>
        <span><i>—</i>按里程碑分期放款</span>
        <span><i>—</i>校验白名单与权限</span>
        <span><i>—</i>发事件上链</span>
      </div>
    </div>
  </div>
  <div class="pins an d3">
    <span class="pin">advisory_only: <b>true</b></span>
    <span class="pin">chain_status: <b>not_submitted</b></span>
    <span class="pin">executable: <b>false</b></span>
    <span class="pin">私钥 / 签名 / 广播：<b>不涉及</b></span>
  </div>
  <p class="closing an d4">4 个 Agent 吵完，你拿到的不是一个分数，
    是<em>一条能追溯的论证链</em>。</p>
</section>

<script>
const DATA = __DATA__;
const STAMP = "__STAMP__";

const ROLE_CN   = __ROLE_CN__;
const ROLE_MARK = __ROLE_MARK__;
const ROLE_COLOR= {pm:"#7fb0ff", tech:"#6ee7a0", token:"#f0c06a", compliance:"#c9a0ff"};
const ROLE_ORDER= ["pm","tech","token","compliance"];
const VD = {approve:"通过", reject:"反对", revise:"需修改"};

const $ = id => document.getElementById(id);
const esc = v => String(v ?? "").replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = n => Number(n).toLocaleString("en-US");

function sp(code, role, rnd){
  const c = DATA[code];
  return (c.speeches || []).find(s => s.role === role && s.round === rnd);
}

/* ---------- 场景 2 ---------- */
(function fillApp(){
  const a = DATA.B.application;
  $("f-traction").textContent = a.traction;

  // 把「庞氏铁证」那一句单独拎出来放大，其余条件降为小字注脚。
  // 这句话是申请书原文，不是我们加的判断 —— 讲的时候一定要强调这点。
  const KEY = "新增用户质押的资金用于支付早期用户的收益";
  $("f-scam").textContent = "「" + KEY + "」";
  $("f-kv").innerHTML = [
    "承诺年化 <b>38%</b>，收益来源写的是挖矿奖励与手续费",
    "为维持这个收益率，每天需回购销毁约 <b>0.4%</b> 流通量",
    "代币总量 1 亿枚，初始流通 8%，团队份额 25%"
  ].map(x => `<span><i>·</i>${x}</span>`).join("");

  $("f-budget").textContent = (a.budget || []).map(b =>
    b.milestone + " " + fmt(b.usdc)).join(" · ");
  $("f-amt").textContent = fmt(a.request_usdc);
  $("f-name").textContent = a.name;
  $("f-applicant").textContent = a.applicant;
})();

/* ---------- 场景 3 四评委 ----------
   ★ 关键：这一格四条发言必须同一帧出现。
     不能依次滑入 —— 观众会以为是 for 循环挨个调模型，并行扇出这个技术点就没了。
     所以这 4 个 div 都不加 d1/d2/d3，只共用 .an 的同一个动画起点。
*/
(function fillJudges(){
  $("judges").innerHTML = ROLE_ORDER.map(role => {
    const s = sp("B", role, 1);
    const say = __SAY_B1__[role] || s.content;
    return `<div class="j an" style="--c:${ROLE_COLOR[role]}">
      <div class="top"><span class="m">${ROLE_MARK[role]}</span>${ROLE_CN[role]}</div>
      <div class="sc num">${s.score}<s>/10</s></div>
      <div class="vd">${VD[s.verdict] || s.verdict}</div>
      <div class="say">${esc(say)}</div>
      <div class="meta">${esc(s.source_mode)} · 证据 ${(s.claims||[]).length} 条</div>
    </div>`;
  }).join("");

  $("fan-a").innerHTML = '4 个节点<b>同时发起</b>，不是排队。';
  $("fan-b").innerHTML = '一轮墙钟耗时 ≈ 1 个最慢的节点，不是 4 倍。';
})();

/* ---------- 场景 4 分歧 ---------- */
(function fillSplit(){
  const r1 = ROLE_ORDER.map(r => sp("B", r, 1).score);
  const mx = Math.max(...r1), mn = Math.min(...r1);
  const avg = r1.reduce((a,b)=>a+b,0) / r1.length;
  $("s-max").textContent = mx;
  $("s-min").textContent = mn;
  $("s-avg").textContent = avg.toFixed(1);
  $("s-gap").textContent = mx - mn;
})();

/* ---------- 场景 5 改口 ---------- */
$("q-flip").textContent = __SAY_FLIP__;

/* ---------- 场景 6 定稿 ---------- */
(function fillFinal(){
  const a = DATA.A, b = DATA.B;
  $("c-b-name").textContent  = b.application.name.split("—")[0].trim();
  $("c-b-score").textContent = b.final_score.toFixed(1);
  $("c-b-on").textContent    = "综合评分 · 被 compliance 一票否决";
  $("c-a-name").textContent  = a.application.name.split("—")[0].trim();
  $("c-a-score").textContent = a.final_score.toFixed(1);
  $("c-a-on").textContent    = "综合评分 · 4 票一致通过";

  const plan = a.release_plan || [];
  const total = plan.reduce((s,p)=>s + p.usdc, 0);
  $("c-a-plan").innerHTML = plan.map(p =>
    `<div class="r"><span>${esc(p.milestone)}</span>
      <span class="a num">${fmt(p.usdc)}</span></div>`).join("")
    + `<div class="r sum"><span>合计</span>
        <span class="a num">${fmt(total)} USDC</span></div>`;

  $("seam-v").textContent = plan.length + " stage";
})();

/* ---------- 场景推进 ---------- */
const SCENES = [...document.querySelectorAll(".scene")];
const TOTAL = SCENES.length;
let cur = 0, hinted = false;

function paint(){
  SCENES.forEach((s, i) => {
    // 先摘掉 on 让动画重置，再加回去 —— 否则回退再前进时动画不会重播
    s.classList.remove("on");
    if (i === cur) {
      void s.offsetWidth;          // 强制重排，重启 CSS 动画
      s.classList.add("on");
    }
  });
  $("bar").style.width = ((cur + 1) / TOTAL * 100) + "%";
  $("pg").textContent = String(cur + 1).padStart(2, "0") + " / " + String(TOTAL).padStart(2, "0");
  if (!hinted && cur > 0) { $("hint").classList.add("hide"); }
}

function go(n, sync){
  cur = Math.max(0, Math.min(TOTAL - 1, n));
  paint();
  if (sync !== false) history.replaceState(null, "", "#" + cur);
}

document.addEventListener("keydown", e => {
  if ([" ", "ArrowRight", "PageDown", "Enter", "n"].includes(e.key)) {
    e.preventDefault(); go(cur + 1);
  } else if (["ArrowLeft", "PageUp", "Backspace", "p"].includes(e.key)) {
    e.preventDefault(); go(cur - 1);
  } else if (e.key === "Home") { go(0); }
  else if (e.key === "End")    { go(TOTAL - 1); }
});

// 点击：右侧 70% 前进，左侧 30% 后退。现场用遥控翻页笔也能触发。
document.addEventListener("click", e => {
  if (e.clientX > window.innerWidth * 0.3) go(cur + 1);
  else go(cur - 1);
});

// 深链：#5 直接跳到第 5 幕
const h = parseInt((location.hash || "").slice(1), 10);
if (!Number.isNaN(h)) cur = Math.max(0, Math.min(TOTAL - 1, h));
paint();

// ?print=1 -> 摊开全部幕，给 Ctrl+P 导出 PDF 用
// 也可以直接浏览器搜 "?print=1"，看不到任何按钮也不影响正常演示
if (new URLSearchParams(location.search).get("print") === "1") {
  document.body.classList.add("flat");
}
</script>
</body>
</html>
"""


def build_html(a: dict, b: dict) -> str:
    data = {
        "A": a,
        "B": b,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
    say_b1 = {r: SPEECH[("B", 1, r)] for r in ROLE_ORDER}
    say_flip = SPEECH[("B", 2, "compliance")]

    return (TEMPLATE
            .replace("__DATA__", payload)
            .replace("__STAMP__", datetime.now().strftime("%Y-%m-%d %H:%M"))
            .replace("__ROLE_CN__", json.dumps(ROLE_CN, ensure_ascii=False))
            .replace("__ROLE_MARK__", json.dumps(ROLE_MARK, ensure_ascii=False))
            .replace("__SAY_B1__", json.dumps(say_b1, ensure_ascii=False))
            .replace("__SAY_FLIP__", json.dumps(say_flip, ensure_ascii=False))
            )


ROLE_ORDER = ["pm", "tech", "token", "compliance"]


def make_pdf(html_path: Path, width: int = 1600, height: int = 900) -> None:
    """逐幕截图再合成 PDF —— 保证跟屏幕上看到的一模一样。

    ★ 为什么不直接 Ctrl+P：
      这套 CSS 的字号是 vw 单位。打印引擎给固定宽度视口，vw 会算错，
      字被挤成竖条、一页溢成两页。实测 8 幕印出来是 12 页。
      逐幕截图用的是真实窗口尺寸，所见即所得。

    依赖：系统自带 Edge（Windows 10/11 都预装）+ pymupdf（打包 PDF）。
    pymupdf 没装就只出 PNG，照样能当幻灯片用。
    """
    import subprocess
    import tempfile

    edge = None
    for c in [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        Path("/usr/bin/microsoft-edge"),
    ]:
        if c.exists():
            edge = c
            break
    if edge is None:
        print("找不到 Edge，跳过 PDF。pitch.html 本身照样可以演示。")
        return

    tmp = Path(tempfile.mkdtemp(prefix="pitch_"))
    shots = []
    for i in range(8):
        png = tmp / f"{i}.png"
        subprocess.run([
            str(edge), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-sandbox", f"--user-data-dir={tmp / 'prof'}",
            "--virtual-time-budget=3000",
            f"--window-size={width},{height}",
            f"--screenshot={png}",
            f"{html_path.as_uri()}#{i}",
        ], capture_output=True, timeout=60)
        if png.exists():
            shots.append(png)

    if not shots:
        print("截图失败，跳过 PDF。")
        return

    try:
        import pymupdf
    except ImportError:
        keep = OUT / "pitch_frames"
        keep.mkdir(exist_ok=True)
        for i, s in enumerate(shots):
            (keep / f"{i:02d}.png").write_bytes(s.read_bytes())
        print(f"未装 pymupdf，已输出 {len(shots)} 张 PNG 到 {keep}")
        print("  想合成 PDF：pip install pymupdf 后重跑")
        return

    doc = pymupdf.open()
    for s in shots:
        img = pymupdf.open(s)
        w, h = img[0].rect.width, img[0].rect.height
        page = doc.new_page(width=w, height=h)
        page.insert_image(page.rect, filename=str(s))
        img.close()

    pdf = OUT / "pitch.pdf"
    doc.save(pdf, deflate=True)
    doc.close()
    print(f"\n已生成：{pdf}")
    print(f"  {pdf.stat().st_size / 1024:.0f} KB · {len(shots)} 页 · 16:9")
    print("  现场只能给 PDF 时用它，不用重做 PPT")


def main() -> None:
    check_only = "--check" in sys.argv
    want_pdf = "--pdf" in sys.argv

    a, b = load("A"), load("B")
    problems = check(a, b)

    if problems:
        print("数字对不上，先别上台：")
        for p in problems:
            print("  ✗", p)
        raise SystemExit(1)

    print("数字核对通过：")
    print(f"  A {a['application']['name'].split('—')[0].strip()} "
          f"{a['final_verdict']} {a['final_score']}")
    print(f"  B {b['application']['name'].split('—')[0].strip()} "
          f"{b['final_verdict']} {b['final_score']}")
    if check_only:
        return

    html = build_html(a, b)
    target = OUT / "pitch.html"
    target.write_text(html, encoding="utf-8")
    print(f"\n已生成：{target}")
    print(f"  {target.stat().st_size / 1024:.0f} KB · 8 幕 · 零依赖，双击就开")
    print(f"  深链示例：{target.as_uri()}#5")

    if want_pdf:
        make_pdf(target)


if __name__ == "__main__":
    main()
