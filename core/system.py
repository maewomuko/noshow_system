"""任務 7：AppointmentSystem —— 把所有資料結構整合成一個系統。

Streamlit 只呼叫這個類別，不直接碰各個結構（畫面與邏輯分開）。

內部組成：
  all_records  list           全部歷史資料（建校正表；不會被修改）
  calibration  dict           風險分數 → 歷史實際未到率
  patients     PatientBST     全部資料的病患索引（key = patient_id）
  id_gen       IdGenerator    產生新的掛號編號
  ---- 以下是「當日」結構，load_day() 時重建 ----
  roster       DoublyLinkedList  當日名單（O(1) 刪除）
  bst          BST               當日名單的編號索引（O(log n) 查詢），節點存 roster 節點參照
  heap         MaxHeap           當日名單的風險排序（Top-K）
  array        ArrayStore        當日名單的陣列版（對照組：線性搜尋）
  waitlist     LinkedQueue       現場候補（FIFO）

即存 log（CLAUDE.md 補充規則）：
  - 每次操作後把「操作後的完整 Record」附加到 data/logs/<看診日>.csv，寫完立刻 flush + fsync
  - 原始 CSV 永遠不修改
  - 第一次載入某天時，照 log 呼叫本類別自己的方法（cancel / add_record / refill /
    confirm_attend）重做一遍，恢復上次的狀態
"""

import csv
import os
import random
from dataclasses import asdict, fields
from pathlib import Path

from core.array_store import ArrayStore
from core.booking import IdGenerator, make_appointment
from core.bst import BST
from core.linked_list import DoublyLinkedList
from core.max_heap import MaxHeap
from core.patient_index import PatientBST
from core.queue_ll import LinkedQueue, pick_waitlist
from core.record import (DEFAULT_CSV, Record, build_calibration, expected_noshow,
                         load_records, risk_level)

DEFAULT_LOG_DIR = DEFAULT_CSV.parent / "logs"
RECORD_FIELDS = [f.name for f in fields(Record)]
LOG_FIELDS = ["action"] + RECORD_FIELDS

_INT_FIELDS = {"appointment_id", "patient_id", "age", "wait_days", "past_noshow"}
_BOOL_FIELDS = {"sms", "chronic"}


def record_from_row(row):
    """把 log 的一列轉回 Record。"""
    values = {}
    for name in RECORD_FIELDS:
        text = row[name]
        if name in _INT_FIELDS:
            values[name] = int(text)
        elif name == "risk":
            values[name] = float(text)
        elif name in _BOOL_FIELDS:
            values[name] = text == "True"
        elif name == "showed_up":
            values[name] = None if text == "" else text == "True"
        else:
            values[name] = text
    return Record(**values)


class AppointmentSystem:
    def __init__(self, records, log_dir=DEFAULT_LOG_DIR, seed=42):
        self.all_records = records
        self.calibration = build_calibration(records)        # 只用歷史資料
        shuffled = records[:]
        random.Random(seed).shuffle(shuffled)                # 打亂再插入，避免 BST 退化
        self.patients = PatientBST.from_records(shuffled)
        self.id_gen = IdGenerator(records)
        self.seed = seed
        self.log_dir = Path(log_dir) if log_dir else None

        self._by_day = {}                                    # 看診日 → 當天歷史預約
        for r in records:
            self._by_day.setdefault(r.appointment_day, []).append(r)
        self._added = {}            # 這次執行新增的預約（id → Record），切換日期時還要看得到
        self._cancelled = set()     # 已取消的掛號編號
        self._replayed = set()      # 已重播過 log 的日期
        self._replaying = False     # 重播中不再寫 log
        self._reserve_logged_ids()

        self.day = None
        self.neighbourhood = None
        self._reset_day_structures()

    @classmethod
    def load(cls, path=DEFAULT_CSV, log_dir=DEFAULT_LOG_DIR, seed=42, limit=None):
        return cls(load_records(path, limit=limit), log_dir=log_dir, seed=seed)

    # ------------------------------------------------------------------
    # 選日期
    # ------------------------------------------------------------------

    def days(self):
        """所有看診日（遞增）。"""
        return sorted(self._by_day)

    def neighbourhoods(self, day):
        """某天各區域的人數，人多的在前。回傳 [(區域, 人數)]。"""
        counts = {}
        for r in self._by_day.get(day, []):
            counts[r.neighbourhood] = counts.get(r.neighbourhood, 0) + 1
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    def load_day(self, day, neighbourhood=None, waitlist_size=5):
        """切換到某一天（可再依區域篩選），重建當日的 roster / bst / heap / array / waitlist。

        第一次載入某天時會重播 data/logs/<day>.csv。回傳 {"day", "count", "replayed"}。
        """
        if day not in self._by_day:
            raise ValueError(f"資料裡沒有 {day} 這一天")
        replayed = 0
        if day not in self._replayed:
            # 先用「不篩區域」的完整當日名單重播 log，讓所有操作都套用得上
            self._build_day(day, None, waitlist_size)
            replayed = self._replay_log(day)
            self._replayed.add(day)
        self._build_day(day, neighbourhood, waitlist_size)
        return {"day": day, "count": len(self.roster), "replayed": replayed}

    def _reset_day_structures(self):
        self.roster = DoublyLinkedList()
        self.bst = BST()
        self.heap = MaxHeap()
        self.array = ArrayStore()
        self.waitlist = LinkedQueue()

    def _build_day(self, day, neighbourhood, waitlist_size):
        self.day, self.neighbourhood = day, neighbourhood
        self._reset_day_structures()

        def keep(r):
            return neighbourhood is None or r.neighbourhood == neighbourhood

        day_records = [r for r in self._by_day[day]
                       if r.appointment_id not in self._cancelled and keep(r)]
        day_records += [r for r in self._added.values()
                        if r.appointment_day == day and keep(r)]
        day_records.sort(key=lambda r: (-r.risk, r.appointment_id))   # 名單顯示順序

        # roster 依顯示順序串起來；BST 用打亂的順序插入，避免退化
        nodes = {r.appointment_id: self.roster.append(r) for r in day_records}
        shuffled = day_records[:]
        random.Random(self.seed).shuffle(shuffled)
        for r in shuffled:
            self.bst.insert(r, nodes[r.appointment_id])
        self.heap.build_heap(day_records)                              # O(n) 建堆
        self.array = ArrayStore(day_records)
        self.waitlist = self._make_waitlist(day, waitlist_size)

    def _make_waitlist(self, day, size):
        """從隔天（最後一天則用前一天）抽 size 位病患，替他們建立「今天現場掛號」的新預約。"""
        days = self.days()
        i = days.index(day)
        source = days[i + 1] if i + 1 < len(days) else days[i - 1]
        picked = pick_waitlist(self.all_records, day=source, exclude_day=day, n=size,
                               seed=self.seed + i)
        queue = LinkedQueue()
        while not picked.is_empty():
            p = picked.dequeue()
            out = make_appointment(
                self.patients, self.id_gen, patient_id=p.patient_id, age=p.age,
                scheduled_day=day, appointment_day=day, gender=p.gender,
                neighbourhood=self.neighbourhood or p.neighbourhood, chronic=p.chronic)
            queue.enqueue(out["record"])
        return queue

    # ------------------------------------------------------------------
    # 讀取
    # ------------------------------------------------------------------

    def overview(self):
        """當日名單（依 roster 順序），每筆是 dict，給表格顯示。"""
        return [self._row(r) for r in self.roster]

    @staticmethod
    def _row(r):
        return {
            "掛號編號": r.appointment_id,
            "病患編號": r.patient_id,
            "年齡": r.age,
            "性別": r.gender,
            "區域": r.neighbourhood,
            "等待天數": r.wait_days,
            "過往未到": r.past_noshow,
            "風險": r.risk,
            "燈號": risk_level(r.risk),
            "簡訊": r.sms,
            "慢性病": r.chronic,
        }

    def search(self, appointment_id):
        """BST 查詢。回傳 (Record 或 None, 比較次數, 耗時 ms)。"""
        node, comparisons, ms = self.bst.search(appointment_id)
        return (node.record if node else None), comparisons, ms

    def compare_search(self, appointment_id):
        """同一個編號，用 BST 和陣列線性搜尋各查一次，給畫面比較。"""
        record, bst_cmp, bst_ms = self.search(appointment_id)
        _, lin_cmp, lin_ms = self.array.linear_search(appointment_id)
        return {
            "record": record,
            "bst": {"comparisons": bst_cmp, "ms": bst_ms},
            "linear": {"comparisons": lin_cmp, "ms": lin_ms},
            "path": self.bst.search_path(appointment_id),
            "height": self.bst.height(),
            "size": len(self.bst),
        }

    def top_risk(self, k):
        """前 K 名高風險（由高到低），O(K log K)，不破壞 heap。"""
        return self.heap.top_k(k)

    def heap_preview(self, levels=4):
        """Heap 陣列的前幾層（畫樹狀圖用）。"""
        return self.heap.to_list()[: 2 ** levels - 1]

    def expected_noshow(self):
        """預估當日未到人數 = 每人「同分者歷史未到率」加總。"""
        return expected_noshow(self.roster, self.calibration)

    def level_counts(self):
        counts = {"紅": 0, "黃": 0, "綠": 0}
        for r in self.roster:
            counts[risk_level(r.risk)] += 1
        return counts

    def patient_history(self, patient_id):
        """病患索引查詢：回傳 (該病患預約 list 或 None, 比較次數, 耗時 ms)。"""
        return self.patients.search(patient_id)

    # ------------------------------------------------------------------
    # 修改（每個操作都同步 roster / bst / heap / array / patients，並寫 log）
    # ------------------------------------------------------------------

    def confirm_attend(self, appointment_id, new_risk=0.0):
        """電訪確認會到 → 調降風險，heap 中往下沉。O(log n)。"""
        if appointment_id not in self.heap:
            return {"ok": False, "message": f"今日名單中找不到掛號編號 {appointment_id}"}
        node, _, _ = self.bst.search(appointment_id)
        old = node.record.risk
        self.heap.update_key(appointment_id, float(new_risk))   # 同時改到共用的 Record
        self._log("confirm", node.record)
        return {"ok": True, "record": node.record, "old_risk": old,
                "message": f"{appointment_id} 已確認會到，風險 {old:.0f} → {new_risk:.0f}"}

    def cancel(self, appointment_id):
        """取消預約。順序：BST 找節點 → roster 刪節點 → bst 刪 → heap 刪 → array 刪 → patients 刪。"""
        node, _, _ = self.bst.search(appointment_id)                # O(log n)
        if node is None:
            return {"ok": False, "message": f"今日名單中找不到掛號編號 {appointment_id}（可能已取消）"}
        record = node.record
        self.roster.delete_node(node.ll_node)                       # O(1)
        self.bst.delete(appointment_id)                             # O(log n)
        self.heap.remove(appointment_id)                            # O(log n)
        self.array.delete(appointment_id)                           # O(n)，對照組
        self.patients.remove_record(record)
        self._cancelled.add(appointment_id)
        self._added.pop(appointment_id, None)
        self._log("cancel", record)
        return {"ok": True, "record": record, "message": f"已取消 {appointment_id}"}

    def add(self, patient_id, age, scheduled_day, appointment_day=None, gender="F",
            neighbourhood=None, sms=False, chronic=False):
        """新增預約到目前載入的這一天。回傳 make_appointment 的 dict（record、level、is_new、history…）。

        輸入不合理時丟出 ValueError。
        """
        if self.day is None:
            raise ValueError("請先載入某一天")
        appointment_day = appointment_day or self.day
        if appointment_day != self.day:
            raise ValueError(f"只能新增目前載入日期（{self.day}）的預約")
        out = make_appointment(
            self.patients, self.id_gen, patient_id=int(patient_id), age=int(age),
            scheduled_day=scheduled_day, appointment_day=appointment_day, gender=gender,
            neighbourhood=neighbourhood if neighbourhood is not None else (self.neighbourhood or ""),
            sms=sms, chronic=chronic)
        self.add_record(out["record"])
        self._log("add", out["record"])
        return out

    def add_record(self, record):
        """把一筆已算好風險的 Record 寫進所有當日結構（add、refill、重播 log 共用）。"""
        node = self.roster.append(record)       # O(1)
        self.bst.insert(record, node)           # O(log n)
        self.heap.push(record)                  # O(log n)
        self.array.append(record)               # O(1)
        self.patients.insert(record)            # O(log n)
        self._added[record.appointment_id] = record
        self.id_gen.reserve(record.appointment_id)

    def refill(self, replay_record=None):
        """候補遞補：waitlist 前端出隊 O(1) → 寫進所有當日結構。

        replay_record 只給重播 log 用：照樣出隊一位，但寫入 log 裡的那筆 Record。
        """
        nxt = self.waitlist.dequeue()
        record = replay_record or nxt
        if record is None:
            return {"ok": False, "message": "候補隊伍是空的"}
        self.add_record(record)
        self._log("refill", record)
        return {"ok": True, "record": record, "level": risk_level(record.risk),
                "remaining": len(self.waitlist),
                "message": f"候補病患 {record.patient_id} 已遞補（掛號編號 {record.appointment_id}）"}

    # ------------------------------------------------------------------
    # 同步檢查
    # ------------------------------------------------------------------

    def check_consistency(self):
        """roster / bst / heap / array 必須同步；有問題丟 AssertionError。"""
        n = len(self.roster)
        assert n == len(self.bst) == len(self.heap) == len(self.array), \
            f"人數不一致 roster={n} bst={len(self.bst)} heap={len(self.heap)} array={len(self.array)}"
        assert [r.appointment_id for r in self.roster.to_list_reverse()][::-1] == \
               [r.appointment_id for r in self.roster]
        for r in self.roster:
            node = self.bst.search(r.appointment_id)[0]
            assert node is not None and node.record is r, f"BST 缺少 {r.appointment_id}"
            assert node.ll_node.record is r, f"BST 的 ll_node 指錯 {r.appointment_id}"
            assert r.appointment_id in self.heap, f"Heap 缺少 {r.appointment_id}"
            history = self.patients.search(r.patient_id)[0] or []
            assert any(h is r for h in history), f"病患索引缺少 {r.appointment_id}"
        assert self.heap.is_valid(), "Heap 性質被破壞"
        keys = [r.appointment_id for r in self.bst.inorder()]
        assert keys == sorted(keys), "BST 中序走訪不是遞增"
        return True

    # ------------------------------------------------------------------
    # 即存 log
    # ------------------------------------------------------------------

    def log_path(self, day=None):
        if self.log_dir is None:
            return None
        return self.log_dir / f"{day or self.day}.csv"

    def _log(self, action, record):
        """附加一列到 data/logs/<看診日>.csv，立刻 flush + fsync，程式當掉也不會漏。"""
        if self._replaying or self.log_dir is None:
            return
        path = self.log_path()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            if is_new:
                writer.writeheader()
            row = {"action": action, **asdict(record)}
            if row["showed_up"] is None:
                row["showed_up"] = ""
            writer.writerow(row)
            f.flush()
            os.fsync(f.fileno())

    def _read_log(self, day):
        path = self.log_path(day)
        if path is None or not path.exists():
            return []
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _reserve_logged_ids(self):
        """開機時掃過所有 log，新產生的掛號編號不會跟 log 裡的重複。"""
        if self.log_dir is None or not self.log_dir.exists():
            return
        for path in self.log_dir.glob("*.csv"):
            for row in self._read_log(path.stem):
                self.id_gen.reserve(int(row["appointment_id"]))

    def _replay_log(self, day):
        """照 log 呼叫本類別的方法重做一遍。回傳重播的筆數。"""
        rows = self._read_log(day)
        self._replaying = True
        try:
            for row in rows:
                record = record_from_row(row)
                action = row["action"]
                if action == "cancel":
                    self.cancel(record.appointment_id)
                elif action == "confirm":
                    self.confirm_attend(record.appointment_id, record.risk)
                elif action == "add":
                    self.add_record(record)
                elif action == "refill":
                    self.refill(replay_record=record)
        finally:
            self._replaying = False
        return len(rows)
