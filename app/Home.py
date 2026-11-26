"""首頁：選日期與區域、當日總覽、風險分數驗證。

執行（在 noshow_system 資料夾）：streamlit run app/Home.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import (LEVEL_COLOR, LEVEL_ICON, MUTED, day_chips, fmt, get_system, kpi_cards,  # noqa: E402
                    level_bar, section, setup_page, show, tech_panel)
from core.record import validate_risk  # noqa: E402

setup_page("門診預約管理系統", "🏥")
st.title("門診預約管理與未到診風險分析系統")

system = get_system()

# 全部歷史資料的燈號驗證（首頁上下兩處共用）
validation = validate_risk(system.all_records)
total_n = sum(n for n, _ in validation.values())
total_miss = sum(n * rate for n, rate in validation.values())
show(f'<div class="ns-lead">{total_n:,} 筆真實門診預約中，<b>每 5 人約 1 人沒有來</b>'
     f'（未到率 {total_miss / total_n:.1%}）。這個系統幫護理站找出最可能不來的人，有人取消時立刻遞補。</div>')

# ---- 選日期與區域（測試依賴：第 1 個 selectbox = 看診日、第 1 個 button = 載入） ----
c1, c2, c3 = st.columns([2, 3, 1], vertical_alignment="bottom")
days = system.days()
day = c1.selectbox("看診日", days, index=days.index(system.day))
areas = system.neighbourhoods(day)                       # 依選到的日期列出區域
options = ["（全部區域）"] + [f"{name}（{count} 人）" for name, count in areas]
current = 0
names = [name for name, _ in areas]
if system.neighbourhood in names and day == system.day:
    current = names.index(system.neighbourhood) + 1
choice = c2.selectbox("區域（篩成 20~100 人比較像一間診間）", options, index=current)
if c3.button("載入", type="primary", width="stretch"):
    area = None if choice == options[0] else names[options.index(choice) - 1]
    info = system.load_day(day, area)
    msg = f"已載入 {info['day']}，共 {info['count']} 人"
    if info["replayed"]:
        msg += f"；已依 log 恢復 {info['replayed']} 筆上次的操作"
    st.success(msg)

day_chips(system)

# ---- 今日指標 ----
counts = system.level_counts()
expected = system.expected_noshow()
n = len(system.roster)
kpi_cards([
    ("當日預約", fmt(n), "Linked List `roster` 的節點數", None),
    ("紅燈（風險 ≥ 70）", fmt(counts["紅"]), f"{counts['紅'] / n:.1%}" if n else "—", LEVEL_COLOR["紅"]),
    ("黃燈（40~69）", fmt(counts["黃"]), f"{counts['黃'] / n:.1%}" if n else "—", LEVEL_COLOR["黃"]),
    ("綠燈（< 40）", fmt(counts["綠"]), f"{counts['綠'] / n:.1%}" if n else "—", LEVEL_COLOR["綠"]),
    ("預估未到", f"{expected:,.1f} 人", "校正表估計（同分者歷史未到率加總）", MUTED),
])
level_bar(counts)

# ---- 當日名單 ----
section("當日名單（依風險由高到低）")
df = pd.DataFrame(system.overview())
if not df.empty:
    df["燈號"] = df["燈號"].map(LEVEL_ICON)
    df["簡訊"] = df["簡訊"].map({True: "有", False: "無"})
    df["慢性病"] = df["慢性病"].map({True: "有", False: "無"})
st.dataframe(
    df, width="stretch", hide_index=True, height=360,
    column_config={
        "風險": st.column_config.ProgressColumn("風險", min_value=0, max_value=100, format="%d"),
        "掛號編號": st.column_config.NumberColumn(format="%d"),
        "病患編號": st.column_config.NumberColumn(format="%d"),
    })

tech_panel(
    ["名單 = **Doubly Linked List**（`roster`）：表格是從 head 走到 tail 依序列出。",
     "取消時拿到節點就能 O(1) 拆鏈，不用像陣列把後面的人往前搬。",
     "預估未到 = 每人的分數換成「歷史上同分者的實際未到率」（校正表 dict）再加總。"],
    measured=[("走訪節點數", fmt(n)), ("預估未到", f"{expected:,.1f} 人")],
    theory=[("走訪名單", "O(n)"), ("刪除已知節點", "O(1)"), ("預估未到", "O(n)")],
)

# ---- 風險分數驗證 ----
section("風險分數有沒有用？（全部歷史資料）")
chart_df = pd.DataFrame({
    "燈號": [f"{k}燈" for k in validation],
    "實際未到率": [rate * 100 for _, rate in validation.values()],
    "人數": [cnt for cnt, _ in validation.values()],
})
c1, c2 = st.columns([3, 2])
with c1:
    bars = alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=56).encode(
        x=alt.X("燈號:N", sort=["紅燈", "黃燈", "綠燈"], title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("實際未到率:Q", title="實際未到率 (%)",
                scale=alt.Scale(domain=[0, chart_df["實際未到率"].max() * 1.18])),
        color=alt.Color("燈號:N", legend=None, scale=alt.Scale(
            domain=["紅燈", "黃燈", "綠燈"], range=[LEVEL_COLOR["紅"], LEVEL_COLOR["黃"], LEVEL_COLOR["綠"]])),
        tooltip=["燈號", alt.Tooltip("實際未到率:Q", format=".1f"), alt.Tooltip("人數:Q", format=",")],
    )
    labels = bars.mark_text(dy=-8, color="#E8EDF4", fontSize=13).encode(
        text=alt.Text("實際未到率:Q", format=".1f"))
    st.altair_chart((bars + labels).properties(height=260), width="stretch")
with c2:
    red, green = validation["紅"][1], validation["綠"][1]
    kpi_cards([("紅燈 ÷ 綠燈 未到率", f"{red / green:.1f} 倍" if green else "—",
                f"{red:.1%} vs {green:.1%}", LEVEL_COLOR["紅"])])
    show(f'<div class="ns-note">各燈號人數：紅 {validation["紅"][0]:,}、黃 {validation["黃"][0]:,}、'
         f'綠 {validation["綠"][0]:,}。<br>紅燈的人實際未到率明顯高於綠燈，代表分數能用來<b>排序</b>。'
         '<br>這是用同一份資料訂權重再驗證（樣本內驗證），會高估效果；分數不等於機率，估人數要用校正表。</div>')
