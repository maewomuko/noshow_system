"""病患索引：以 patient_id 為 key 的 BST。

知識點：同一份資料可以依「不同的 key」建立不同的索引。
  - core/bst.py 的 BST      → key = appointment_id（一次預約一個節點）
  - 這裡的 PatientBST       → key = patient_id（一位病患一個節點，節點裡存他所有預約）
用在：新增預約時叫出病患舊紀錄，算「過往未到次數」。

一位病患可能有多筆預約，所以節點存的是 list（依看診日排序），
這是「BST + 每個節點掛一串資料」的做法。
全部用迴圈實作，不用遞迴。
"""

import time


class PatientNode:
    __slots__ = ("key", "records", "left", "right")

    def __init__(self, patient_id):
        self.key = patient_id
        self.records = []      # 這位病患的所有預約，依 (看診日, 掛號編號) 排序
        self.left = None
        self.right = None


class PatientBST:
    def __init__(self):
        self.root = None
        self._patients = 0     # 節點數 = 病患人數
        self._records = 0      # 總預約筆數

    def __len__(self):
        """病患人數。"""
        return self._patients

    @property
    def record_count(self):
        return self._records

    # ---- 插入 ----

    def insert(self, record):
        """把一筆預約加到該病患的節點；病患不存在就建立新節點。O(log n) + 該病患筆數。"""
        pid = record.patient_id
        if self.root is None:
            self.root = PatientNode(pid)
            node = self.root
            self._patients += 1
        else:
            node = self.root
            while True:
                if pid == node.key:
                    break
                nxt = node.left if pid < node.key else node.right
                if nxt is None:
                    new = PatientNode(pid)
                    if pid < node.key:
                        node.left = new
                    else:
                        node.right = new
                    node = new
                    self._patients += 1
                    break
                node = nxt

        # 依看診日插入到正確位置（每位病患的筆數很少，線性插入即可）
        key = (record.appointment_day, record.appointment_id)
        recs = node.records
        i = len(recs)
        while i > 0 and (recs[i - 1].appointment_day, recs[i - 1].appointment_id) > key:
            i -= 1
        recs.insert(i, record)
        self._records += 1

    # ---- 查詢 ----

    def search(self, patient_id):
        """回傳 (該病患的預約 list 或 None, 比較次數, 耗時 ms)。"""
        start = time.perf_counter()
        comparisons = 0
        node = self.root
        while node:
            comparisons += 1
            if patient_id == node.key:
                return node.records, comparisons, (time.perf_counter() - start) * 1000
            node = node.left if patient_id < node.key else node.right
        return None, comparisons, (time.perf_counter() - start) * 1000

    def past_noshow(self, patient_id, before_day):
        """這位病患在 before_day「之前」未到診幾次。查不到 = 新病患 = 0。

        showed_up 為 None（新預約、還沒看診）的不算。
        """
        records, _, _ = self.search(patient_id)
        if not records:
            return 0
        return sum(1 for r in records
                   if r.appointment_day < before_day and r.showed_up is False)

    # ---- 刪除（取消預約時用）----

    def remove_record(self, record):
        """從該病患節點移除這一筆預約。節點保留（病患仍有歷史資料）。回傳是否成功。"""
        records, _, _ = self.search(record.patient_id)
        if not records:
            return False
        for i, r in enumerate(records):
            if r.appointment_id == record.appointment_id:
                records.pop(i)
                self._records -= 1
                return True
        return False

    # ---- 其他 ----

    def height(self):
        if self.root is None:
            return 0
        level, h = [self.root], 0
        while level:
            h += 1
            level = [c for n in level for c in (n.left, n.right) if c]
        return h

    @classmethod
    def from_records(cls, records):
        """開機建檔用。records 建議先打亂，避免 BST 退化。"""
        idx = cls()
        for r in records:
            idx.insert(r)
        return idx
