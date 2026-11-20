"""任務 5：Queue（以單向 Linked List 實作）—— 現場候補遞補。

知識點：先進先出 FIFO；enqueue 從尾端、dequeue 從前端，皆 O(1)；
       用鏈結實作，不會有陣列版「前端空出要搬移」的問題。
用在：畫面三（候補遞補），與 Heap 串成「找出高風險 → 確認取消 → 自動補人」。

另附 ArrayQueue（用 list.pop(0)，O(n)）當實驗三的對照組。
"""


class _QNode:
    __slots__ = ("record", "next")

    def __init__(self, record):
        self.record = record
        self.next = None


class LinkedQueue:
    def __init__(self):
        self.head = None    # 前端（下一個出隊）
        self.tail = None    # 尾端（最新加入）
        self._size = 0

    def __len__(self):
        return self._size

    def is_empty(self):
        return self._size == 0

    def enqueue(self, record):
        """尾端加入，O(1)。"""
        node = _QNode(record)
        if self.tail is None:
            self.head = self.tail = node
        else:
            self.tail.next = node
            self.tail = node
        self._size += 1

    def dequeue(self):
        """前端取出，O(1)。空的時候回傳 None。"""
        if self.head is None:
            return None
        node = self.head
        self.head = node.next
        if self.head is None:
            self.tail = None
        self._size -= 1
        return node.record

    def peek(self):
        return self.head.record if self.head else None

    def to_list(self):
        out, node = [], self.head
        while node:
            out.append(node.record)
            node = node.next
        return out

    @classmethod
    def from_records(cls, records):
        q = cls()
        for r in records:
            q.enqueue(r)
        return q


class ArrayQueue:
    """實驗三對照組：用 list 實作，dequeue 用 pop(0)，每次要搬移全部元素 O(n)。"""

    def __init__(self):
        self.data = []

    def __len__(self):
        return len(self.data)

    def is_empty(self):
        return not self.data

    def enqueue(self, record):
        self.data.append(record)

    def dequeue(self):
        return self.data.pop(0) if self.data else None

    def peek(self):
        return self.data[0] if self.data else None

    def to_list(self):
        return list(self.data)


def pick_waitlist(records, day, exclude_day, n=5, seed=None):
    """任務 5-6：從另一天（day）抽 n 筆當作 exclude_day 當天的現場候補病患。

    回傳 LinkedQueue。seed 可固定抽樣結果，方便 Demo 重現。
    """
    import random
    pool = [r for r in records if r.appointment_day == day and r.appointment_day != exclude_day]
    rng = random.Random(seed)
    chosen = rng.sample(pool, min(n, len(pool)))
    return LinkedQueue.from_records(chosen)
