"""任務 1：Array —— 對照組。

知識點：連續儲存、索引 O(1)、線性搜尋 O(n)、二分搜尋 O(log n)、中間刪除需搬移 O(n)。
用在：實驗一（搜尋比較）、實驗三（刪除比較）。
"""

import time


class ArrayStore:
    def __init__(self, records=None):
        # 用 Python list 模擬陣列，照原始順序存放
        self.data = list(records) if records else []
        self._sorted = None   # 依 ID 排序的副本（二分搜尋用）

    def __len__(self):
        return len(self.data)

    def to_list(self):
        return list(self.data)

    def append(self, record):
        """加在最後，O(1)。"""
        self.data.append(record)
        self._sorted = None

    def linear_search(self, appointment_id):
        """線性搜尋，O(n)。回傳 (record 或 None, 比較次數, 耗時 ms)。"""
        start = time.perf_counter()
        comparisons = 0
        for record in self.data:
            comparisons += 1
            if record.appointment_id == appointment_id:
                return record, comparisons, (time.perf_counter() - start) * 1000
        return None, comparisons, (time.perf_counter() - start) * 1000

    def delete(self, appointment_id):
        """先線性找到位置，再手動把後面的元素往前搬一格，O(n)。

        刻意不用 list.remove / del，才看得到搬移成本。
        回傳 (是否刪除成功, 搬移次數, 耗時 ms)。
        """
        start = time.perf_counter()
        index = -1
        for i, record in enumerate(self.data):
            if record.appointment_id == appointment_id:
                index = i
                break
        if index == -1:
            return False, 0, (time.perf_counter() - start) * 1000

        shifts = 0
        for i in range(index, len(self.data) - 1):
            self.data[i] = self.data[i + 1]
            shifts += 1
        self.data.pop()          # 移除最後一格（已被往前複製）
        self._sorted = None
        return True, shifts, (time.perf_counter() - start) * 1000

    # ---- 二分搜尋（實驗一的第三組對照）----

    def sorted_copy(self):
        """依 appointment_id 排序的副本，快取起來避免重複排序。"""
        if self._sorted is None:
            self._sorted = sorted(self.data, key=lambda r: r.appointment_id)
        return self._sorted

    def binary_search(self, appointment_id):
        """在排序副本上二分搜尋，O(log n)。回傳 (record 或 None, 比較次數, 耗時 ms)。

        注意：排序本身的成本（O(n log n)）不算在這裡，報告時要說明。
        """
        arr = self.sorted_copy()
        start = time.perf_counter()
        comparisons = 0
        low, high = 0, len(arr) - 1
        while low <= high:
            mid = (low + high) // 2
            comparisons += 1
            key = arr[mid].appointment_id
            if key == appointment_id:
                return arr[mid], comparisons, (time.perf_counter() - start) * 1000
            if key < appointment_id:
                low = mid + 1
            else:
                high = mid - 1
        return None, comparisons, (time.perf_counter() - start) * 1000
