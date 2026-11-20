"""實驗二：Top-K（Heap 負責人）。

比較（K = 10、100、1000）：
  heap_top_k       已建好的 Max-Heap 呼叫 top_k(K)        O(K log K)
  sorted           sorted() 全部排序再取前 K               O(n log n)
  rebuild_pop      每次重新 build_heap，再 pop K 次        O(n + K log n)

排序依據與 Max-Heap 相同：風險高者優先，同分時掛號編號小者優先。
sorted() 是 C 實作，資料量小時可能反而較快，所以另外記錄「比較次數」說明演算法本身的差異。
比較次數另外跑一次計數版（計數會拖慢速度，不跟計時混在一起）。

執行：python -m experiments.exp2_topk
"""

import time
from contextlib import contextmanager
from functools import cmp_to_key

from experiments.common import SIZES, MAX_RUNS, measure, make_row, run_and_save, sample
from core.max_heap import MaxHeap

K_VALUES = [10, 100, 1000]


def _priority(r):
    return (-r.risk, r.appointment_id)


@contextmanager
def count_heap_comparisons():
    """暫時把 MaxHeap._higher 換成會計數的版本（只在實驗裡用，離開時還原）。"""
    original = MaxHeap.__dict__["_higher"]
    counter = [0]

    def counting(a, b):
        counter[0] += 1
        return original.__func__(a, b)

    MaxHeap._higher = staticmethod(counting)
    try:
        yield counter
    finally:
        MaxHeap._higher = original


def count_sorted_comparisons(data, k):
    counter = [0]

    def cmp(a, b):
        counter[0] += 1
        pa, pb = _priority(a), _priority(b)
        return -1 if pa < pb else (1 if pa > pb else 0)

    sorted(data, key=cmp_to_key(cmp))[:k]
    return counter[0]


def heap_top_k(heap, k):
    return heap.top_k(k)


def sorted_top_k(data, k):
    return sorted(data, key=_priority)[:k]


def rebuild_pop(data, k):
    h = MaxHeap()
    h.build_heap(data)
    return [h.pop() for _ in range(min(k, len(h)))]


def run(records, sizes=SIZES, max_runs=MAX_RUNS, seed=0, k_values=K_VALUES, **kw):
    rows = []
    for size in sizes:
        data = sample(records, size, seed)
        n = len(data)
        heap = MaxHeap.from_records(data)

        for k in k_values:
            if k > n:
                continue
            methods = {
                "heap_top_k": lambda: heap_top_k(heap, k),
                "sorted": lambda: sorted_top_k(data, k),
                "rebuild_pop": lambda: rebuild_pop(data, k),
            }

            # 比較次數：各跑一次計數版（結果是確定的，不用重複）
            with count_heap_comparisons() as c:
                heap_top_k(heap, k)
            cmp_heap = c[0]
            cmp_sorted = count_sorted_comparisons(data, k)
            with count_heap_comparisons() as c:
                rebuild_pop(data, k)
            cmp_rebuild = c[0]
            comparisons = {"heap_top_k": cmp_heap, "sorted": cmp_sorted, "rebuild_pop": cmp_rebuild}

            # 驗證三種方法結果一致
            expect = [r.appointment_id for r in sorted_top_k(data, k)]
            assert [r.appointment_id for r in heap_top_k(heap, k)] == expect
            assert [r.appointment_id for r in rebuild_pop(data, k)] == expect

            for name, fn in methods.items():
                def op(_, fn=fn, name=name):
                    t = time.perf_counter()
                    fn()
                    return (time.perf_counter() - t) * 1000, comparisons[name], 0
                rows.append(make_row("topk", name, n,
                                     measure(op, range(max_runs), max_runs, **kw), k=k))
    return rows


def main():
    run_and_save(run, "results_exp2.csv", "實驗二：Top-K")


if __name__ == "__main__":
    main()
