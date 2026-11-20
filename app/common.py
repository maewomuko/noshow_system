"""Streamlit 各頁共用：取得系統物件、畫樹狀圖、顯示「背後的資料結構」。

規則（CLAUDE.md）：畫面只呼叫 AppointmentSystem，不直接改各個結構；
系統物件存在 st.session_state，按按鈕重跑時才不會遺失狀態。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.record import risk_level  # noqa: E402
from core.system import AppointmentSystem, DEFAULT_LOG_DIR  # noqa: E402

DEFAULT_DAY = "2016-06-06"
LEVEL_ICON = {"紅": "🔴 紅", "黃": "🟡 黃", "綠": "🟢 綠"}
LEVEL_COLOR = {"紅": "#f8b4b4", "黃": "#fde68a", "綠": "#bbf7d0"}


def get_system():
    """第一次呼叫時讀檔建系統並載入預設日期；之後都從 session_state 拿同一個物件。"""
    if "system" not in st.session_state:
        log_dir = os.environ.get("NOSHOW_LOG_DIR") or DEFAULT_LOG_DIR   # 測試時可改到暫存資料夾
        with st.spinner("讀取 106,982 筆資料、建立病患索引中…（約 2 秒）"):
            system = AppointmentSystem.load(log_dir=log_dir)
            system.load_day(DEFAULT_DAY)
        st.session_state.system = system
    return st.session_state.system


def day_caption(system):
    area = system.neighbourhood or "全部區域"
    st.caption(f"目前載入：{system.day}｜{area}｜{len(system.roster)} 人"
               "　（到「首頁」可切換日期與區域）")


def structure_box(lines):
    """每頁的「背後的資料結構」說明，簡報截圖時用紅框框這一塊。"""
    st.info("**背後的資料結構**\n\n" + "\n\n".join(lines))


def level_label(risk):
    return LEVEL_ICON[risk_level(risk)]


def record_table(records):
    """Record list → 表格用的 list of dict。"""
    return [{
        "掛號編號": r.appointment_id,
        "病患編號": r.patient_id,
        "年齡": r.age,
        "等待天數": r.wait_days,
        "過往未到": r.past_noshow,
        "風險": r.risk,
        "燈號": level_label(r.risk),
    } for r in records]


def bst_path_dot(path, target):
    """BST 搜尋路徑圖：只畫經過的節點，左轉／右轉標在箭頭上。"""
    lines = ['digraph G {', 'rankdir=TB;', 'node [shape=circle, fontsize=10, style=filled, '
             'fillcolor="#e0e7ff"];']
    for i, key in enumerate(path):
        color = "#86efac" if key == target else "#e0e7ff"
        lines.append(f'n{i} [label="{key}", fillcolor="{color}"];')
        if i > 0:
            side = "左（較小）" if key < path[i - 1] else "右（較大）"
            lines.append(f'n{i - 1} -> n{i} [label="{side}", fontsize=9];')
    if path and path[-1] != target:
        lines.append(f'miss [label="找不到\\n{target}", shape=box, fillcolor="#fecaca"];')
        lines.append(f'n{len(path) - 1} -> miss [style=dashed];')
    lines.append("}")
    return "\n".join(lines)


def heap_dot(records):
    """Heap 前幾層：陣列索引 i 的子節點是 2i+1、2i+2。"""
    lines = ['digraph H {', 'node [shape=box, style="rounded,filled", fontsize=10];']
    for i, r in enumerate(records):
        color = LEVEL_COLOR[risk_level(r.risk)]
        lines.append(f'h{i} [label="[{i}] 風險 {r.risk:.0f}\\n#{r.appointment_id}", '
                     f'fillcolor="{color}"];')
        if i > 0:
            lines.append(f'h{(i - 1) // 2} -> h{i};')
    lines.append("}")
    return "\n".join(lines)
