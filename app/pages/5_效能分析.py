"""效能分析：讀 experiments/results_exp1~3.csv 畫折線圖（不使用 session_state 的系統）。"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import ROOT, structure_box  # noqa: E402

st.set_page_config(page_title="效能分析", page_icon="📈", layout="wide")
st.title("📈 效能分析")

EXP_DIR = ROOT / "experiments"
FILES = {1: "results_exp1.csv", 2: "results_exp2.csv", 3: "results_exp3.csv"}
data = {i: pd.read_csv(EXP_DIR / f) for i, f in FILES.items() if (EXP_DIR / f).exists()}

if len(data) < 3:
    st.warning("還沒有完整的實驗結果。請在 noshow_system 資料夾執行："
               "`python -m experiments.run_all`（約需數分鐘），再重新整理這一頁。")
    if not data:
        st.stop()

metric_name = st.radio("縱軸", ["平均耗時 (ms)", "平均比較次數", "平均搬移次數"], horizontal=True)
column = {"平均耗時 (ms)": "avg_ms", "平均比較次數": "avg_comparisons",
          "平均搬移次數": "avg_moves"}[metric_name]
log_scale = st.checkbox("縱軸取對數（差距太大時比較看得出來）", value=False)


def line_chart(df, title):
    """x = 資料量 n，每個方法一條線。"""
    table = df.pivot_table(index="n", columns="method", values=column)
    if log_scale:
        table = table.where(table > 0).apply(lambda s: s.map(math.log10))   # 0 不能取 log，留空
    st.markdown(f"**{title}**" + ("（log₁₀）" if log_scale else ""))
    st.line_chart(table)
    with st.expander("看數字"):
        st.dataframe(df, hide_index=True, width="stretch")


tab1, tab2, tab3 = st.tabs(["實驗一：搜尋＋插入", "實驗二：Top-K", "實驗三：刪除＋Queue"])

with tab1:
    if 1 in data:
        df = data[1]
        c1, c2 = st.columns(2)
        with c1:
            line_chart(df[df.experiment == "search"], "搜尋")
        with c2:
            line_chart(df[df.experiment == "insert"], "插入")
        st.markdown(
            "- **線性搜尋**隨資料量直線上升（O(n)）；**二分搜尋**和 **BST** 幾乎是平的（O(log n)）。\n"
            "- 二分搜尋查得跟 BST 一樣快，但**排序陣列插入要搬移**一半的元素，BST 插入不用 → "
            "經常新增、取消的系統選 BST。\n"
            "- **退化 BST**（依編號排序後插入）變成一條鏈，跟線性搜尋一樣慢 → 載入前一定要先打亂。")

with tab2:
    if 2 in data:
        df = data[2]
        ks = sorted(df.k.dropna().unique())
        k = st.select_slider("K", options=[int(x) for x in ks], value=int(ks[0]))
        line_chart(df[df.k == k], f"取前 {k} 名")
        st.markdown(
            "- **Heap `top_k`** 只看根附近的節點，O(K log K)，幾乎不受資料量影響。\n"
            "- **`sorted()`** 每次把全部人排序，O(n log n)；**重建 heap 再 pop** 是 O(n + K log n)。\n"
            "- `sorted()` 是 C 語言寫的，資料量小、K 很大時耗時可能反而比較短；"
            "但看**比較次數**就能看出演算法本身的差距。護理站只需要前 10 名，沒必要排序全部。")

with tab3:
    if 3 in data:
        df = data[3]
        c1, c2 = st.columns(2)
        with c1:
            line_chart(df[df.experiment == "delete"], "刪除一筆預約")
        with c2:
            line_chart(df[df.experiment == "queue"], "Queue dequeue 一次")
        st.markdown(
            "- **陣列刪除**要先找到位置、再把後面的元素往前搬，O(n)。\n"
            "- **BST 找節點 → Linked List 刪節點**：O(log n) + O(1)，只改指標、不用搬移。\n"
            "- **ArrayQueue** 用 `pop(0)`，每次後面全部往前搬；**LinkedQueue** 只移動 head，O(1)。"
            "（`pop(0)` 的搬移由 C 語言完成，所以耗時差距比搬移次數小。）")

structure_box([
    "每組資料量（1,000／10,000／50,000／全部）重複操作最多 1,000 次取平均；"
    "很慢的方法在 3 秒內提早停止，實際次數記在 `runs` 欄。",
    "計時只算操作本身（`time.perf_counter()`），不算建立結構；固定 random seed，結果可重現。",
    "實驗用自己建立的新結構，不使用網頁上正在操作的系統；只讀原始 CSV。",
])
