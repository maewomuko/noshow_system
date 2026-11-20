"""預約查詢：BST 依掛號編號查詢，並和陣列線性搜尋比較。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common import bst_path_dot, day_caption, get_system, level_label, structure_box  # noqa: E402

st.set_page_config(page_title="預約查詢", page_icon="🔍", layout="wide")
st.title("🔍 預約查詢")
system = get_system()
day_caption(system)

if len(system.roster) == 0:
    st.warning("今日名單是空的，請到首頁重新載入。")
    st.stop()

roster = system.roster.to_list()
default_id = roster[len(roster) // 2].appointment_id
c1, c2 = st.columns([2, 3])
target = c1.number_input("掛號編號", value=default_id, step=1, format="%d")
c2.caption("提示：可以從首頁的名單複製編號；輸入不存在的編號，也能看到 BST 走到哪裡停下來。")
c2.write(f"例如：{', '.join(str(r.appointment_id) for r in roster[:5])}")

result = system.compare_search(int(target))
record = result["record"]

if record:
    st.success(f"找到掛號編號 {record.appointment_id}")
    cols = st.columns(6)
    cols[0].metric("病患編號", record.patient_id)
    cols[1].metric("年齡", record.age)
    cols[2].metric("等待天數", record.wait_days)
    cols[3].metric("過往未到", record.past_noshow)
    cols[4].metric("風險分數", f"{record.risk:.0f}")
    cols[5].metric("燈號", level_label(record.risk))
else:
    st.error(f"今日名單中沒有掛號編號 {int(target)}（可能已取消，或不是這一天的預約）")

st.subheader("BST vs. 線性搜尋")
c1, c2 = st.columns(2)
c1.metric("BST 比較次數", result["bst"]["comparisons"], help=f"耗時 {result['bst']['ms']:.4f} ms")
c2.metric("線性搜尋比較次數", result["linear"]["comparisons"],
          help=f"耗時 {result['linear']['ms']:.4f} ms")
st.caption(f"BST 耗時 {result['bst']['ms']:.4f} ms；線性搜尋耗時 {result['linear']['ms']:.4f} ms。"
           f"今日 {result['size']} 人，BST 樹高 {result['height']}。")

st.subheader("搜尋路徑")
st.graphviz_chart(bst_path_dot(result["path"], int(target)))

structure_box([
    f"**BST 搜尋**：從根開始，比節點小往左、大往右，比較 {result['bst']['comparisons']} 次"
    f"（{result['bst']['ms']:.4f} ms），平均 O(log n)。",
    f"**對照：陣列線性搜尋**：從頭一筆一筆比，比較 {result['linear']['comparisons']} 次"
    f"（{result['linear']['ms']:.4f} ms），O(n)。",
    "BST 節點裡存了 Linked List 節點的參照（`ll_node`），所以找到之後取消預約可以 O(1) 從名單刪除。",
])
