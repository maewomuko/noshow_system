"""首頁：選日期與區域、當日總覽。

執行（在 noshow_system 資料夾）：streamlit run app/Home.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import LEVEL_ICON, day_caption, get_system, structure_box  # noqa: E402
from core.record import validate_risk  # noqa: E402

st.set_page_config(page_title="門診預約管理系統", page_icon="🏥", layout="wide")
st.title("🏥 門診預約管理與未到診風險分析系統")
st.write("用 106,982 筆真實門診資料，展示 BST、Max-Heap、Linked List、Queue 如何支援"
         "「找出最可能未到診的病患」與「取消後立即遞補」。左側選單可切換各功能頁。")

system = get_system()

# ---- 選日期與區域 ----
c1, c2, c3 = st.columns([2, 3, 1])
days = system.days()
day = c1.selectbox("看診日", days, index=days.index(system.day))
areas = system.neighbourhoods(day)                       # 依選到的日期列出區域
options = ["（全部區域）"] + [f"{name}（{count} 人）" for name, count in areas]
current = 0
names = [name for name, _ in areas]
if system.neighbourhood in names and day == system.day:
    current = names.index(system.neighbourhood) + 1
choice = c2.selectbox("區域（篩成 20~100 人比較像一間診間）", options, index=current)
c3.write("")
c3.write("")
if c3.button("載入", type="primary", width="stretch"):
    area = None if choice == options[0] else names[options.index(choice) - 1]
    info = system.load_day(day, area)
    msg = f"已載入 {info['day']}，共 {info['count']} 人"
    if info["replayed"]:
        msg += f"；已依 log 恢復 {info['replayed']} 筆上次的操作"
    st.success(msg)

day_caption(system)

# ---- 指標 ----
counts = system.level_counts()
expected = system.expected_noshow()
m = st.columns(5)
m[0].metric("當日人數", len(system.roster))
m[1].metric("🔴 紅燈", counts["紅"])
m[2].metric("🟡 黃燈", counts["黃"])
m[3].metric("🟢 綠燈", counts["綠"])
m[4].metric("預估未到", f"{expected:.1f} 人")

# ---- 總覽表 ----
st.subheader("當日名單")
df = pd.DataFrame(system.overview())
if not df.empty:
    df["燈號"] = df["燈號"].map(LEVEL_ICON)
st.dataframe(df, width="stretch", hide_index=True, height=360)

structure_box([
    "名單 = **Doubly Linked List**（`roster`）：從 head 走到 tail 列出全部，O(n)；取消時刪節點 O(1)。",
    "預估未到 = 把每人的風險分數換成「歷史上同分者的實際未到率」再加總（校正表 dict），O(n)。",
])

# ---- 風險分數驗證 ----
st.subheader("風險分數有沒有用？（全部歷史資料）")
v = validate_risk(system.all_records)
chart = pd.DataFrame({"燈號": [LEVEL_ICON[k] for k in v],
                      "實際未到率 (%)": [round(rate * 100, 1) for _, rate in v.values()],
                      "人數": [n for n, _ in v.values()]})
c1, c2 = st.columns([3, 2])
c1.bar_chart(chart, x="燈號", y="實際未到率 (%)")
c2.dataframe(chart, hide_index=True, width="stretch")
c2.caption("紅燈的人實際未到率明顯高於綠燈，代表分數能用來排序。"
           "分數不等於機率，估人數時要用校正表。")
