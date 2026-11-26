"""風險關懷名單：Max-Heap Top-K，電訪確認會到（調降風險）或取消預約。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common import (LEVEL_COLOR, day_chips, get_system, heap_dot, heap_strip, level_badge,  # noqa: E402
                    section, setup_page, show, tech_panel)
from core.record import risk_level  # noqa: E402

setup_page("風險關懷名單", "📞")
st.title("風險關懷名單")
show('<div class="ns-lead">護理站每天只需要先打電話給<b>最可能不來的前幾位</b>，'
     '用 Max-Heap 直接取前 K 名，不需要把全部人排序。</div>')
system = get_system()
day_chips(system)


def on_confirm(appointment_id):
    out = system.confirm_attend(appointment_id)
    st.session_state.care_msg = ("ok" if out["ok"] else "err", out["message"] + (
        "。Heap 用 `update_key` 把他往下沉（sift-down），所以從前 K 名消失。" if out["ok"] else ""))


def on_cancel(appointment_id):
    out = system.cancel(appointment_id)
    st.session_state.care_msg = ("ok" if out["ok"] else "err", out["message"] + (
        "。已同步從 Linked List、BST、Max-Heap、陣列、病患索引移除，可到「候補與超額預約」遞補。"
        if out["ok"] else ""))


if len(system.roster) == 0:
    st.warning("今日名單是空的，請到首頁重新載入。")
    st.stop()

if "care_msg" in st.session_state:
    kind, text = st.session_state.pop("care_msg")
    (st.success if kind == "ok" else st.error)(text)

max_k = min(30, len(system.roster))
k = st.slider("要列出前幾名（K）", 1, max_k, min(10, max_k))
top = system.top_risk(k)
top_ids = {r.appointment_id for r in top}

# ---- 前 K 名（測試依賴：按鈕 key = ok_<id> / cancel_<id>） ----
section(f"今日風險前 {k} 名")
ROW_RATIO = [7, 1.2, 1.2]
head, _, _ = st.columns(ROW_RATIO, gap="small")
with head:
    show('<div class="ns-row ns-row-head"><span>名次</span><span>掛號編號</span><span>燈號</span>'
         '<span>風險分數</span><span>等待</span><span>過往未到</span></div>')
for rank, r in enumerate(top, 1):
    color = LEVEL_COLOR[risk_level(r.risk)]
    row, b1, b2 = st.columns(ROW_RATIO, vertical_alignment="center", gap="small")
    with row:
        show(f'<div class="ns-row"><span class="ns-rank">{rank}</span>'
             f'<span class="ns-num">{r.appointment_id}</span>{level_badge(r.risk)}'
             f'<span class="ns-riskbar"><span class="ns-riskbar-track"><span class="ns-riskbar-fill" '
             f'style="display:block;width:{r.risk:.0f}%;background:{color}"></span></span>'
             f'<b class="ns-num">{r.risk:.0f}</b></span>'
             f'<span class="ns-num">{r.wait_days} 天</span><span class="ns-num">{r.past_noshow} 次</span></div>')
    b1.button("確認會到", key=f"ok_{r.appointment_id}", on_click=on_confirm,
              args=(r.appointment_id,), width="stretch", help=f"病患 {r.patient_id} 電訪確認會來 → 風險改為 0")
    b2.button("取消預約", key=f"cancel_{r.appointment_id}", on_click=on_cancel,
              args=(r.appointment_id,), width="stretch")

# ---- Heap 結構 ----
preview = system.heap_preview(4)
shown = sum(1 for r in preview if r.appointment_id in top_ids)
section("Max-Heap 前 4 層（真實資料；外框 = 目前前 K 名中位於這 4 層的節點）")
st.graphviz_chart(heap_dot(preview, highlight=top_ids))
show('<div class="ns-note">同一份資料在記憶體裡其實是一個陣列：索引 i 的小孩在 2i+1、2i+2，爸爸在 (i−1)//2。</div>')
heap_strip(preview, highlight=top_ids)
show(f'<div class="ns-note">前 {k} 名中有 {shown} 位落在前 4 層（前 15 格）；'
     f'其餘的在更深的層，<code>top_k</code> 會從根往下只展開需要的節點去找。'
     f'同分時掛號編號小的優先，所以名單固定、可重現。</div>')

tech_panel(
    ["**Max-Heap**：父節點風險 ≥ 子節點，最高風險的人永遠在根（索引 0）。",
     f"`top_k({k})` 另外開一個小的輔助 heap，從根開始每取出一個就把它的兩個小孩放進候選，"
     "原本的 heap 完全不動。",
     "**確認會到**：`update_key` 把風險改成 0 → sift-down；用 `pos` 字典直接查到他在陣列哪一格。",
     "**取消預約**：BST 找節點 → Linked List 用 `ll_node` 刪除 → BST 刪除 → Heap `remove`，所有結構同步。",
     "對照：每次用 `sorted()` 把全部人排序再取前 K（見「效能分析」實驗二；K 接近 n 時 `sorted()` 反而較快）。"],
    measured=[("今日 heap 大小", f"{len(system.heap):,}"), ("本次 K", str(k)),
              ("前 K 名在前 4 層", f"{shown} 位")],
    theory=[("`top_k(K)`", "O(K log K)"), ("`update_key`", "O(log n)"), ("`remove`", "O(log n)"),
            ("`sorted()` 取前 K", "O(n log n)")],
)
