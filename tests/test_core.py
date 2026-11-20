"""任務 0~5 的單元測試。執行：python -m pytest tests -v"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.record import (Record, load_records, calc_risk, risk_level, validate_risk,
                         compute_past_noshow, build_calibration, expected_noshow)
from core.array_store import ArrayStore
from core.bst import BST
from core.linked_list import DoublyLinkedList
from core.max_heap import MaxHeap
from core.queue_ll import LinkedQueue, ArrayQueue, pick_waitlist


def make(i, risk=0.0, age=30, wait=0, patient=None, day="2016-05-01", showed=True):
    return Record(appointment_id=i, patient_id=patient if patient is not None else i, age=age,
                  gender="F", wait_days=wait, scheduled_day=day, appointment_day=day,
                  neighbourhood="X", sms=False, chronic=False, showed_up=showed, risk=risk)


@pytest.fixture(scope="module")
def all_records():
    return load_records()


# ---------------- 任務 0 ----------------

class TestRecord:
    def test_load_count_and_clean(self, all_records):
        assert len(all_records) == 106_982          # 106,987 - 5 筆負等待天數
        assert all(r.wait_days >= 0 for r in all_records)

    def test_ids_unique(self, all_records):
        assert len({r.appointment_id for r in all_records}) == len(all_records)

    def test_past_noshow(self):
        recs = [make(1, patient=9, day="2016-05-01", showed=False),
                make(2, patient=9, day="2016-05-03", showed=True),
                make(3, patient=9, day="2016-05-05", showed=False),
                make(4, patient=9, day="2016-05-07")]
        compute_past_noshow(recs)
        assert [r.past_noshow for r in recs] == [0, 1, 1, 2]

    def test_risk_range_and_level(self, all_records):
        assert all(0 <= r.risk <= 100 for r in all_records)
        assert calc_risk(make(1, age=25, wait=30)) == 45 + 0 + 20
        assert risk_level(70) == "紅" and risk_level(40) == "黃" and risk_level(39) == "綠"

    def test_calibration(self, all_records):
        calib = build_calibration(all_records)
        exp = expected_noshow(all_records, calib)
        actual = sum(not r.showed_up for r in all_records)
        assert abs(exp - actual) < 1          # 全體加總應等於實際未到數
        assert calib[0.0] < calib[100.0]

    def test_risk_is_meaningful(self, all_records):
        v = validate_risk(all_records)
        assert v["紅"][1] > v["黃"][1] > v["綠"][1]


# ---------------- 任務 1 ----------------

class TestArray:
    def test_linear_and_binary_search(self):
        recs = [make(i) for i in random.Random(1).sample(range(1000), 200)]
        arr = ArrayStore(recs)
        target = recs[150].appointment_id
        r, comps, _ = arr.linear_search(target)
        assert r.appointment_id == target and comps == 151
        r, comps, _ = arr.binary_search(target)
        assert r.appointment_id == target and comps <= 8
        assert arr.linear_search(-1)[0] is None
        assert arr.binary_search(-1)[0] is None

    def test_delete_shifts(self):
        arr = ArrayStore([make(i) for i in range(10)])
        ok, shifts, _ = arr.delete(3)
        assert ok and shifts == 6 and len(arr) == 9
        assert [r.appointment_id for r in arr.to_list()] == [0, 1, 2, 4, 5, 6, 7, 8, 9]
        assert arr.delete(99)[0] is False


# ---------------- 任務 2 ----------------

class TestBST:
    def test_insert_inorder_search(self):
        ids = random.Random(2).sample(range(10_000), 2000)
        t = BST.from_records([make(i) for i in ids])
        assert len(t) == 2000
        assert [r.appointment_id for r in t.inorder()] == sorted(ids)
        node, comps, _ = t.search(ids[500])
        assert node.key == ids[500] and comps <= t.height()
        assert t.search(-5)[0] is None

    def test_duplicate_insert(self):
        t = BST()
        assert t.insert(make(5)) is True
        assert t.insert(make(5, risk=9)) is False
        assert len(t) == 1 and t.search(5)[0].record.risk == 9

    @pytest.mark.parametrize("target", [20, 30, 50])   # 0 子、1 子、2 子
    def test_delete_three_cases(self, target):
        t = BST()
        for i in [50, 30, 70, 20, 60, 80, 35, 33]:
            t.insert(make(i))
        # 20 = 葉節點；35 只有左子 33；30 有兩個子；50 = 根且有兩個子
        removed = t.delete(target)
        assert removed.key == target
        keys = [r.appointment_id for r in t.inorder()]
        assert target not in keys and keys == sorted(keys) and len(t) == 7

    def test_delete_one_child_and_missing(self):
        t = BST()
        for i in [50, 30, 70, 35, 33]:
            t.insert(make(i))
        t.delete(35)   # 只有一個左子
        assert [r.appointment_id for r in t.inorder()] == [30, 33, 50, 70]
        assert t.delete(999) is None

    def test_delete_all_random(self):
        ids = random.Random(3).sample(range(5000), 500)
        t = BST.from_records([make(i) for i in ids])
        for i in random.Random(4).sample(ids, 500):
            assert t.delete(i) is not None
        assert len(t) == 0 and t.root is None

    def test_degenerate_height(self):
        sorted_tree = BST.from_records([make(i) for i in range(2000)])
        assert sorted_tree.height() == 2000       # 依序插入 → 退化成鏈
        ids = list(range(2000))
        random.Random(5).shuffle(ids)
        assert BST.from_records([make(i) for i in ids]).height() < 40

    def test_search_path(self):
        t = BST()
        for i in [50, 30, 70, 35]:
            t.insert(make(i))
        assert t.search_path(35) == [50, 30, 35]

    def test_ll_node_reference(self):
        dll, t = DoublyLinkedList(), BST()
        for i in [5, 3, 8]:
            r = make(i)
            t.insert(r, dll.append(r))
        node = t.search(3)[0]
        dll.delete_node(node.ll_node)
        assert [r.appointment_id for r in dll] == [5, 8]


# ---------------- 任務 3 ----------------

class TestDoublyLinkedList:
    def ids(self, dll):
        fwd = [r.appointment_id for r in dll.to_list()]
        bwd = [r.appointment_id for r in dll.to_list_reverse()]
        assert fwd == bwd[::-1]          # prev / next 指標一致
        return fwd

    def test_delete_head_tail_middle_last(self):
        dll = DoublyLinkedList()
        nodes = [dll.append(make(i)) for i in range(5)]
        dll.delete_node(nodes[2]); assert self.ids(dll) == [0, 1, 3, 4]
        dll.delete_node(nodes[0]); assert self.ids(dll) == [1, 3, 4]
        dll.delete_node(nodes[4]); assert self.ids(dll) == [1, 3]
        dll.delete_node(nodes[1]); dll.delete_node(nodes[3])
        assert self.ids(dll) == [] and dll.head is None and dll.tail is None and len(dll) == 0
        dll.append(make(9)); assert self.ids(dll) == [9]

    def test_filter_and_find(self):
        dll = DoublyLinkedList.from_records(
            [make(1, day="2016-05-01"), make(2, day="2016-05-02"), make(3, day="2016-05-01")])
        assert [r.appointment_id for r in dll.filter_by_day("2016-05-01")] == [1, 3]
        assert dll.find(2).record.appointment_id == 2 and dll.find(7) is None


# ---------------- 任務 4 ----------------

class TestMaxHeap:
    def recs(self, n=500, seed=6):
        rng = random.Random(seed)
        return [make(i, risk=float(rng.randint(0, 100))) for i in range(n)]

    def expected_top(self, recs, k):
        return [r.appointment_id for r in sorted(recs, key=lambda r: (-r.risk, r.appointment_id))[:k]]

    def test_push_pop_order(self):
        recs = self.recs()
        h = MaxHeap()
        for r in recs:
            h.push(r)
            assert h.is_valid() if r.appointment_id % 50 == 0 else True
        out = [h.pop().appointment_id for _ in range(len(recs))]
        assert out == self.expected_top(recs, len(recs)) and h.pop() is None

    def test_build_heap_and_top_k(self):
        recs = self.recs()
        h = MaxHeap.from_records(recs)
        assert h.is_valid()
        for k in (1, 10, 100, 500, 600):
            assert [r.appointment_id for r in h.top_k(k)] == self.expected_top(recs, k)
        assert len(h) == 500 and h.is_valid()     # top_k 不破壞 heap
        assert h.top_k(0) == []

    def test_update_key(self):
        recs = self.recs()
        h = MaxHeap.from_records(recs)
        top = h.peek().appointment_id
        assert h.update_key(top, 0.0)              # 電訪確認會到 → 往下沉
        assert h.peek().appointment_id != top and h.is_valid()
        assert h.update_key(7, 1000.0)             # 往上浮
        assert h.peek().appointment_id == 7 and h.is_valid()
        assert h.update_key(-1, 5) is False

    def test_remove_random(self):
        recs = self.recs()
        h = MaxHeap.from_records(recs)
        remaining = {r.appointment_id: r for r in recs}
        for i in random.Random(7).sample(range(500), 300):
            assert h.remove(i).appointment_id == i
            del remaining[i]
            assert h.is_valid()
        assert len(h) == 200 and h.remove(-1) is None
        assert [r.appointment_id for r in h.top_k(20)] == self.expected_top(remaining.values(), 20)

    def test_push_existing_updates(self):
        h = MaxHeap.from_records([make(1, risk=10), make(2, risk=20)])
        h.push(make(1, risk=90))
        assert len(h) == 2 and h.peek().appointment_id == 1 and h.is_valid()


# ---------------- 任務 5 ----------------

class TestQueue:
    @pytest.mark.parametrize("cls", [LinkedQueue, ArrayQueue])
    def test_fifo(self, cls):
        q = cls()
        assert q.dequeue() is None and q.peek() is None and q.is_empty()
        for i in range(5):
            q.enqueue(make(i))
        assert q.peek().appointment_id == 0 and len(q) == 5
        assert [q.dequeue().appointment_id for _ in range(3)] == [0, 1, 2]
        q.enqueue(make(9))
        assert [r.appointment_id for r in q.to_list()] == [3, 4, 9]
        while not q.is_empty():
            q.dequeue()
        assert len(q) == 0 and q.dequeue() is None
        q.enqueue(make(7)); assert q.peek().appointment_id == 7

    def test_pick_waitlist(self, all_records):
        q = pick_waitlist(all_records, day="2016-06-07", exclude_day="2016-06-06", n=5, seed=1)
        assert len(q) == 5 and all(r.appointment_day == "2016-06-07" for r in q.to_list())
