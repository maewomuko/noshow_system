"""候補與超額預約：預估未到人數、候補隊伍（Queue）、遞補。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import day_caption, get_system, record_table, structure_box  # noqa: E402

st.set_page_config(page_title="候補與超額預約", page_icon="🚶", layout="wide")
st.title("🚶 候補與超額預約")
system = get_system()
day_caption(system)


def on_refill():
    st.session_state.refill_msg = system.refill()


def on_cancel(appointment_id):
    st.session_state.refill_msg = system.cancel(appointment_id)


if "refill_msg" in st.session_state:
    out = st.session_state.pop("refill_msg")
    (st.success if out["ok"] else st.warning)(out["message"])

# ---- 超額預約 ----
st.subheader("今天會空出幾個位子？")
n = len(system.roster)
expected = system.expected_noshow()
capacity = st.number_input("診間名額", min_value=1, value=max(n, 1), step=1)
c = st.columns(4)
c[0].metric("已預約", n)
c[1].metric("預估未到", f"{expected:.1f} 人")
c[2].metric("預估實到", f"{n - expected:.1f} 人")
spare = capacity - (n - expected)
c[3].metric("建議可再收", f"{max(0, int(spare))} 人")
st.caption("預估未到 = 每個人的風險分數換成「歷史上同分者的實際未到率」再加總。"
           "例如 2016-06-06 全天預估 957 人未到，實際 845 人。")

# ---- 候補隊伍 ----
st.subheader(f"現場候補隊伍（{len(system.waitlist)} 人，先來先補）")
queue = system.waitlist.to_list()
if queue:
    st.dataframe(pd.DataFrame(record_table(queue)), hide_index=True, width="stretch")
else:
    st.info("候補隊伍已經空了。")

c1, c2 = st.columns(2)
c1.button("➡️ 遞補隊伍第一位", on_click=on_refill, type="primary", disabled=not queue)

top = system.top_risk(1)
if top:
    c2.button(f"❌ 取消最高風險者（{top[0].appointment_id}）",
              on_click=on_cancel, args=(top[0].appointment_id,))
st.caption("示範流程：先取消一位（名單少一人）→ 按遞補（名單補回、候補少一人）。")

structure_box([
    "**候補隊伍 = LinkedQueue**（單向鏈結串列）：遞補時從前端 `dequeue`，O(1)；"
    "新來的人從尾端 `enqueue`，O(1)。",
    "對照：用陣列 `list.pop(0)` 做佇列，每次要把後面所有人往前搬，O(n)（見「效能分析」實驗三）。",
    "遞補的人會同時寫進 Linked List、BST、Max-Heap、病患索引，所以其他頁面馬上看得到。",
])
