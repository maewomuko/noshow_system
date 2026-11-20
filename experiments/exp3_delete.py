"""實驗三：刪除＋Queue（Linked List／Queue 負責人）。

刪除比較（每次刪一筆不同的預約）：
  array            陣列：線性找到位置 → 後面元素往前搬          O(n)
  bst_linked_list  BST 找節點 → 取出 ll_node → delete_node      O(log n) + O(1)

Queue 比較（先放 n 筆，再連續 dequeue）：
  array_queue      ArrayQueue，dequeue 用 list.pop(0)，後面全部往前搬   每次 O(n)
  linked_queue     LinkedQueue，只移動 head 指標                        每次 O(1)

搬移次數：陣列 = 實際搬移的元素數；鏈結結構只改指標，記為 0。
注意：list.pop(0) 的搬移是 C 語言做的，耗時差距會比比較次數小。

執行：python -m experiments.exp3_delete
"""

import random
import time

from experiments.common import SIZES, MAX_RUNS, measure, make_row, run_and_save, sample
from core.array_store import ArrayStore
from core.bst import BST
from core.linked_list import DoublyLinkedList
from core.queue_ll import ArrayQueue, LinkedQueue


def run(records, sizes=SIZES, max_runs=MAX_RUNS, seed=0, **kw):
    rows = []
    for size in sizes:
        data = sample(records, size, seed)
        n = len(data)
        rng = random.Random(seed + 2)
        targets = rng.sample([r.appointment_id for r in data], min(max_runs, n // 2))

        # ---- 陣列刪除 ----
        arr = ArrayStore(data)

        def array_delete(target):
            length = len(arr)
            ok, shifts, ms = arr.delete(target)
            assert ok
            # 找到位置前比較了 index + 1 次；index = length - 1 - shifts
            return ms, length - shifts, shifts

        # ---- BST + Doubly Linked List 刪除 ----
        dll, bst = DoublyLinkedList(), BST()
        for r in data:
            bst.insert(r, dll.append(r))

        def linked_delete(target):
            t = time.perf_counter()
            node, comparisons, _ = bst.search(target)
            dll.delete_node(node.ll_node)
            ms = (time.perf_counter() - t) * 1000
            return ms, comparisons, 0

        rows.append(make_row("delete", "array", n, measure(array_delete, targets, max_runs, **kw)))
        rows.append(make_row("delete", "bst_linked_list", n,
                             measure(linked_delete, targets, max_runs, **kw)))

        # ---- Queue：連續 dequeue ----
        aq, lq = ArrayQueue(), LinkedQueue()
        for r in data:
            aq.enqueue(r)
            lq.enqueue(r)
        steps = range(min(max_runs, n))

        def array_dequeue(_):
            moves = len(aq) - 1
            t = time.perf_counter()
            aq.dequeue()
            return (time.perf_counter() - t) * 1000, 0, moves

        def linked_dequeue(_):
            t = time.perf_counter()
            lq.dequeue()
            return (time.perf_counter() - t) * 1000, 0, 0

        rows.append(make_row("queue", "array_queue", n, measure(array_dequeue, steps, max_runs, **kw)))
        rows.append(make_row("queue", "linked_queue", n, measure(linked_dequeue, steps, max_runs, **kw)))
    return rows


def main():
    run_and_save(run, "results_exp3.csv", "實驗三：刪除＋Queue")


if __name__ == "__main__":
    main()
