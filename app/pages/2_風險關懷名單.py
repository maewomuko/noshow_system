"""風險關懷名單：Max-Heap Top-K，電訪確認會到（調降風險）或取消預約。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common import day_caption, get_system, heap_dot, level_label, structure_box  # noqa: E402

st.set_page_config(page_title="風險關懷名單", page_icon="📞", layout="wide")
st.title("📞 風險關懷名單")
system = get_system()
day_caption(system)


def on_confirm(appointment_id):
    st.session_state.care_msg = system.confirm_attend(appointment_id)["message"]


def on_cancel(appointment_id):
    st.session_state.care_msg = system.cancel(appointment_id)["message"]


if len(system.roster) == 0:
    st.warning("今日名單是空的，請到首頁重新載入。")
    st.stop()

if "care_msg" in st.session_state:
    st.success(st.session_state.pop("care_msg"))

max_k = min(30, len(system.roster))
k = st.slider("要列出前幾名（K）", 1, max_k, min(10, max_k))
st.caption("護理站每天只需要打電話給最可能不來的前幾位，不需要把全部人排序。")

top = system.top_risk(k)
header = st.columns([1, 2, 2, 1, 1, 1, 2, 2, 2])
for col, name in zip(header, ["名次", "掛號編號", "病患編號", "年齡", "等待", "過往未到",
                              "風險／燈號", "", ""]):
    col.markdown(f"**{name}**")
for rank, r in enumerate(top, 1):
    c = st.columns([1, 2, 2, 1, 1, 1, 2, 2, 2])
    c[0].write(rank)
    c[1].write(r.appointment_id)
    c[2].write(r.patient_id)
    c[3].write(r.age)
    c[4].write(f"{r.wait_days} 天")
    c[5].write(r.past_noshow)
    c[6].write(f"{r.risk:.0f}　{level_label(r.risk)}")
    c[7].button("✅ 確認會到", key=f"ok_{r.appointment_id}",
                on_click=on_confirm, args=(r.appointment_id,))
    c[8].button("❌ 取消預約", key=f"cancel_{r.appointment_id}",
                on_click=on_cancel, args=(r.appointment_id,))

st.subheader("Heap 前 4 層（陣列索引 i 的子節點在 2i+1、2i+2）")
st.graphviz_chart(heap_dot(system.heap_preview(4)))

structure_box([
    f"**Max-Heap `top_k({k})`**：從根往下只展開需要的節點，O(K log K)，不破壞原本的 heap。",
    "**確認會到**：`update_key` 把風險改成 0 → 往下沉（sift-down），O(log n)。",
    "**取消預約**：BST 找節點 O(log n) → Linked List 刪節點 O(1) → BST 刪除 O(log n) → "
    "Heap `remove` O(log n)，所有結構同步。",
    "對照：每次用 `sorted()` 把全部人排序再取前 K，要 O(n log n)（見「效能分析」實驗二）。",
])
