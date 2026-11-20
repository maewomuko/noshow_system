"""任務 2：BST —— 依掛號編號查詢／報到。

知識點：左子樹 < 節點 < 右子樹；搜尋／插入／刪除平均 O(log n)；
       刪除三種情況；中序走訪得到排序結果；依序插入會退化成鏈狀 O(n)。
用在：畫面一（查詢、報到）、畫面四（新增）、實驗一。

全部用迴圈實作（不用遞迴），避免退化樹超過 Python 遞迴深度上限。
"""

import time


class BSTNode:
    __slots__ = ("key", "record", "ll_node", "left", "right")

    def __init__(self, record, ll_node=None):
        self.key = record.appointment_id
        self.record = record
        self.ll_node = ll_node      # 指向 Doubly Linked List 的節點，刪除時 O(1) 取得
        self.left = None
        self.right = None


class BST:
    def __init__(self):
        self.root = None
        self._size = 0

    def __len__(self):
        return self._size

    def insert(self, record, ll_node=None):
        """插入一筆，O(log n)（平均）。key 重複則更新資料，回傳 False。"""
        new = BSTNode(record, ll_node)
        if self.root is None:
            self.root = new
            self._size += 1
            return True
        node = self.root
        while True:
            if new.key == node.key:          # 重複：更新而不新增
                node.record = record
                node.ll_node = ll_node
                return False
            if new.key < node.key:
                if node.left is None:
                    node.left = new
                    break
                node = node.left
            else:
                if node.right is None:
                    node.right = new
                    break
                node = node.right
        self._size += 1
        return True

    def search(self, appointment_id):
        """回傳 (BSTNode 或 None, 比較次數, 耗時 ms)。"""
        start = time.perf_counter()
        comparisons = 0
        node = self.root
        while node:
            comparisons += 1
            if appointment_id == node.key:
                return node, comparisons, (time.perf_counter() - start) * 1000
            node = node.left if appointment_id < node.key else node.right
        return None, comparisons, (time.perf_counter() - start) * 1000

    def search_path(self, appointment_id):
        """回傳搜尋經過的 key list（畫面上畫路徑用）。"""
        path = []
        node = self.root
        while node:
            path.append(node.key)
            if appointment_id == node.key:
                break
            node = node.left if appointment_id < node.key else node.right
        return path

    def delete(self, appointment_id):
        """刪除指定 key，回傳被刪的 BSTNode（找不到回傳 None）。

        三種情況：
          1. 沒有子節點 → 直接移除
          2. 一個子節點 → 讓子節點接上父節點
          3. 兩個子節點 → 找中序後繼（右子樹最小值）取代，再刪掉後繼
        """
        parent, node = None, self.root
        while node and node.key != appointment_id:
            parent = node
            node = node.left if appointment_id < node.key else node.right
        if node is None:
            return None

        removed = BSTNode(node.record, node.ll_node)   # 保留被刪資料的副本供回傳

        # 情況 3：兩個子節點 → 用中序後繼的資料覆蓋，轉成刪除後繼（後繼最多一個右子）
        if node.left and node.right:
            succ_parent, succ = node, node.right
            while succ.left:
                succ_parent, succ = succ, succ.left
            node.key, node.record, node.ll_node = succ.key, succ.record, succ.ll_node
            parent, node = succ_parent, succ

        # 情況 1、2：node 最多一個子節點
        child = node.left if node.left else node.right
        if parent is None:
            self.root = child
        elif parent.left is node:
            parent.left = child
        else:
            parent.right = child

        self._size -= 1
        return removed

    def inorder(self):
        """中序走訪（迴圈 + 堆疊），回傳依 key 遞增的 Record list。"""
        out, stack, node = [], [], self.root
        while stack or node:
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            out.append(node.record)
            node = node.right
        return out

    def height(self):
        """樹高（只有根 = 1，空樹 = 0），用 BFS 逐層計算。"""
        if self.root is None:
            return 0
        level, h = [self.root], 0
        while level:
            h += 1
            level = [c for n in level for c in (n.left, n.right) if c]
        return h

    @classmethod
    def from_records(cls, records):
        tree = cls()
        for r in records:
            tree.insert(r)
        return tree
