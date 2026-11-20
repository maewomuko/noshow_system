"""任務 3：Doubly Linked List —— 當日門診名單。

知識點：節點用 prev / next 指標串接；已持有節點時刪除 O(1)；無法用索引直接存取。
用在：畫面一（總覽表）、畫面二（退掛刪除）、實驗三。
"""


class DLLNode:
    __slots__ = ("record", "prev", "next")

    def __init__(self, record):
        self.record = record
        self.prev = None
        self.next = None


class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self._size = 0

    def __len__(self):
        return self._size

    def __iter__(self):
        node = self.head
        while node:
            yield node.record
            node = node.next

    def is_empty(self):
        return self._size == 0

    def append(self, record):
        """加到尾端，O(1)。回傳新節點（BST 會存這個參照）。"""
        node = DLLNode(record)
        if self.tail is None:            # 空串列
            self.head = self.tail = node
        else:
            node.prev = self.tail
            self.tail.next = node
            self.tail = node
        self._size += 1
        return node

    def delete_node(self, node):
        """刪除指定節點，O(1)。處理頭、尾、中間、只剩一個四種情況。"""
        if node.prev:
            node.prev.next = node.next
        else:                            # 刪的是頭
            self.head = node.next
        if node.next:
            node.next.prev = node.prev
        else:                            # 刪的是尾
            self.tail = node.prev
        node.prev = node.next = None     # 斷開，避免誤用
        self._size -= 1
        return node.record

    def find(self, appointment_id):
        """線性找節點，O(n)。整合時應改用 BST 找，這裡只供測試或對照。"""
        node = self.head
        while node:
            if node.record.appointment_id == appointment_id:
                return node
            node = node.next
        return None

    def to_list(self):
        """從頭走到尾，回傳 Record list（給總覽表用）。"""
        return list(self)

    def to_list_reverse(self):
        """從尾走到頭，測試 prev 指標是否正確。"""
        out = []
        node = self.tail
        while node:
            out.append(node.record)
            node = node.prev
        return out

    @classmethod
    def from_records(cls, records):
        dll = cls()
        for r in records:
            dll.append(r)
        return dll

    def filter_by_day(self, day):
        """取出某一天的預約，回傳新的 DoublyLinkedList。"""
        result = DoublyLinkedList()
        for r in self:
            if r.appointment_day == day:
                result.append(r)
        return result
