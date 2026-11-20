"""實驗一：搜尋＋插入（BST 負責人）。

搜尋比較：
  linear           陣列線性搜尋              O(n)
  binary           排序陣列二分搜尋          O(log n)（排序成本不計）
  bst              BST（打亂後插入）         O(log n)
  bst_degenerate   BST（依編號排序後插入）   O(n)，樹退化成一條鏈；只跑到 1 萬筆
插入比較：
  sorted_array     排序陣列：二分找位置 + 把後面元素往後搬   O(n)
  bst              BST 插入                                  O(log n)

搜尋目標：90% 存在的編號、10% 不存在的編號（隨機抽，固定 seed）。

執行：python -m experiments.exp1_search
"""

import random
import time
from dataclasses import replace

from experiments.common import SIZES, MAX_RUNS, measure, make_row, run_and_save, sample
from core.array_store import ArrayStore
from core.bst import BST

DEGENERATE_MAX = 10_000      # 退化 BST 建樹是 O(n²)，資料量上限 1 萬


def _missing_ids(existing, count, rng):
    """產生 count 個「不存在」的編號（在既有編號範圍內，路徑才不會偏一邊）。"""
    lo, hi = min(existing), max(existing)
    out = set()
    while len(out) < count:
        x = rng.randint(lo, hi)
        if x not in existing:
            out.add(x)
    return list(out)


def make_targets(ids, runs, rng):
    existing = set(ids)
    n_missing = runs // 10
    targets = [rng.choice(ids) for _ in range(runs - n_missing)]
    targets += _missing_ids(existing, n_missing, rng)
    rng.shuffle(targets)
    return targets


def sorted_array_insert(arr, record):
    """在依編號排序的 list 中插入一筆：二分找位置 → 手動往後搬。

    刻意不用 bisect / list.insert，才看得到比較與搬移成本。
    回傳 (比較次數, 搬移次數)。
    """
    key = record.appointment_id
    low, high = 0, len(arr)
    comparisons = 0
    while low < high:
        mid = (low + high) // 2
        comparisons += 1
        if arr[mid].appointment_id < key:
            low = mid + 1
        else:
            high = mid
    arr.append(None)                       # 尾端多一格
    moves = 0
    for i in range(len(arr) - 1, low, -1):
        arr[i] = arr[i - 1]
        moves += 1
    arr[low] = record
    return comparisons, moves


def _search_op(search_fn):
    def op(target):
        _, comparisons, ms = search_fn(target)
        return ms, comparisons, 0
    return op


def run(records, sizes=SIZES, max_runs=MAX_RUNS, seed=0, degenerate_max=DEGENERATE_MAX, **kw):
    rows = []
    for size in sizes:
        data = sample(records, size, seed)
        n = len(data)
        ids = [r.appointment_id for r in data]
        rng = random.Random(seed + 1)
        targets = make_targets(ids, max_runs, rng)

        # ---- 搜尋 ----
        arr = ArrayStore(data)
        arr.sorted_copy()                  # 先排好，排序成本不算在搜尋裡
        bst = BST.from_records(data)       # data 已打亂
        rows.append(make_row("search", "linear", n,
                             measure(_search_op(arr.linear_search), targets, max_runs, **kw)))
        rows.append(make_row("search", "binary", n,
                             measure(_search_op(arr.binary_search), targets, max_runs, **kw)))
        rows.append(make_row("search", "bst", n,
                             measure(_search_op(bst.search), targets, max_runs, **kw)))
        if n <= degenerate_max:
            degenerate = BST.from_records(sorted(data, key=lambda r: r.appointment_id))
            rows.append(make_row("search", "bst_degenerate", n,
                                 measure(_search_op(degenerate.search), targets, max_runs, **kw)))

        # ---- 插入：產生不存在的新編號，複製一筆 Record 改編號 ----
        new_ids = _missing_ids(set(ids), max_runs, rng)
        new_records = [replace(rng.choice(data), appointment_id=x) for x in new_ids]

        sorted_arr = sorted(data, key=lambda r: r.appointment_id)

        def array_insert(rec):
            t = time.perf_counter()
            comparisons, moves = sorted_array_insert(sorted_arr, rec)
            return (time.perf_counter() - t) * 1000, comparisons, moves

        tree = BST.from_records(data)

        def bst_insert(rec):
            t = time.perf_counter()
            tree.insert(rec)
            ms = (time.perf_counter() - t) * 1000
            # 插入時比較的次數 = 新節點的祖先數（計時之後才算，不影響耗時）
            return ms, len(tree.search_path(rec.appointment_id)) - 1, 0

        rows.append(make_row("insert", "sorted_array", n,
                             measure(array_insert, new_records, max_runs, **kw)))
        rows.append(make_row("insert", "bst", n,
                             measure(bst_insert, new_records, max_runs, **kw)))
    return rows


def main():
    run_and_save(run, "results_exp1.csv", "實驗一：搜尋＋插入")


if __name__ == "__main__":
    main()
