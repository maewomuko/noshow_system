"""實驗共用工具：抽樣、計時、寫 CSV。

規則（CLAUDE.md）：
  - 只讀 data/healthcare_noshows.csv，不修改
  - 每個實驗都建立新的結構實例，不使用 Streamlit 裡的系統
  - 計時只算操作本身，不算建立結構；用 time.perf_counter()
  - 固定 random seed，結果可重現

CSV 欄位（三個實驗統一，任務 8 直接讀取）：
  experiment       實驗名稱：search / insert / topk / delete / queue
  method           比較對象
  n                資料量
  k                Top-K 的 K（其他實驗留空）
  runs             實際重複次數
  avg_ms           平均耗時（毫秒）
  avg_comparisons  平均比較次數
  avg_moves        平均搬移次數（陣列搬移元素；鏈結結構只改指標 = 0）
"""

import csv
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.record import load_records  # noqa: E402

EXP_DIR = Path(__file__).resolve().parent
SIZES = [1_000, 10_000, 50_000, None]      # None = 全部
MAX_RUNS = 1000                             # 每組最多重複 1000 次
TIME_BUDGET_S = 3.0                         # 每組最多花 3 秒；很慢的方法會提早停（runs 會記錄實際次數）
MIN_RUNS = 5                                # 至少跑 5 次
FIELDS = ["experiment", "method", "n", "k", "runs", "avg_ms", "avg_comparisons", "avg_moves"]


def sample(records, n, seed=0):
    """抽 n 筆並打亂順序（避免 BST 退化）。n 為 None 或超過總數時取全部。"""
    rng = random.Random(seed)
    if n is None or n >= len(records):
        data = records[:]
        rng.shuffle(data)
        return data
    return rng.sample(records, n)


def measure(op, items, max_runs=MAX_RUNS, budget_s=TIME_BUDGET_S, min_runs=MIN_RUNS):
    """對 items 逐一執行 op(item)，op 回傳 (ms, comparisons, moves)。

    跑滿 max_runs 次，或超過時間預算（且至少 min_runs 次）就停。
    回傳 (runs, avg_ms, avg_comparisons, avg_moves)。
    """
    total_ms = total_cmp = total_mv = 0.0
    runs = 0
    start = time.perf_counter()
    for item in items:
        ms, cmp_, mv = op(item)
        total_ms += ms
        total_cmp += cmp_
        total_mv += mv
        runs += 1
        if runs >= max_runs:
            break
        if runs >= min_runs and time.perf_counter() - start > budget_s:
            break
    if runs == 0:
        return 0, 0.0, 0.0, 0.0
    return runs, total_ms / runs, total_cmp / runs, total_mv / runs


def make_row(experiment, method, n, result, k=""):
    runs, avg_ms, avg_cmp, avg_mv = result
    return {
        "experiment": experiment,
        "method": method,
        "n": n,
        "k": k,
        "runs": runs,
        "avg_ms": round(avg_ms, 6),
        "avg_comparisons": round(avg_cmp, 2),
        "avg_moves": round(avg_mv, 2),
    }


def write_csv(rows, filename):
    path = EXP_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def print_rows(rows):
    for r in rows:
        k = f" K={r['k']}" if r["k"] != "" else ""
        print(f"  {r['experiment']:<7}{r['method']:<22}n={r['n']:<7}{k:<7}"
              f"runs={r['runs']:<5} {r['avg_ms']:>10.4f} ms  比較 {r['avg_comparisons']:>10.1f}"
              f"  搬移 {r['avg_moves']:>10.1f}")


def run_and_save(run_fn, filename, title):
    """載入資料 → 執行實驗 → 存 CSV → 印出結果（給各實驗的 main 用）。"""
    print(f"== {title} ==")
    records = load_records()
    rows = run_fn(records)
    path = write_csv(rows, filename)
    print_rows(rows)
    print(f"  → 已存到 {path}")
    return rows
