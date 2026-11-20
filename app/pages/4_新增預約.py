"""新增預約：PatientBST 叫出病患舊紀錄 → 算風險 → 插入所有當日結構。"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import day_caption, get_system, level_label, record_table, structure_box  # noqa: E402

st.set_page_config(page_title="新增預約", page_icon="➕", layout="wide")
st.title("➕ 新增預約")
system = get_system()
day_caption(system)

day = date.fromisoformat(system.day)

# 方便 Demo：列出幾位「以前常沒來」的舊病患編號
examples = []
seen = set()
for r in system.all_records:
    if r.past_noshow >= 2 and r.appointment_day < system.day and r.patient_id not in seen:
        examples.append(r.patient_id)
        seen.add(r.patient_id)
    if len(examples) >= 3:
        break
st.caption(f"試試看：舊病患（以前沒來 2 次以上）{', '.join(map(str, examples))}；"
           "或輸入一個不存在的編號當新病患，例如 1。")

with st.form("add"):
    c1, c2, c3 = st.columns(3)
    patient_id = c1.number_input("病患編號", min_value=1, value=examples[0] if examples else 1,
                                 step=1, format="%d")
    age = c2.number_input("年齡", min_value=0, max_value=120, value=25, step=1)
    gender = c3.selectbox("性別", ["F", "M"])
    c4, c5, c6 = st.columns(3)
    scheduled = c4.date_input("預約日（哪天打電話來約）", value=day, max_value=day)
    c5.text_input("看診日", value=system.day, disabled=True,
                  help="只能新增目前載入的這一天，要換日期請到首頁")
    sms = c6.checkbox("有收到簡訊")
    chronic = c6.checkbox("高血壓或糖尿病")
    submitted = st.form_submit_button("新增預約", type="primary")

if submitted:
    try:
        out = system.add(patient_id=int(patient_id), age=int(age),
                         scheduled_day=scheduled.isoformat(), gender=gender,
                         sms=sms, chronic=chronic)
    except ValueError as e:
        st.error(str(e))
    else:
        r = out["record"]
        st.success(f"已新增掛號編號 {r.appointment_id}")
        cols = st.columns(5)
        cols[0].metric("病患", "新病患" if out["is_new"] else f"舊病患（{out['history']} 筆紀錄）")
        cols[1].metric("等待天數", r.wait_days)
        cols[2].metric("過往未到", r.past_noshow)
        cols[3].metric("風險分數", f"{r.risk:.0f}")
        cols[4].metric("燈號", level_label(r.risk))
        rank = [x.appointment_id for x in system.top_risk(len(system.roster))].index(r.appointment_id)
        st.write(f"在今日 {len(system.roster)} 人中排第 **{rank + 1}** 名"
                 f"（病患索引查詢比較 {out['comparisons']} 次，{out['ms']:.4f} ms）。")

        history, _, _ = system.patient_history(int(patient_id))
        if history:
            st.subheader("這位病患的所有預約（病患索引節點裡的 list）")
            rows = record_table(history)
            for row, h in zip(rows, history):
                row["看診日"] = h.appointment_day
                row["有到診"] = {True: "✔", False: "✘ 沒來", None: "（尚未看診）"}[h.showed_up]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

structure_box([
    "**病患索引 PatientBST**（key = 病患編號）：O(log n) 找到這個人，節點裡存他所有預約，"
    "數有幾次沒來 → 算風險。只算這一個人，其他 10 萬筆不用重算。",
    "**插入**：Linked List `append` O(1) → BST `insert` O(log n) → Max-Heap `push` O(log n) → "
    "病患索引 `insert` O(log n)。",
    "同一份資料用不同 key 建兩棵 BST：掛號編號查單筆預約、病患編號查一個人的全部紀錄。",
])
