"""預約查詢：BST 依掛號編號查詢，並和陣列線性搜尋比較。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import (ACCENT, MUTED, bst_path_chain, day_chips, fmt, get_system, ideal_height,  # noqa: E402
                    kpi_cards, record_card, section, setup_page, show, tech_panel)

setup_page("預約查詢", "🔍")
st.title("預約查詢")
show('<div class="ns-lead">輸入掛號編號，用 <b>BST</b> 找到這筆預約；同時用陣列從頭找一次，看兩者差多少。</div>')
system = get_system()
day_chips(system)

if len(system.roster) == 0:
    st.warning("今日名單是空的，請到首頁重新載入。")
    st.stop()

roster = system.roster.to_list()

# 換了日期／區域就把預設編號換成新名單中間那筆
if st.session_state.get("search_day") != (system.day, system.neighbourhood):
    st.session_state.search_day = (system.day, system.neighbourhood)
    st.session_state.search_id = roster[len(roster) // 2].appointment_id


def pick(appointment_id):
    st.session_state.search_id = appointment_id


c1, c2 = st.columns([1, 3], vertical_alignment="bottom")
target = int(c1.number_input("掛號編號", step=1, format="%d", key="search_id"))
with c2:
    st.caption("快速帶入今日名單中的編號（也可以輸入不存在的編號，看 BST 走到哪裡停下來）：")
    picks = st.columns(5)
    for col, r in zip(picks, roster[:5]):
        col.button(str(r.appointment_id), key=f"pick_{r.appointment_id}", on_click=pick,
                   args=(r.appointment_id,), width="stretch")

result = system.compare_search(target)
record = result["record"]
bst_cmp, lin_cmp = result["bst"]["comparisons"], result["linear"]["comparisons"]
bst_ms, lin_ms = result["bst"]["ms"], result["linear"]["ms"]

if record:
    record_card(record)
else:
    st.error(f"今日名單中沒有掛號編號 {target}（可能已取消，或不是這一天的預約）。"
             "下方仍可看到 BST 走到哪個空指標才停下。")

# ---- BST vs 線性搜尋 ----
section("BST vs. 陣列線性搜尋（同一個編號、同一份名單）")
ratio = lin_cmp / bst_cmp if bst_cmp else 0
kpi_cards([
    ("BST 比較次數", fmt(bst_cmp), f"耗時 {bst_ms:.4f} ms", ACCENT),
    ("線性搜尋比較次數", fmt(lin_cmp), f"耗時 {lin_ms:.4f} ms", MUTED),
    ("比較次數差距", f"{ratio:,.0f} 倍" if ratio else "—", "線性 ÷ BST", None),
    ("今日 BST 樹高", fmt(result["height"]),
     f"{fmt(result['size'])} 個節點；完全平衡約 {ideal_height(result['size'])}", None),
])
cmp_df = pd.DataFrame({"方法": ["BST 搜尋", "陣列線性搜尋"], "比較次數": [bst_cmp, lin_cmp]})
bars = alt.Chart(cmp_df).mark_bar(cornerRadiusEnd=4, size=26).encode(
    y=alt.Y("方法:N", title=None, sort=None, axis=alt.Axis(labelLimit=200, labelFontSize=13)),
    x=alt.X("比較次數:Q", title="比較次數（本次實際）"),
    color=alt.Color("方法:N", legend=None, scale=alt.Scale(domain=["BST 搜尋", "陣列線性搜尋"],
                                                         range=[ACCENT, MUTED])),
)
text = bars.mark_text(align="left", dx=6, color="#E8EDF4").encode(text=alt.Text("比較次數:Q", format=","))
st.altair_chart((bars + text).properties(height=150), width="stretch")
st.caption("耗時會受電腦與 Python 執行狀況影響，每次不同；比較次數只看演算法，才是公平的比較。")

# ---- 搜尋路徑 ----
section(f"BST 搜尋路徑（實際經過 {len(result['path'])} 個節點，由根往下）")
bst_path_chain(result["path"], target)

tech_panel(
    ["**BST**（key = 掛號編號）：從根開始，比節點小往左、大往右，每比一次排除一半的子樹。",
     "插入前先打亂順序，避免照編號插入時樹退化成一條鏈（O(n)）。",
     "BST 節點存著 Linked List 節點的參照（`ll_node`），找到之後取消預約可以 O(1) 從名單刪除。",
     "對照組 **ArrayStore**：從第一格開始一筆一筆比。"],
    measured=[("BST 比較", f"{fmt(bst_cmp)} 次"), ("線性比較", f"{fmt(lin_cmp)} 次"),
              ("樹高 / 理想高度", f"{result['height']} / {ideal_height(result['size'])}")],
    theory=[("BST 搜尋（平均）", "O(log n)"), ("BST 搜尋（退化）", "O(n)"), ("線性搜尋", "O(n)")],
)
