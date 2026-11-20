"""任務 4：Max-Heap —— 高風險 Top-K 名單（系統核心）。

知識點：完全二元樹、父 >= 子；陣列儲存（子 2i+1 / 2i+2，父 (i-1)//2）；
       sift-up / sift-down；插入、取出 O(log n)；建堆 O(n)；優先佇列。
用在：畫面二（Top-K、電訪調降、取消）、畫面四（新增）、實驗二。

排序依據：risk 大者優先；同分時 appointment_id 小者優先（讓結果可重現）。
pos 字典記錄「appointment_id → 在陣列中的索引」，update_key / remove 才能 O(log n)。
"""


class MaxHeap:
    def __init__(self):
        self.data = []     # 存 Record
        self.pos = {}      # appointment_id -> index

    def __len__(self):
        return len(self.data)

    def __contains__(self, appointment_id):
        return appointment_id in self.pos

    def is_empty(self):
        return not self.data

    # ---- 基本工具 ----

    @staticmethod
    def _higher(a, b):
        """a 的優先權是否高於 b。"""
        if a.risk != b.risk:
            return a.risk > b.risk
        return a.appointment_id < b.appointment_id

    def _swap(self, i, j):
        d = self.data
        d[i], d[j] = d[j], d[i]
        self.pos[d[i].appointment_id] = i
        self.pos[d[j].appointment_id] = j

    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self._higher(self.data[i], self.data[parent]):
                self._swap(i, parent)
                i = parent
            else:
                break

    def _sift_down(self, i):
        n = len(self.data)
        while True:
            largest = i
            left, right = 2 * i + 1, 2 * i + 2
            if left < n and self._higher(self.data[left], self.data[largest]):
                largest = left
            if right < n and self._higher(self.data[right], self.data[largest]):
                largest = right
            if largest == i:
                break
            self._swap(i, largest)
            i = largest

    # ---- 對外操作 ----

    def push(self, record):
        """插入，O(log n)。ID 已存在則改成更新分數。"""
        if record.appointment_id in self.pos:
            self.update_key(record.appointment_id, record.risk)
            return
        self.data.append(record)
        self.pos[record.appointment_id] = len(self.data) - 1
        self._sift_up(len(self.data) - 1)

    def peek(self):
        """看最大值，O(1)。"""
        return self.data[0] if self.data else None

    def pop(self):
        """取出最大值，O(log n)。"""
        if not self.data:
            return None
        self._swap(0, len(self.data) - 1)
        top = self.data.pop()
        del self.pos[top.appointment_id]
        if self.data:
            self._sift_down(0)
        return top

    def top_k(self, k):
        """回傳前 k 名（由高到低），不破壞原 heap。

        做法：另用一個小 heap 存「候選索引」，從根開始往下展開，
        只看 k 個節點附近，O(k log k)，比 pop k 次再 push 回去更乾淨。
        """
        if k <= 0 or not self.data:
            return []
        result = []
        candidates = MaxHeap._IndexHeap(self)
        candidates.push(0)
        n = len(self.data)
        while candidates and len(result) < k:
            i = candidates.pop()
            result.append(self.data[i])
            for c in (2 * i + 1, 2 * i + 2):
                if c < n:
                    candidates.push(c)
        return result

    def update_key(self, appointment_id, new_risk):
        """修改某人的風險分數：變大往上浮、變小往下沉，O(log n)。回傳是否成功。"""
        i = self.pos.get(appointment_id)
        if i is None:
            return False
        old = self.data[i].risk
        self.data[i].risk = new_risk
        if new_risk > old:
            self._sift_up(i)
        else:
            self._sift_down(i)
        return True

    def remove(self, appointment_id):
        """移除任意一人，O(log n)。回傳被移除的 Record（找不到回傳 None）。"""
        i = self.pos.get(appointment_id)
        if i is None:
            return None
        last = len(self.data) - 1
        self._swap(i, last)
        removed = self.data.pop()
        del self.pos[appointment_id]
        if i < len(self.data):        # 補上來的元素可能要往上或往下
            moved_id = self.data[i].appointment_id
            self._sift_up(i)
            self._sift_down(self.pos[moved_id])
        return removed

    def build_heap(self, records):
        """一次建堆（heapify），O(n)。會清空原本內容。"""
        self.data = list(records)
        self.pos = {r.appointment_id: i for i, r in enumerate(self.data)}
        for i in range(len(self.data) // 2 - 1, -1, -1):
            self._sift_down(i)

    @classmethod
    def from_records(cls, records):
        h = cls()
        h.build_heap(records)
        return h

    def to_list(self):
        """依陣列順序（不是排序結果）回傳，畫 heap 樹狀圖用。"""
        return list(self.data)

    def is_valid(self):
        """檢查 heap 性質與 pos 是否一致（測試用）。"""
        n = len(self.data)
        for i in range(n):
            if self.pos.get(self.data[i].appointment_id) != i:
                return False
            for c in (2 * i + 1, 2 * i + 2):
                if c < n and self._higher(self.data[c], self.data[i]):
                    return False
        return len(self.pos) == n

    class _IndexHeap:
        """top_k 內部用：存主 heap 的索引，依對應 Record 的優先權排序。"""

        def __init__(self, owner):
            self.owner = owner
            self.items = []

        def __bool__(self):
            return bool(self.items)

        def _hi(self, a, b):
            return MaxHeap._higher(self.owner.data[a], self.owner.data[b])

        def push(self, idx):
            items = self.items
            items.append(idx)
            i = len(items) - 1
            while i > 0:
                p = (i - 1) // 2
                if self._hi(items[i], items[p]):
                    items[i], items[p] = items[p], items[i]
                    i = p
                else:
                    break

        def pop(self):
            items = self.items
            top = items[0]
            last = items.pop()
            if items:
                items[0] = last
                i, n = 0, len(items)
                while True:
                    best = i
                    for c in (2 * i + 1, 2 * i + 2):
                        if c < n and self._hi(items[c], items[best]):
                            best = c
                    if best == i:
                        break
                    items[i], items[best] = items[best], items[i]
                    i = best
            return top
