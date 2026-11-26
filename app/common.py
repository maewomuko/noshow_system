"""Streamlit 各頁共用：取得系統物件、深色主題元件、結構圖。

規則（CLAUDE.md）：畫面只呼叫 AppointmentSystem，不直接改各個結構；
系統物件存在 st.session_state，按按鈕重跑時才不會遺失狀態。
本檔只負責「怎麼顯示」，所有數字都來自系統方法的回傳值或實驗 CSV。
"""

import html
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core.record import AGE_POINTS, PAST_MAX, PAST_POINTS, WAIT_POINTS, risk_level  # noqa: E402
from core.system import AppointmentSystem, DEFAULT_LOG_DIR  # noqa: E402

DEFAULT_DAY = "2016-06-06"

# ---- 色票（與簡報相同，SKILL.md 6.1） ----
BG = "#101C2C"
CARD = "#1B2D43"
CARD_2 = "#22385A"
ACCENT = "#36B6AC"
TEXT = "#E8EDF4"
MUTED = "#8FA8C4"
LINE = "#2C4566"
LEVEL_COLOR = {"紅": "#D94B4B", "黃": "#D9A441", "綠": "#3FA35B"}
LEVEL_ICON = {"紅": "🔴 紅", "黃": "🟡 黃", "綠": "🟢 綠"}


# ---------------------------------------------------------------------------
# 系統物件
# ---------------------------------------------------------------------------

def get_system():
    """第一次呼叫時讀檔建系統並載入預設日期；之後都從 session_state 拿同一個物件。"""
    if "system" not in st.session_state:
        log_dir = os.environ.get("NOSHOW_LOG_DIR") or DEFAULT_LOG_DIR   # 測試時可改到暫存資料夾
        with st.spinner("讀取 106,982 筆資料、建立病患索引中…（約 2 秒）"):
            system = AppointmentSystem.load(log_dir=log_dir)
            system.load_day(DEFAULT_DAY)
        st.session_state.system = system
    return st.session_state.system


# ---------------------------------------------------------------------------
# 全域樣式
# ---------------------------------------------------------------------------

_CSS = f"""
<style>
.block-container {{ padding-top: 2.2rem; max-width: 1400px; }}
h1 {{ letter-spacing: .02em; }}
.ns-lead {{ color: {MUTED}; font-size: 1.02rem; margin: -.4rem 0 1rem; }}
.ns-lead b {{ color: {TEXT}; }}
.ns-chips {{ display: flex; gap: .5rem; flex-wrap: wrap; margin: .2rem 0 1rem; }}
.ns-chip {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 999px;
           padding: .2rem .8rem; font-size: .86rem; color: {MUTED}; }}
.ns-chip b {{ color: {TEXT}; font-weight: 600; }}
.ns-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
           gap: .75rem; margin: .4rem 0 1rem; }}
.ns-kpi {{ background: {CARD}; border: 1px solid {LINE}; border-left: 4px solid var(--accent, {ACCENT});
          border-radius: 10px; padding: .75rem 1rem; }}
.ns-kpi-label {{ color: {MUTED}; font-size: .82rem; }}
.ns-kpi-value {{ color: {TEXT}; font-size: 1.75rem; font-weight: 700; line-height: 1.25;
                font-variant-numeric: tabular-nums; }}
.ns-kpi-sub {{ color: {MUTED}; font-size: .78rem; margin-top: .1rem; }}
.ns-bar {{ display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin: .2rem 0 .35rem; }}
.ns-bar-legend {{ display: flex; gap: 1.2rem; color: {MUTED}; font-size: .8rem; margin-bottom: 1rem; }}
.ns-badge {{ display: inline-flex; align-items: center; gap: .3rem; padding: .05rem .55rem;
            border-radius: 999px; font-size: .82rem; font-weight: 600; white-space: nowrap; }}
.ns-badge::before {{ content: ""; width: .55rem; height: .55rem; border-radius: 50%;
                    background: currentColor; }}
.ns-tech {{ background: linear-gradient(180deg, {CARD} 0%, #172739 100%); border: 1px solid {LINE};
           border-top: 3px solid {ACCENT}; border-radius: 12px; padding: 1rem 1.2rem; margin: 1.2rem 0; }}
.ns-tech-head {{ color: {ACCENT}; font-weight: 700; letter-spacing: .08em; font-size: .85rem;
                margin-bottom: .6rem; }}
.ns-tech-grid {{ display: grid; grid-template-columns: 1.6fr 1fr 1fr; gap: 1.2rem; }}
.ns-tech-grid h4 {{ color: {MUTED}; font-size: .78rem; font-weight: 600; margin: 0 0 .4rem;
                   text-transform: none; letter-spacing: .05em; }}
.ns-tech-grid ul {{ margin: 0; padding-left: 1.1rem; }}
.ns-tech-grid li {{ margin-bottom: .35rem; font-size: .9rem; line-height: 1.5; }}
.ns-kv {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
.ns-kv td {{ padding: .22rem 0; border-bottom: 1px dashed {LINE}; vertical-align: top; }}
.ns-kv td:last-child {{ text-align: right; color: {TEXT}; font-weight: 600;
                       font-variant-numeric: tabular-nums; }}
.ns-kv td:first-child {{ color: {MUTED}; }}
code, .ns-mono {{ font-family: "JetBrains Mono", Consolas, monospace; }}
.ns-card {{ background: {CARD}; border: 1px solid {LINE}; border-left: 5px solid var(--accent, {ACCENT});
           border-radius: 12px; padding: 1rem 1.2rem; margin: .4rem 0 1rem; }}
.ns-card-top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
               flex-wrap: wrap; }}
.ns-card-id {{ font-size: 1.35rem; font-weight: 700; }}
.ns-card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
                gap: .6rem; margin-top: .8rem; }}
.ns-field small {{ display: block; color: {MUTED}; font-size: .75rem; }}
.ns-field span {{ font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.ns-score {{ display: flex; align-items: center; gap: .5rem; margin-top: .9rem; flex-wrap: wrap;
            font-size: .9rem; }}
.ns-score-part {{ background: {CARD_2}; border-radius: 8px; padding: .3rem .7rem; }}
.ns-score-part b {{ font-variant-numeric: tabular-nums; }}
.ns-score-total {{ background: var(--accent, {ACCENT}); color: {BG}; border-radius: 8px;
                  padding: .3rem .8rem; font-weight: 700; }}
.ns-note {{ color: {MUTED}; font-size: .82rem; margin-top: .5rem; }}
.ns-row {{ display: grid; grid-template-columns: 2.4rem 6.5rem 5.2rem 1fr 4.5rem 4.5rem;
          align-items: center; gap: .6rem; background: {CARD}; border: 1px solid {LINE};
          border-radius: 10px; padding: .45rem .8rem; min-height: 2.6rem; font-size: .9rem; }}
.ns-row-head {{ background: transparent; border: none; color: {MUTED}; font-size: .78rem;
               min-height: auto; padding-top: 0; padding-bottom: 0; }}
.ns-rank {{ color: {MUTED}; font-weight: 700; font-variant-numeric: tabular-nums; }}
.ns-riskbar {{ display: flex; align-items: center; gap: .5rem; }}
.ns-riskbar-track {{ flex: 1; height: 8px; background: {BG}; border-radius: 4px; overflow: hidden; }}
.ns-riskbar-fill {{ height: 100%; border-radius: 4px; }}
.ns-num {{ font-variant-numeric: tabular-nums; }}
.ns-queue {{ display: flex; align-items: stretch; gap: .35rem; overflow-x: auto; padding: .3rem 0 .6rem; }}
.ns-qend {{ display: flex; flex-direction: column; justify-content: center; color: {ACCENT};
           font-size: .75rem; font-weight: 700; padding: 0 .3rem; white-space: nowrap; }}
.ns-qnode {{ min-width: 128px; background: {CARD}; border: 1px solid {LINE};
            border-top: 4px solid var(--accent, {ACCENT}); border-radius: 10px; padding: .5rem .7rem; }}
.ns-qnode.front {{ box-shadow: 0 0 0 2px {ACCENT}; }}
.ns-qnode small {{ color: {MUTED}; font-size: .72rem; display: block; }}
.ns-qarrow {{ display: flex; align-items: center; color: {MUTED}; font-size: 1.1rem; }}
.ns-steps {{ display: flex; gap: .4rem; flex-wrap: wrap; margin: .4rem 0 1rem; }}
.ns-step {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 10px; padding: .45rem .75rem;
           font-size: .85rem; min-width: 120px; }}
.ns-step small {{ display: block; color: {MUTED}; font-size: .72rem; }}
.ns-step b {{ color: {ACCENT}; }}
.ns-steparrow {{ display: flex; align-items: center; color: {MUTED}; }}
.ns-strip {{ display: grid; grid-template-columns: repeat(15, minmax(0, 1fr)); gap: 3px; margin: .3rem 0; }}
.ns-strip div {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 6px; text-align: center;
                padding: .25rem 0; font-size: .78rem; font-variant-numeric: tabular-nums; }}
.ns-strip div small {{ display: block; color: {MUTED}; font-size: .65rem; }}
.ns-strip div.hit {{ box-shadow: inset 0 0 0 2px {ACCENT}; }}
.ns-timeline {{ border-left: 2px solid {LINE}; margin: .4rem 0 0 .4rem; padding-left: 1rem; }}
.ns-tl-item {{ position: relative; padding: .25rem 0 .55rem; font-size: .9rem; }}
.ns-tl-item::before {{ content: ""; position: absolute; left: -1.38rem; top: .55rem; width: .62rem;
                      height: .62rem; border-radius: 50%; background: var(--dot, {MUTED}); }}
.ns-tl-item small {{ color: {MUTED}; margin-left: .4rem; }}
.ns-callout {{ background: rgba(217,164,65,.10); border: 1px solid rgba(217,164,65,.45);
              border-radius: 10px; padding: .7rem 1rem; margin: .6rem 0 1rem; font-size: .9rem; }}
.ns-callout b {{ color: #D9A441; }}
.ns-path {{ display: flex; flex-wrap: wrap; align-items: center; gap: .35rem .2rem; margin: .4rem 0 1rem; }}
.ns-pathnode {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 10px; padding: .35rem .7rem;
               text-align: center; min-width: 92px; }}
.ns-pathnode b {{ display: block; font-variant-numeric: tabular-nums; }}
.ns-pathnode small {{ display: block; font-size: .7rem; opacity: .8; }}
.ns-pathnode.miss {{ background: #3A1E24; border: 1px dashed #D94B4B; color: #F0B4B4; }}
.ns-pathedge {{ color: {ACCENT}; font-size: .78rem; font-weight: 700; text-align: center; padding: 0 .15rem; }}
.ns-pathedge small {{ display: block; color: {MUTED}; font-weight: 400; font-size: .65rem;
                     font-variant-numeric: tabular-nums; }}
.ns-section {{ color: {MUTED}; font-size: .8rem; letter-spacing: .12em; font-weight: 700;
              margin: 1.4rem 0 .3rem; }}
@media (max-width: 900px) {{ .ns-tech-grid {{ grid-template-columns: 1fr; }} }}
</style>
"""


def setup_page(title, icon):
    """每頁開頭呼叫：設定頁面 + 套用共用樣式。"""
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)


def md_inline(text):
    """把說明文字裡的 `code` 與 **粗體** 轉成 HTML（其餘內容先跳脫）。"""
    s = html.escape(str(text))
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    return s


def show(html_text):
    st.markdown(html_text, unsafe_allow_html=True)


def section(label):
    show(f'<div class="ns-section">{html.escape(label)}</div>')


# ---------------------------------------------------------------------------
# 小元件
# ---------------------------------------------------------------------------

def fmt(n, digits=0):
    """數字加千分位。"""
    if isinstance(n, float) and digits:
        return f"{n:,.{digits}f}"
    return f"{n:,.0f}" if isinstance(n, float) else f"{n:,}"


def day_chips(system):
    """頁首：目前載入的日期／區域／人數。"""
    area = system.neighbourhood or "全部區域"
    show('<div class="ns-chips">'
         f'<span class="ns-chip">看診日 <b>{html.escape(system.day)}</b></span>'
         f'<span class="ns-chip">區域 <b>{html.escape(area)}</b></span>'
         f'<span class="ns-chip">當日名單 <b>{len(system.roster):,} 人</b></span>'
         '<span class="ns-chip">到「首頁」切換日期與區域</span></div>')


# 舊名稱保留，避免其他地方還在用
day_caption = day_chips


def kpi_cards(items):
    """items：[(標籤, 數值字串, 小字說明, 強調色或 None)]。"""
    cells = []
    for label, value, sub, color in items:
        style = f' style="--accent:{color}"' if color else ""
        sub_html = f'<div class="ns-kpi-sub">{md_inline(sub)}</div>' if sub else ""
        cells.append(f'<div class="ns-kpi"{style}><div class="ns-kpi-label">{html.escape(label)}</div>'
                     f'<div class="ns-kpi-value">{html.escape(str(value))}</div>{sub_html}</div>')
    show('<div class="ns-kpis">' + "".join(cells) + "</div>")


def level_badge(risk):
    level = risk_level(risk)
    color = LEVEL_COLOR[level]
    return (f'<span class="ns-badge" style="color:{color};background:{color}22">{level}燈</span>')


def level_label(risk):
    """表格用文字燈號（含 emoji，不只靠顏色）。"""
    return LEVEL_ICON[risk_level(risk)]


def level_bar(counts):
    """紅黃綠比例條。counts = {"紅": n, "黃": n, "綠": n}。"""
    total = sum(counts.values()) or 1
    parts = "".join(f'<div style="width:{counts[k] / total * 100:.2f}%;background:{LEVEL_COLOR[k]}"></div>'
                    for k in ("紅", "黃", "綠") if counts[k])
    legend = "".join(f'<span><span style="color:{LEVEL_COLOR[k]}">●</span> {k}燈 {counts[k]:,} 人'
                     f'（{counts[k] / total:.1%}）</span>' for k in ("紅", "黃", "綠"))
    show(f'<div class="ns-bar">{parts}</div><div class="ns-bar-legend">{legend}</div>')


def tech_panel(structure, measured=None, theory=None, title="背後的資料結構"):
    """技術面板：結構與操作（文字）／本次實測（數字）／理論複雜度，三者分開。

    structure：說明句子 list（可用 `code` 與 **粗體**）
    measured、theory：[(名稱, 值)]
    """
    def kv(rows):
        if not rows:
            return '<div class="ns-note">—</div>'
        return '<table class="ns-kv">' + "".join(
            f"<tr><td>{md_inline(k)}</td><td>{md_inline(v)}</td></tr>" for k, v in rows) + "</table>"

    items = "".join(f"<li>{md_inline(s)}</li>" for s in structure)
    show(f'<div class="ns-tech"><div class="ns-tech-head">{html.escape(title)}</div>'
         f'<div class="ns-tech-grid"><div><h4>結構與操作</h4><ul>{items}</ul></div>'
         f'<div><h4>本次實際測量</h4>{kv(measured)}</div>'
         f'<div><h4>理論時間複雜度</h4>{kv(theory)}</div></div></div>')


# 舊名稱保留：只有說明文字的技術面板
def structure_box(lines):
    tech_panel(lines)


# ---------------------------------------------------------------------------
# 風險分數拆解（只顯示；規則與 core/record.py 的 calc_risk 相同，常數直接引用）
# ---------------------------------------------------------------------------

def _points(table, value):
    for upper, pts in table:
        if upper is None or value <= upper:
            return pts
    return 0


def risk_parts(r):
    """回傳 [(因素, 條件, 分數)]，三項加總 = calc_risk 的結果。"""
    wait = _points(WAIT_POINTS, r.wait_days)
    past = PAST_POINTS.get(r.past_noshow, PAST_MAX)
    age = _points(AGE_POINTS, r.age)
    return [("等待天數", f"{r.wait_days} 天", wait),
            ("過往未到", f"{r.past_noshow} 次", past),
            ("年齡", f"{r.age} 歲", age)]


def record_card(r, title=None, extra_fields=()):
    """病歷卡：燈號色邊框、欄位、計分拆解。"""
    level = risk_level(r.risk)
    color = LEVEL_COLOR[level]
    fields = [("病患編號", f"{r.patient_id}"), ("年齡／性別", f"{r.age}／{r.gender}"),
              ("等待天數", f"{r.wait_days} 天"), ("過往未到", f"{r.past_noshow} 次"),
              ("看診日", r.appointment_day), ("區域", r.neighbourhood or "—"),
              ("簡訊（不計分）", "有" if r.sms else "無"), ("慢性病（不計分）", "有" if r.chronic else "無"),
              *extra_fields]
    grid = "".join(f'<div class="ns-field"><small>{html.escape(k)}</small>'
                   f'<span>{html.escape(str(v))}</span></div>' for k, v in fields)
    parts = risk_parts(r)
    rule_total = sum(p for _, _, p in parts)
    score = " <span>＋</span> ".join(
        f'<span class="ns-score-part">{k} {html.escape(c)} → <b>{p}</b></span>' for k, c, p in parts)
    note = ""
    if rule_total != r.risk:
        note = (f'<div class="ns-note">依規則計分為 {rule_total} 分；目前風險 {r.risk:.0f} 分'
                f'（已電訪「確認會到」，風險被調降）。</div>')
    head = html.escape(title or f"掛號編號 {r.appointment_id}")
    show(f'<div class="ns-card" style="--accent:{color}"><div class="ns-card-top">'
         f'<span class="ns-card-id">{head}</span>'
         f'<span>風險 <b style="font-size:1.3rem">{r.risk:.0f}</b> / 100　{level_badge(r.risk)}</span></div>'
         f'<div class="ns-card-grid">{grid}</div>'
         f'<div class="ns-score">{score}<span>＝</span>'
         f'<span class="ns-score-total" style="--accent:{color}">{rule_total} 分</span></div>{note}'
         '<div class="ns-note">規則式計分（不是機器學習）；分數用來排序，不等於未到機率。</div></div>')


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


def ideal_height(n):
    """n 個節點的完全平衡二元樹高度 ⌈log₂(n+1)⌉。"""
    return math.ceil(math.log2(n + 1)) if n > 0 else 0


# ---------------------------------------------------------------------------
# 結構圖（graphviz，深色）
# ---------------------------------------------------------------------------

_DOT_BASE = (f'bgcolor="transparent"; node [fontname="Helvetica", fontcolor="{TEXT}", '
             f'color="{LINE}", penwidth=1.4]; edge [color="{MUTED}", fontcolor="{MUTED}", '
             'fontname="Helvetica", fontsize=9];')


def bst_path_dot(path, target):
    """BST 搜尋路徑圖（graphviz 版，目前頁面改用 bst_path_chain）：只畫經過的節點。"""
    lines = ["digraph G {", "rankdir=TB;", _DOT_BASE,
             f'node [shape=box, style="rounded,filled", fillcolor="{CARD}", fontsize=11];']
    for i, key in enumerate(path):
        hit = key == target
        fill = ACCENT if hit else CARD
        font = BG if hit else TEXT
        role = "找到" if hit else ("根" if i == 0 else f"第 {i + 1} 次比較")
        lines.append(f'n{i} [label="{key}\\n{role}", fillcolor="{fill}", fontcolor="{font}"];')
        if i > 0:
            side = "左（較小）" if key < path[i - 1] else "右（較大）"
            lines.append(f'n{i - 1} -> n{i} [label=" {side}"];')
    if path and path[-1] != target:
        lines.append(f'miss [label="找不到 {target}\\n走到空指標", shape=box, style="rounded,filled,dashed", '
                     f'fillcolor="#3A1E24", color="{LEVEL_COLOR["紅"]}"];')
        lines.append(f'n{len(path) - 1} -> miss [style=dashed];')
    lines.append("}")
    return "\n".join(lines)


def bst_path_chain(path, target):
    """BST 搜尋路徑（HTML 版，會自動換行）：每個節點是真實鍵值，箭頭標往左或往右。

    路徑長達十幾個節點時，graphviz 直排太高、橫排太小，所以頁面上用這個版本。
    """
    cells = []
    for i, key in enumerate(path):
        hit = key == target
        role = "找到" if hit else ("根" if i == 0 else f"第 {i + 1} 次比較")
        style = f"background:{ACCENT};color:{BG};border-color:{ACCENT}" if hit else ""
        if i > 0:
            go_left = key < path[i - 1]
            cells.append(f'<div class="ns-pathedge">{"← 左" if go_left else "右 →"}<small>'
                         f'{target} {"<" if go_left else ">"} {path[i - 1]}</small></div>')
        cells.append(f'<div class="ns-pathnode" style="{style}"><b>{key}</b><small>{role}</small></div>')
    if path and path[-1] != target:
        last = path[-1]
        cells.append(f'<div class="ns-pathedge">{"← 左" if target < last else "右 →"}<small>'
                     f'{target} {"<" if target < last else ">"} {last}</small></div>')
        cells.append(f'<div class="ns-pathnode miss"><b>空指標</b><small>找不到 {target}</small></div>')
    show('<div class="ns-path">' + "".join(cells) + "</div>")


def heap_dot(records, highlight=()):
    """Heap 前幾層（真實陣列）：索引 i 的子節點是 2i+1、2i+2。highlight 內的編號加主色外框。"""
    lines = ["digraph H {", _DOT_BASE,
             'node [shape=box, style="rounded,filled", fontsize=10];']
    for i, r in enumerate(records):
        color = LEVEL_COLOR[risk_level(r.risk)]
        border = f'color="{ACCENT}", penwidth=3' if r.appointment_id in highlight else f'color="{color}"'
        lines.append(f'h{i} [label="[{i}]  風險 {r.risk:.0f}\\n#{r.appointment_id}", '
                     f'fillcolor="{CARD}", {border}];')
        if i > 0:
            lines.append(f"h{(i - 1) // 2} -> h{i};")
    lines.append("}")
    return "\n".join(lines)


def heap_strip(records, highlight=()):
    """Heap 底層陣列（前 15 格），和樹狀圖是同一份資料。"""
    cells = []
    for i, r in enumerate(records):
        color = LEVEL_COLOR[risk_level(r.risk)]
        cls = ' class="hit"' if r.appointment_id in highlight else ""
        cells.append(f'<div{cls} style="border-bottom:3px solid {color}"><small>[{i}]</small>{r.risk:.0f}</div>')
    show('<div class="ns-strip">' + "".join(cells) + "</div>")


def queue_chain(records):
    """候補隊伍：真實 FIFO 順序，左邊 front 先出隊、右邊 rear 新的人排這裡。"""
    if not records:
        show('<div class="ns-note">候補隊伍已經空了（front = rear = None）。</div>')
        return
    nodes = []
    for i, r in enumerate(records):
        color = LEVEL_COLOR[risk_level(r.risk)]
        cls = "ns-qnode front" if i == 0 else "ns-qnode"
        nodes.append(f'<div class="{cls}" style="--accent:{color}"><small>候補 {i + 1}'
                     f'{"（下一位）" if i == 0 else ""}</small><b>病患 {r.patient_id}</b>'
                     f'<small>掛號 {r.appointment_id}・風險 {r.risk:.0f}</small></div>')
    chain = '<div class="ns-qarrow">→</div>'.join(nodes)
    show(f'<div class="ns-queue"><div class="ns-qend">front<br>先出隊 ↑</div>{chain}'
         f'<div class="ns-qend">rear<br>新的排這裡</div></div>')


def steps(items):
    """流程步驟條：items = [(步驟名稱, 小字)]。"""
    cells = [f'<div class="ns-step">{md_inline(t)}<small>{md_inline(s)}</small></div>' for t, s in items]
    show('<div class="ns-steps">' + '<div class="ns-steparrow">→</div>'.join(cells) + "</div>")
