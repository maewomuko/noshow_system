"""效能分析：讀 experiments/results_exp1~3.csv 畫圖（不使用 session_state 的系統）。

所有數字都直接來自 CSV；倍數由 CSV 的值相除得到。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import altair as alt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from common import ACCENT, LEVEL_COLOR, MUTED, ROOT, md_inline, section, setup_page, show, tech_panel  # noqa: E402

setup_page("效能分析", "📈")
st.title("效能分析")
show('<div class="ns-lead">同一份真實資料抽 1,000／10,000／50,000／全部 106,982 筆，'
     '比較「好方法」與「對照組」的<b>比較次數、搬移次數、耗時</b>。</div>')

EXP_DIR = ROOT / "experiments"
FILES = {1: "results_exp1.csv", 2: "results_exp2.csv", 3: "results_exp3.csv"}
data = {i: pd.read_csv(EXP_DIR / f) for i, f in FILES.items() if (EXP_DIR / f).exists()}

if len(data) < 3:
    st.warning("還沒有完整的實驗結果。請在 noshow_system 資料夾執行："
               "`python -m experiments.run_all`（約需數分鐘），再重新整理這一頁。")
    if not data:
        st.stop()

LABEL = {
    "linear": "線性搜尋（陣列）", "binary": "二分搜尋（排序陣列）", "bst": "BST",
    "bst_degenerate": "退化 BST（依序插入）", "sorted_array": "排序陣列插入",
    "heap_top_k": "Heap top_k", "sorted": "sorted() 全排序", "rebuild_pop": "重建 heap 再 pop",
    "array": "陣列刪除（搬移）", "bst_linked_list": "BST + Linked List",
    "array_queue": "ArrayQueue（pop(0)）", "linked_queue": "LinkedQueue",
}
GOOD = {"bst", "binary", "heap_top_k", "bst_linked_list", "linked_queue"}
COLOR = {"bst": ACCENT, "heap_top_k": ACCENT, "bst_linked_list": ACCENT, "linked_queue": ACCENT,
         "binary": "#9C8CF0", "linear": MUTED, "sorted": MUTED, "array": MUTED, "array_queue": MUTED,
         "sorted_array": LEVEL_COLOR["黃"], "rebuild_pop": LEVEL_COLOR["黃"],
         "bst_degenerate": LEVEL_COLOR["紅"]}

c1, c2 = st.columns([3, 2])
metric_name = c1.radio("縱軸", ["平均比較次數", "平均搬移次數", "平均耗時 (ms)"], horizontal=True)
column = {"平均耗時 (ms)": "avg_ms", "平均比較次數": "avg_comparisons", "平均搬移次數": "avg_moves"}[metric_name]
log_scale = c2.checkbox("縱軸取對數（差距太大時才看得出來）", value=True)


def line_chart(df, title, hint=None):
    """x = 資料量 n（對數軸），每個方法一條線；數值為 0 時對數軸畫不出來，另外註明。

    hint：這個實驗主要該看哪個縱軸（例如插入看搬移次數）。
    """
    d = df.copy()
    d["方法"] = d["method"].map(LABEL)
    d["值"] = d[column]
    if (d["值"] <= 0).all():
        st.markdown(f"**{title}**")
        st.info(f"這個實驗的所有方法{metric_name}都是 0（例如佇列出隊不做比較）。"
                + (f"請把縱軸切到「{hint}」。" if hint else "請切換縱軸。"))
        return
    zero = sorted(d.loc[d["值"] <= 0, "方法"].unique())
    if log_scale:
        d = d[d["值"] > 0]
    methods = [m for m in df["method"].unique()]
    scale = alt.Scale(domain=[LABEL[m] for m in methods], range=[COLOR[m] for m in methods])
    chart = alt.Chart(d).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=2.5).encode(
        x=alt.X("n:Q", scale=alt.Scale(type="log", domain=[800, 135000], nice=False),
                title="資料量 n（對數軸）",
                axis=alt.Axis(values=[1000, 10000, 50000, 106982], format=",")),
        y=alt.Y("值:Q", title=metric_name, scale=alt.Scale(type="log" if log_scale else "linear")),
        color=alt.Color("方法:N", scale=scale, legend=alt.Legend(
            orient="bottom", title=None, columns=2, labelLimit=320, labelFontSize=12)),
        tooltip=["方法", alt.Tooltip("n:Q", format=","), alt.Tooltip("runs:Q", title="實際重複次數"),
                 alt.Tooltip("值:Q", format=",.4g", title=metric_name)],
    ).properties(title=title, height=320)
    st.altair_chart(chart, width="stretch")
    notes = []
    if zero:
        notes.append(f"{'、'.join(zero)} 的{metric_name}為 0，對數軸上不畫出。")
    if hint and hint != metric_name:
        notes.append(f"這個實驗的關鍵差別在「{hint}」。")
    if notes:
        st.caption(" ".join(notes))


def ratio_rows(df, pairs):
    """全部資料（最大 n）時，對照組 ÷ 好方法 的倍數。pairs = [(說明, 好方法, 對照組)]。"""
    full = df[df.n == df.n.max()].set_index("method")
    rows = []
    for label, good, base in pairs:
        if good in full.index and base in full.index:
            g, b = full.loc[good], full.loc[base]
            rows.append({
                "比較": label,
                "好方法 耗時 ms": g.avg_ms, "對照組 耗時 ms": b.avg_ms,
                "耗時倍數": b.avg_ms / g.avg_ms if g.avg_ms else None,
                "好方法 比較": g.avg_comparisons, "對照組 比較": b.avg_comparisons,
                "好方法 搬移": g.avg_moves, "對照組 搬移": b.avg_moves,
                "對照組 runs": int(b.runs),
            })
    return pd.DataFrame(rows)


def show_ratio(df, pairs):
    table = ratio_rows(df, pairs)
    if table.empty:
        return
    st.dataframe(table, hide_index=True, width="stretch", column_config={
        "耗時倍數": st.column_config.NumberColumn(format="%.0f 倍"),
        "好方法 耗時 ms": st.column_config.NumberColumn(format="%.4f"),
        "對照組 耗時 ms": st.column_config.NumberColumn(format="%.4f"),
        "好方法 比較": st.column_config.NumberColumn(format="localized"),
        "對照組 比較": st.column_config.NumberColumn(format="localized"),
        "好方法 搬移": st.column_config.NumberColumn(format="localized"),
        "對照組 搬移": st.column_config.NumberColumn(format="localized"),
    })


def raw_table(df):
    """原始數字；runs < 1000 代表該組超過 3 秒提早停止。"""
    with st.expander("看原始數字（含實際重複次數 runs）"):
        d = df.copy()
        d["方法"] = d["method"].map(LABEL)
        d["提早停止"] = d["runs"].map(lambda x: "是（3 秒上限）" if x < 1000 else "")
        st.dataframe(d[["方法", "n", "k", "runs", "提早停止", "avg_ms", "avg_comparisons", "avg_moves"]],
                     hide_index=True, width="stretch")


def theory_vs_measured(theory, measured):
    """理論與實測分兩欄，避免混在一起。"""
    a, b = st.columns(2)
    with a:
        show('<div class="ns-section">理論時間複雜度</div>')
        show("<ul>" + "".join(f"<li>{md_inline(t)}</li>" for t in theory) + "</ul>")
    with b:
        show('<div class="ns-section">實測觀察（CSV）</div>')
        show("<ul>" + "".join(f"<li>{md_inline(t)}</li>" for t in measured) + "</ul>")


tab1, tab2, tab3 = st.tabs(["實驗一：搜尋＋插入", "實驗二：Top-K", "實驗三：刪除＋Queue"])

with tab1:
    if 1 in data:
        df = data[1]
        c1, c2 = st.columns(2)
        with c1:
            line_chart(df[df.experiment == "search"], "搜尋一筆")
        with c2:
            line_chart(df[df.experiment == "insert"], "插入一筆", hint="平均搬移次數")
        section("全部 106,982 筆時")
        show_ratio(df[df.experiment == "search"], [("搜尋：BST vs 線性", "bst", "linear"),
                                                    ("搜尋：二分 vs 線性", "binary", "linear")])
        show_ratio(df[df.experiment == "insert"], [("插入：BST vs 排序陣列", "bst", "sorted_array")])
        theory_vs_measured(
            ["線性搜尋 O(n)；二分搜尋、BST O(log n)", "排序陣列插入：二分找位置 O(log n)＋搬移 O(n)",
             "BST 插入 O(log n)，不搬移", "退化 BST（依序插入）樹高 = n，搜尋 O(n)"],
            ["線性搜尋的比較次數隨 n 直線上升，BST、二分幾乎是平的",
             "二分搜尋查得跟 BST 一樣快，但**排序陣列插入要大量搬移**，BST 不用 → 常新增、取消的系統選 BST",
             "退化 BST 只測到 1 萬筆（建樹是 O(n²)）；比較次數接近線性搜尋 → 載入前一定要先打亂"])
        raw_table(df)

with tab2:
    if 2 in data:
        df = data[2]
        ks = sorted(int(x) for x in df.k.dropna().unique())
        k = st.select_slider("K", options=ks, value=ks[0])
        line_chart(df[df.k == k], f"取前 {k} 名")
        section("全部 106,982 筆時")
        show_ratio(df[df.k == k], [("Top-K：heap vs sorted()", "heap_top_k", "sorted"),
                                   ("Top-K：heap vs 重建 heap", "heap_top_k", "rebuild_pop")])

        # 不符合直覺的結果：直接從 CSV 找出 sorted() 比 heap 快的組合
        piv = df.pivot_table(index=["n", "k"], columns="method", values=["avg_ms", "avg_comparisons"])
        faster = []
        for (n_, k_), row in piv.iterrows():
            h_ms, s_ms = row[("avg_ms", "heap_top_k")], row[("avg_ms", "sorted")]
            if s_ms < h_ms:
                h_c, s_c = row[("avg_comparisons", "heap_top_k")], row[("avg_comparisons", "sorted")]
                cmp_note = "比較次數也是 sorted() 較少" if s_c < h_c else "但比較次數仍是 heap 較少"
                faster.append(f"<li>n = {int(n_):,}、K = {int(k_):,}：sorted() {s_ms:.3f} ms ＜ heap {h_ms:.3f} ms"
                              f"（比較 {s_c:,.0f} vs {h_c:,.0f}，{cmp_note}）</li>")
        if faster:
            show('<div class="ns-callout"><b>不符合預期的結果（照實呈現）</b><ul style="margin:.3rem 0 .2rem">'
                 + "".join(faster) + "</ul>K 接近 n 時，<code>top_k</code> 幾乎要展開整棵 heap，"
                 "而 <code>sorted()</code> 是 C 實作、常數很小。Top-K 適合 K 遠小於 n 的情況；"
                 "護理站只看前 10 名，正好符合。</div>")
        theory_vs_measured(
            ["Heap `top_k`：O(K log K)，與 n 幾乎無關", "`sorted()` 全排序：O(n log n)",
             "每次重建 heap 再 pop K 次：O(n + K log n)"],
            ["K = 10 時，heap 的比較次數在各種 n 都維持在 50 多次",
             "`sorted()` 的比較次數隨 n 成長（n log n）",
             "小資料、大 K 時 `sorted()` 可能較快（見上方黃框）"])
        raw_table(df)

with tab3:
    if 3 in data:
        df = data[3]
        c1, c2 = st.columns(2)
        with c1:
            line_chart(df[df.experiment == "delete"], "刪除一筆預約", hint="平均搬移次數")
        with c2:
            line_chart(df[df.experiment == "queue"], "Queue dequeue 一次", hint="平均搬移次數")
        section("全部 106,982 筆時")
        show_ratio(df[df.experiment == "delete"], [("刪除：BST+Linked List vs 陣列", "bst_linked_list", "array")])
        show_ratio(df[df.experiment == "queue"], [("出隊：LinkedQueue vs ArrayQueue", "linked_queue", "array_queue")])
        theory_vs_measured(
            ["陣列刪除：找位置 O(n)＋搬移 O(n)", "BST 找節點 O(log n)＋Linked List 拆鏈 O(1)",
             "ArrayQueue `pop(0)`：O(n)；LinkedQueue：O(1)"],
            ["陣列刪除平均搬移約一半的元素；鏈結結構只改指標，搬移 0 次",
             "`pop(0)` 的搬移由 C 語言的記憶體複製完成，所以耗時差距比搬移次數小很多",
             "搬移次數不受電腦快慢影響，最能看出 O(n) 與 O(1) 的差別"])
        raw_table(df)

tech_panel(
    ["資料：從原始 106,982 筆**真實資料**隨機抽樣（固定 seed），沒有任何生成或放大的資料。",
     "每組最多重複 1,000 次取平均；很慢的方法超過 3 秒就提早停止（至少 5 次），實際次數記在 `runs`。",
     "計時只算操作本身（`time.perf_counter()`），不算建立結構。",
     "實驗用自己建立的新結構，不使用網頁上正在操作的系統；只讀原始 CSV。"],
    measured=[("可重現", "比較次數、搬移次數"), ("每次略有不同", "耗時 ms"), ("硬體環境", "CSV 未記錄")],
    theory=[("看演算法本身", "比較／搬移次數"), ("看實際體感", "耗時 ms")],
    title="實驗方法與測量條件",
)
