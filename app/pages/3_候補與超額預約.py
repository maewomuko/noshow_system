"""候補與超額預約：預估未到人數（校正表）、候補隊伍（Queue）、遞補。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import (ACCENT, MUTED, ROOT, day_chips, fmt, get_system, kpi_cards, queue_chain,  # noqa: E402
                    section, setup_page, show, steps, tech_panel)

setup_page("候補與超額預約", "🚶")
st.title("候補與超額預約")
show('<div class="ns-lead">先估計今天會空出幾個位子；有人取消時，用 <b>Queue</b> 讓現場候補的人'
     '先來先補。</div>')
system = get_system()
day_chips(system)


def on_refill():
    st.session_state.refill_msg = system.refill()


def on_cancel(appointment_id):
    st.session_state.refill_msg = system.cancel(appointment_id)


refill_done = None
if "refill_msg" in st.session_state:
    out = st.session_state.pop("refill_msg")
    (st.success if out["ok"] else st.warning)(out["message"])
    if out["ok"] and "remaining" in out:
        refill_done = out

# ---- 超額預約 ----
section("今天會空出幾個位子？")
n = len(system.roster)
expected = system.expected_noshow()
c1, c2 = st.columns([1, 4], vertical_alignment="bottom")
capacity = c1.number_input("診間名額", min_value=1, value=max(n, 1), step=1)
arrive = n - expected
spare = capacity - arrive
with c2:
    kpi_cards([
        ("已預約", fmt(n), None, None),
        ("預估未到", f"{expected:,.1f} 人", "校正表估計", MUTED),
        ("預估實到", f"{arrive:,.1f} 人", "已預約 − 預估未到", None),
        ("建議可再收", f"{max(0, int(spare))} 人", f"名額 {capacity} − 預估實到 {arrive:,.1f}", ACCENT),
    ])

# 歷史日期可以拿真正的到診結果對照（新增或遞補的預約還沒看診，不算）
finished = [r for r in system.roster if r.showed_up is not None]
if finished:
    actual = sum(1 for r in finished if r.showed_up is False)
    show(f'<div class="ns-note">對照：這份名單中有 {len(finished):,} 筆是有看診結果的歷史資料，'
         f'實際未到 <b>{actual:,}</b> 人。估計值 = 每人分數換成「歷史上同分者的實際未到率」再加總，'
         '不是機器學習預測。</div>')

# ---- 候補隊伍 ----
queue = system.waitlist.to_list()
section(f"現場候補隊伍（{len(queue)} 人，先來先補）")
queue_chain(queue)

# 測試依賴：第 1 個 button = 遞補
c1, c2, _ = st.columns([2, 2, 3])
c1.button("遞補隊伍第一位", on_click=on_refill, type="primary", disabled=not queue, width="stretch")
top = system.top_risk(1)
if top:
    c2.button(f"取消最高風險者（{top[0].appointment_id}）", on_click=on_cancel,
              args=(top[0].appointment_id,), width="stretch")
st.caption("示範流程：先取消一位（名單少一人）→ 按遞補（名單補回、候補少一人）。")

if refill_done:
    r = refill_done["record"]
    section(f"剛才的遞補：病患 {r.patient_id}（掛號 {r.appointment_id}）")
    steps([("`waitlist.dequeue()`", "front 出隊 O(1)"), ("Linked List `append`", "O(1)"),
           ("BST `insert`", "O(log n)"), ("Max-Heap `push`", "O(log n)"),
           ("陣列 `append`", "對照組 O(1)"), ("病患索引 `insert`", "O(log n)")])

# 實驗三的真實數字（只讀 CSV，不使用網頁上的系統）
moves_note = []
csv3 = ROOT / "experiments" / "results_exp3.csv"
if csv3.exists():
    q = pd.read_csv(csv3)
    q = q[(q.experiment == "queue") & (q.n == q.n.max())].set_index("method")
    if {"array_queue", "linked_queue"} <= set(q.index):
        moves_note = [("ArrayQueue 每次搬移（實驗三）", f"{q.loc['array_queue', 'avg_moves']:,.0f} 個"),
                      ("LinkedQueue 每次搬移（實驗三）", f"{q.loc['linked_queue', 'avg_moves']:,.0f} 個")]

tech_panel(
    ["**候補隊伍 = LinkedQueue**（單向鏈結串列）：記住 front 和 rear，遞補時從 front `dequeue`，"
     "新來的人從 rear `enqueue`，都只改指標。",
     "對照：用陣列 `list.pop(0)` 做佇列，每次要把後面所有人往前搬一格。",
     "遞補的人會同時寫進 Linked List、BST、Max-Heap、陣列、病患索引，其他頁面馬上看得到。",
     "**超額預約**：校正表是 dict（分數 → 歷史未到率），查表 O(1)，全部加總 O(n)。"],
    measured=[("候補人數", str(len(queue))), ("今日名單", f"{n:,} 人"), *moves_note],
    theory=[("`enqueue` / `dequeue`", "O(1)"), ("`list.pop(0)`", "O(n)"), ("預估未到", "O(n)")],
)
