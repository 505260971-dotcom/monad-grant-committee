"""命令行运行器：在终端里看完整场评审。

用法：
    python run.py            # 依次评审 A / B / C 三份申请
    python run.py A          # 只评审 A
    python run.py B 1        # 评审 B，只辩 1 轮

★ 这是你最常用的调试工具。先在这里把逻辑调对，再上界面。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from committee.graph import run_committee
from committee.prompts import PERSONAS

BASE = Path(__file__).parent
APPS = BASE / "applications"
OUT = BASE / "out"


def load_app(code: str) -> dict:
    files = list(APPS.glob(f"{code}_*.json"))
    if not files:
        raise SystemExit(f"找不到申请书：{code}")
    return json.loads(files[0].read_text(encoding="utf-8"))


def banner(text: str, char: str = "=") -> None:
    print(f"\n{char * 66}")
    print(f"  {text}")
    print(f"{char * 66}")


def show_round(state: dict, rnd: int) -> None:
    """打印某一轮的所有发言。"""
    speeches = [s for s in state["speeches"] if s["round"] == rnd]
    if not speeches:
        return

    print(f"\n--- 第 {rnd} 轮 ---")
    for s in speeches:
        name = PERSONAS.get(s["role"], {}).get("name", s["role"])
        mark = "✓" if s["verdict"] == "approve" else (
            "✗" if s["verdict"] == "reject" else "~")
        print(f"\n[{mark}] {name}（{s['score']} 分，{s['verdict']}）")
        print(f"    {s['content']}")

    avg = sum(x["score"] for x in speeches) / len(speeches)
    print(f"\n    本轮均分：{avg:.1f}")


def show_result(state: dict) -> None:
    """打印最终结论。"""
    banner(f"最终结论：{state['final_verdict'].upper()}", "=")
    print(f"  综合评分：{state['final_score']}")

    verdict_cn = {
        "approve": "通过，进入放款流程",
        "reject": "驳回，不予资助",
        "revise": "需修改后重新提交",
    }
    print(f"  结论说明：{verdict_cn.get(state['final_verdict'], '')}")

    plan = state.get("release_plan", [])
    if plan:
        print("\n  放款计划：")
        total = 0
        for p in plan:
            print(f"    [{p['stage']}] {p['milestone']} — {p['usdc']} USDC（锁定）")
            total += p["usdc"]
        print(f"    合计 {total} USDC，按里程碑分批释放")
    else:
        print("\n  放款计划：无（未通过审核）")

    print("\n  执行轨迹：")
    for t in state.get("trace", []):
        print(f"    · {t}")


async def review(code: str, rounds: int = 2) -> dict:
    app = load_app(code)
    banner(f"评审申请 {code}：{app['name']}")
    print(f"  申请金额：{app['request_usdc']} USDC")

    state = await run_committee(app, max_rounds=rounds)

    # 逐轮打印，模拟"实时"效果
    for rnd in range(1, state["current_round"] + 1):
        show_round(state, rnd)

    show_result(state)

    # 存档，供界面回放
    OUT.mkdir(exist_ok=True)
    out_file = OUT / f"{code}_result.json"
    out_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n  结果已存档：{out_file.name}")
    return state


async def main() -> None:
    args = sys.argv[1:]
    code = args[0].upper() if args else None
    rounds = int(args[1]) if len(args) > 1 else 2

    if code:
        await review(code, rounds)
        return

    for c in ["A", "B", "C"]:
        await review(c, rounds)


if __name__ == "__main__":
    asyncio.run(main())
