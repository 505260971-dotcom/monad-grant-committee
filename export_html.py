"""把评审结果导出成一个单文件 HTML 演示页。

★ 为什么不用 Streamlit：
  - 不用起服务、不用装依赖、不用等端口
  - 双击就能打开，断网也能演
  - 现场不会因为 Python 环境问题翻车

产出：out/demo.html  一个文件，可以直接发给人看，也能当现场大屏。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent
OUT = BASE / "out"

ROLE_CN = {"pm": "产品经理", "tech": "技术极客",
           "token": "代币经济学", "compliance": "合规与财务"}
ROLE_ORDER = ["pm", "tech", "token", "compliance"]


def load_all() -> list[dict]:
    """按「演示效果」排序，不是按字母。

    ★ B 放在第一个：它有 2 轮辩论、有评委改口，是全场最抓人的案例。
    现场默认就停在它上面，评委一上来就看见分歧。
    """
    cases = []
    for code in ["B", "A", "C"]:
        p = OUT / f"{code}_result.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            d["_code"] = code
            cases.append(d)
    return cases


def build_html(cases: list[dict]) -> str:
    data = json.dumps(cases, ensure_ascii=False)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 投委会 · 评审现场</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: #0d0f14; color: #e6e8ee;
    font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 14px; line-height: 1.7;
  }}
  .wrap {{ max-width: 1120px; margin: 0 auto; padding: 28px 24px 64px; }}
  header {{ border-bottom: 1px solid #232733; padding-bottom: 18px; margin-bottom: 22px; }}
  h1 {{ font-size: 19px; font-weight: 500; margin: 0 0 6px; }}
  .sub {{ color: #7d8598; font-size: 13px; }}
  .tabs {{ display: flex; gap: 8px; margin: 18px 0 20px; flex-wrap: wrap; }}
  .tab {{
    padding: 9px 16px; border: 1px solid #262b38; border-radius: 8px;
    background: #14171f; cursor: pointer; font-size: 13px; color: #a9b1c4;
    transition: all .12s;
  }}
  .tab:hover {{ border-color: #3a4152; color: #e6e8ee; }}
  .tab.on {{ background: #1d2433; border-color: #4a5a7a; color: #fff; }}
  .tab b {{ display: block; font-weight: 500; }}
  .tab span {{ font-size: 12px; opacity: .65; }}

  .verdict {{
    display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
    padding: 16px 20px; border-radius: 10px; margin-bottom: 22px;
    border: 1px solid #262b38; background: #14171f;
  }}
  .badge {{
    padding: 5px 14px; border-radius: 6px; font-size: 13px; font-weight: 500;
  }}
  .badge.pass {{ background: #15321f; color: #6ee7a0; border: 1px solid #235c36; }}
  .badge.reject {{ background: #33161b; color: #ff8f9c; border: 1px solid #5c2530; }}
  .badge.revise {{ background: #33290f; color: #f0c06a; border: 1px solid #5c4a1e; }}
  .score {{ font-size: 26px; font-weight: 500; }}
  .score small {{ font-size: 12px; color: #7d8598; font-weight: 400; margin-left: 4px; }}

  .round-label {{
    font-size: 12px; color: #7d8598; text-transform: uppercase;
    letter-spacing: .08em; margin: 26px 0 12px; padding-left: 2px;
  }}
  .speech {{
    display: grid; grid-template-columns: 132px 1fr; gap: 16px;
    padding: 14px 0; border-top: 1px solid #1b1f29;
  }}
  .who {{ font-size: 13px; }}
  .who .name {{ font-weight: 500; display: block; margin-bottom: 4px; }}
  .who .sc {{ font-size: 12px; color: #7d8598; }}
  .bar {{ height: 3px; border-radius: 2px; background: #232733; margin-top: 6px; overflow: hidden; }}
  .bar i {{ display: block; height: 100%; }}
  .said {{ font-size: 14px; color: #d3d8e4; }}
  .ev {{ margin-top: 8px; font-size: 12px; color: #6f7a90; }}
  .ev span {{ display: block; }}
  .ev span::before {{ content: "· "; }}
  .changed {{
    display: inline-block; font-size: 11px; padding: 1px 7px; margin-left: 6px;
    border-radius: 4px; background: #33290f; color: #f0c06a; border: 1px solid #5c4a1e;
    vertical-align: middle;
  }}

  .plan {{ margin-top: 26px; padding: 16px 20px; border-radius: 10px;
           border: 1px solid #262b38; background: #14171f; }}
  .plan h3 {{ font-size: 13px; font-weight: 500; margin: 0 0 12px; color: #a9b1c4; }}
  .mrow {{ display: flex; justify-content: space-between; padding: 7px 0;
           border-bottom: 1px solid #1b1f29; font-size: 13px; }}
  .mrow:last-child {{ border-bottom: none; }}
  .mrow .amt {{ color: #6ee7a0; font-variant-numeric: tabular-nums; }}
  .empty {{ color: #7d8598; font-size: 13px; }}

  .trace {{ margin-top: 22px; font-size: 12px; color: #6f7a90; }}
  .trace div {{ padding: 2px 0; }}
  footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #1b1f29;
            font-size: 12px; color: #5b6377; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>AI 投委会 · 评审现场</h1>
    <div class="sub">4 个 Agent 并行评审 · 多轮辩论 · 结论自动写入放款计划</div>
  </header>

  <div class="tabs" id="tabs"></div>
  <div id="panel"></div>

  <footer>离线回放 · 生成于 {stamp} · 不依赖网络</footer>
</div>

<script>
const CASES = {data};
const ROLE_CN = {json.dumps(ROLE_CN, ensure_ascii=False)};
const ROLE_COLOR = {{ pm: "#7fb0ff", tech: "#6ee7a0", token: "#f0c06a", compliance: "#c9a0ff" }};
const VERDICT_CN = {{ approve: "通过", reject: "驳回", revise: "需修改" }};
const VERDICT_CLS = {{ approve: "pass", reject: "reject", revise: "revise" }};

let cur = 0;

function renderTabs() {{
  document.getElementById("tabs").innerHTML = CASES.map((c, i) => {{
    const short = c.application.name.split("—")[0].trim();
    return `<div class="tab ${{i === cur ? "on" : ""}}" onclick="pick(${{i}})">
      <b>${{c._code}} · ${{short}}</b>
      <span>${{VERDICT_CN[c.final_verdict]}} · ${{c.final_score}} 分</span>
    </div>`;
  }}).join("");
}}

function pick(i) {{ cur = i; renderTabs(); renderPanel(); }}

function scoreByIdx(code, role, rnd) {{
  const c = CASES.find(x => x._code === code);
  const s = (c.speeches || []).find(x => x.role === role && x.round === rnd);
  return s ? s.score : null;
}}

function renderPanel() {{
  const c = CASES[cur];
  const roles = ["pm", "tech", "token", "compliance"];
  const maxRound = Math.max(...(c.speeches || []).map(s => s.round));

  let roundsHtml = "";
  for (let r = 1; r <= maxRound; r++) {{
    const list = c.speeches.filter(s => s.round === r)
      .sort((a, b) => roles.indexOf(a.role) - roles.indexOf(b.role));
    if (!list.length) continue;
    roundsHtml += `<div class="round-label">第 ${{r}} 轮</div>`;
    roundsHtml += list.map(s => {{
      const before = r > 1 ? scoreByIdx(c._code, s.role, r - 1) : null;
      const flipped = before !== null && before !== s.score;
      const arrow = flipped ? ` <span class="changed">${{before}} → ${{s.score}}</span>` : "";
      const pct = (s.score / 10) * 100;
      return `<div class="speech">
        <div class="who">
          <span class="name" style="color:${{ROLE_COLOR[s.role]}}">${{ROLE_CN[s.role]}}</span>
          <span class="sc">${{s.score}} 分 · ${{VERDICT_CN[s.verdict] || s.verdict}}${{arrow}}</span>
          <div class="bar"><i style="width:${{pct}}%;background:${{ROLE_COLOR[s.role]}}"></i></div>
        </div>
        <div>
          <div class="said">${{s.content}}</div>
          ${{(s.evidence || []).length ? `<div class="ev">${{s.evidence.map(e => `<span>${{e}}</span>`).join("")}}</div>` : ""}}
        </div>
      </div>`;
    }}).join("");
  }}

  const plan = c.release_plan || [];
  const planHtml = plan.length
    ? plan.map(p => `<div class="mrow"><span>${{p.milestone}}</span>
        <span class="amt">${{p.usdc.toLocaleString()}} USDC</span></div>`).join("")
      + `<div class="mrow"><span>合计</span><span class="amt">${{plan.reduce((a, b) => a + b.usdc, 0).toLocaleString()}} USDC</span></div>`
    : `<div class="empty">未通过审核，不生成放款计划</div>`;

  const trace = (c.trace || []).map(t => `<div>${{t}}</div>`).join("");

  document.getElementById("panel").innerHTML = `
    <div class="verdict">
      <span class="badge ${{VERDICT_CLS[c.final_verdict]}}">${{VERDICT_CN[c.final_verdict]}}</span>
      <span class="score">${{c.final_score}}<small>综合评分</small></span>
      <span style="color:#7d8598;font-size:13px">
        ${{c.application.name}} · 申请 ${{c.application.request_usdc.toLocaleString()}} USDC
      </span>
    </div>
    ${{roundsHtml}}
    <div class="plan">
      <h3>放款计划（按里程碑锁定释放）</h3>
      ${{planHtml}}
    </div>
    <div class="trace">${{trace}}</div>`;
}}

renderTabs();
renderPanel();
</script>
</body>
</html>"""


def main() -> None:
    cases = load_all()
    if not cases:
        raise SystemExit("没有结果文件，请先跑 run.py")

    html = build_html(cases)
    target = OUT / "demo.html"
    target.write_text(html, encoding="utf-8")

    size = target.stat().st_size / 1024
    print(f"已生成：{target}")
    print(f"  大小 {size:.0f} KB · 包含 {len(cases)} 个案例")
    for c in cases:
        print(f"  {c['_code']} {c['application']['name']} -> {c['final_verdict']}")


if __name__ == "__main__":
    main()
