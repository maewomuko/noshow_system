"""任務 0~5 的快速示範：用完整 CSV 建立所有結構，印出關鍵數字。

執行：python demo_core.py
"""

import random
import time

from core.record import load_records, risk_level, validate_risk, build_calibration, expected_noshow
from core.array_store import ArrayStore
from core.bst import BST
from core.linked_list import DoublyLinkedList
from core.max_heap import MaxHeap
from core.queue_ll import pick_waitlist

DAY = "2016-06-06"        # 示範用的「當日門診」
WAIT_DAY = "2016-06-07"   # 從這天抽候補病患


def timed(label, fn):
    t = time.perf_counter()
    out = fn()
    print(f"  {label:<28}{(time.perf_counter() - t) * 1000:9.1f} ms")
    return out


def main():
    print("== 任務 0：讀檔與風險計分 ==")
    records = timed("load_records", load_records)
    print(f"  共 {len(records)} 筆")
    for level, (n, rate) in validate_risk(records).items():
        print(f"  {level}燈 {n:6d} 人，實際未到率 {rate:.1%}")

    print("\n== 建立結構（全部資料） ==")
    shuffled = records[:]
    random.Random(42).shuffle(shuffled)          # 打亂，避免 BST 退化
    arr = timed("ArrayStore", lambda: ArrayStore(records))
    dll = DoublyLinkedList()
    bst = BST()

    def build_dll_bst():
        for r in shuffled:
            bst.insert(r, dll.append(r))
    timed("DoublyLinkedList + BST", build_dll_bst)
    heap = timed("MaxHeap.build_heap", lambda: MaxHeap.from_records(records))
    print(f"  BST 樹高 {bst.height()}（完全平衡約 17）")

    print("\n== 搜尋比較（實驗一預覽） ==")
    target = records[len(records) // 2].appointment_id
    _, c1, t1 = arr.linear_search(target)
    _, c2, t2 = arr.binary_search(target)
    _, c3, t3 = bst.search(target)
    print(f"  找 ID {target}")
    print(f"  線性搜尋  比較 {c1:6d} 次  {t1:.3f} ms")
    print(f"  二分搜尋  比較 {c2:6d} 次  {t2:.3f} ms")
    print(f"  BST 搜尋  比較 {c3:6d} 次  {t3:.3f} ms")

    print(f"\n== 當日門診 {DAY} ==")
    day_list = dll.filter_by_day(DAY)
    day_heap = MaxHeap.from_records(day_list.to_list())
    calib = build_calibration(records)
    actual = sum(not r.showed_up for r in day_list)
    print(f"  當日 {len(day_list)} 人，預估未到 {expected_noshow(day_list, calib):.1f} 人"
          f"（實際未到 {actual} 人）")
    print("  Top-5 高風險：")
    for rank, r in enumerate(day_heap.top_k(5), 1):
        print(f"   {rank}. ID {r.appointment_id}  風險 {r.risk:5.1f}（{risk_level(r.risk)}）"
              f"  等待 {r.wait_days} 天  過往未到 {r.past_noshow} 次  {r.age} 歲")

    print("\n== 候補佇列 ==")
    q = pick_waitlist(records, day=WAIT_DAY, exclude_day=DAY, n=3, seed=1)
    print(f"  候補 {len(q)} 人，下一位 ID {q.peek().appointment_id}")
    print("\n（整合 AppointmentSystem 屬於任務 7，尚未實作）")


if __name__ == "__main__":
    main()
