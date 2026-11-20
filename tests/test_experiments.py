"""任務 6：實驗程式的測試（用小資料量，確認能跑、欄位正確、結果合理）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.record import load_records
from experiments import exp1_search, exp2_topk, exp3_delete
from experiments.common import FIELDS
from core.max_heap import MaxHeap

SMALL = dict(sizes=[500, 2000], max_runs=50, budget_s=5.0)


@pytest.fixture(scope="module")
def records():
    return load_records()


def by_method(rows, experiment, n, k=""):
    return {r["method"]: r for r in rows if r["experiment"] == experiment
            and r["n"] == n and r["k"] == k}


def test_exp1(records):
    rows = exp1_search.run(records, **SMALL)
    assert all(set(r) == set(FIELDS) for r in rows)
    s = by_method(rows, "search", 2000)
    assert set(s) == {"linear", "binary", "bst", "bst_degenerate"}
    assert s["bst"]["avg_comparisons"] < s["linear"]["avg_comparisons"]
    assert s["binary"]["avg_comparisons"] <= 12            # log2(2000) ≈ 11
    assert s["bst_degenerate"]["avg_comparisons"] > 10 * s["bst"]["avg_comparisons"]
    ins = by_method(rows, "insert", 2000)
    assert ins["sorted_array"]["avg_moves"] > 100 and ins["bst"]["avg_moves"] == 0


def test_sorted_array_insert():
    from core.record import Record
    def rec(i):
        return Record(i, i, 30, "F", 0, "d", "d", "x", False, False, True)
    arr = [rec(i) for i in (1, 3, 5, 7)]
    _, moves = exp1_search.sorted_array_insert(arr, rec(4))
    assert [r.appointment_id for r in arr] == [1, 3, 4, 5, 7] and moves == 2


def test_exp2(records):
    rows = exp2_topk.run(records, sizes=[2000], max_runs=20, budget_s=5.0, k_values=[10, 100])
    m = by_method(rows, "topk", 2000, k=10)
    assert set(m) == {"heap_top_k", "sorted", "rebuild_pop"}
    assert m["heap_top_k"]["avg_comparisons"] < m["sorted"]["avg_comparisons"]
    assert m["heap_top_k"]["avg_comparisons"] < m["rebuild_pop"]["avg_comparisons"]


def test_exp2_counter_restores_heap():
    original = MaxHeap.__dict__["_higher"]
    with exp2_topk.count_heap_comparisons():
        pass
    assert MaxHeap.__dict__["_higher"] is original


def test_exp3(records):
    rows = exp3_delete.run(records, **SMALL)
    d = by_method(rows, "delete", 2000)
    assert d["array"]["avg_moves"] > 0 and d["bst_linked_list"]["avg_moves"] == 0
    assert d["bst_linked_list"]["avg_comparisons"] < d["array"]["avg_comparisons"]
    q = by_method(rows, "queue", 2000)
    assert q["array_queue"]["avg_moves"] > 1000 and q["linked_queue"]["avg_moves"] == 0
