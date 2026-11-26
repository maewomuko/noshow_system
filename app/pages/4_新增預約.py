"""新增預約：PatientBST 叫出病患舊紀錄 → 算風險 → 插入所有當日結構。"""

import html
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common import (ACCENT, LEVEL_COLOR, MUTED, day_chips, get_system, kpi_cards,  # noqa: E402
                    record_card, section, setup_page, show, steps, tech_panel)

setup_page("新增預約", "➕")
st.title("新增預約")
show('<div class="ns-lead">櫃台幫病人掛號：用<b>病患索引 PatientBST</b> 叫出他以前的紀錄、算出風險，'
     '再把新預約同時寫進所有當日結構。</div>')
system = get_system()
day_chips(system)

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

# 測試依賴：第 1 個 number_input = 病患編號、第 1 個 button = 送出
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
    sms = c6.checkbox("有收到簡訊（只記錄，不計分）")
    chronic = c6.checkbox("高血壓或糖尿病（只記錄，不計分）")
    submitted = st.form_submit_button("新增預約", type="primary")

out = None
if submitted:
    try:
        out = system.add(patient_id=int(patient_id), age=int(age),
                         scheduled_day=scheduled.isoformat(), gender=gender,
                         sms=sms, chronic=chronic)
    except ValueError as e:
        st.error(str(e))

if out:
    r = out["record"]
    st.success(f"已新增掛號編號 {r.appointment_id}")
    ranking = [x.appointment_id for x in system.top_risk(len(system.roster))]
    rank = ranking.index(r.appointment_id) + 1
    who = "新病患（索引中查無紀錄）" if out["is_new"] else f"舊病患（{out['history']} 筆舊紀錄）"
    record_card(r, title=f"新預約 {r.appointment_id}")
    kpi_cards([
        ("病患", who, None, None),
        ("今日風險排名", f"第 {rank} 名", f"共 {len(system.roster):,} 人", LEVEL_COLOR["紅"] if rank <= 10 else None),
        ("病患索引查詢", f"{out['comparisons']} 次比較", f"{out['ms']:.4f} ms", ACCENT),
    ])

    section("這筆預約寫進了哪些結構")
    steps([("PatientBST `search`", f"查病患 · {out['comparisons']} 次比較"),
           ("`calc_risk`", f"算風險 {r.risk:.0f} 分"),
           ("Linked List `append`", "O(1)"), ("BST `insert`", "O(log n)"),
           ("Max-Heap `push`", "O(log n)"), ("陣列 `append`", "對照組 O(1)"),
           ("PatientBST `insert`", "O(log P)")])

    history, _, _ = system.patient_history(int(patient_id))
    if history:
        section(f"病患 {int(patient_id)} 的所有預約（PatientBST 節點裡的 list，依看診日排序）")
        items = []
        for h in history:
            if h.showed_up is None:
                dot, status = ACCENT, "尚未看診"
            elif h.showed_up:
                dot, status = LEVEL_COLOR["綠"], "有到診"
            else:
                dot, status = LEVEL_COLOR["紅"], "沒來"
            new = "　← 剛新增" if h is r else ""
            items.append(f'<div class="ns-tl-item" style="--dot:{dot}"><b>{html.escape(h.appointment_day)}</b>'
                         f'　{status}<small>掛號 {h.appointment_id}・風險 {h.risk:.0f}{new}</small></div>')
        show('<div class="ns-timeline">' + "".join(items) + "</div>")

tech_panel(
    ["**病患索引 PatientBST**（key = 病患編號）：找到這個人，節點裡存他所有預約，"
     "數「看診日之前沒來幾次」就是過往未到次數 → 算風險。只算這一個人，其他 10 萬筆不用重算。",
     "同一份資料用不同 key 建兩棵 BST：掛號編號查單筆預約、病患編號查一個人的全部紀錄（資料庫索引的概念）。",
     "新預約的 `showed_up = None`（還沒看診），不會被拿去驗證風險分數。"],
    measured=([("病患索引查詢", f"{out['comparisons']} 次比較"), ("新預約風險", f"{out['record'].risk:.0f} 分")]
              if out else [("病患索引大小", f"{len(system.patients):,} 位病患")]),
    theory=[("PatientBST 查詢", "O(log P)"), ("Linked List `append`", "O(1)"),
            ("BST / Heap 插入", "O(log n)")],
)
show(f'<div class="ns-note" style="color:{MUTED}">P = 病患人數，n = 今日名單人數。</div>')
