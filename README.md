# 門診預約管理與未到診風險分析系統

資料結構期末專題。用 106,982 筆真實門診資料，展示 BST、Max-Heap、Doubly Linked List、Queue 如何支援「找出最可能未到診的病患」與「取消後立即遞補」，並用效能實驗證明選對資料結構比較快。

## 目前進度

| 任務 | 內容 | 狀態 |
| --- | --- | --- |
| 0 | Record、讀檔清理、風險計分 | ✅ 完成 |
| 1 | Array（線性／二分搜尋、搬移刪除） | ✅ 完成 |
| 2 | BST | ✅ 完成 |
| 3 | Doubly Linked List | ✅ 完成 |
| 4 | Max-Heap | ✅ 完成 |
| 5 | Queue（Linked List 實作）+ ArrayQueue 對照組 | ✅ 完成 |
| 5.5 | 病患索引 PatientBST + 新增預約 `make_appointment`（任務 7 前置） | ✅ 完成 |
| 6 | 三個效能實驗 | ✅ 完成 |
| 7 | 整合 `AppointmentSystem` + 即存 log | ✅ 完成 |
| 8 | Streamlit 畫面（首頁 + 5 頁） | ✅ 完成 |

## 快速開始

以下指令都在 `noshow_system` 資料夾執行。

```bash
pip install -r requirements.txt
python -m pytest tests -q          # 69 個測試
streamlit run app/Home.py          # 開啟網頁系統
python -m experiments.run_all      # 重跑三個實驗（約 5 分鐘），結果存 experiments/results_exp*.csv
python demo_core.py                # 文字版示範
```

`core/` 只用 Python 標準函式庫；測試用 pytest，畫面用 Streamlit。

## 資料夾結構

```
noshow_system/
├── data/healthcare_noshows.csv   # 資料集（已清理版）
├── core/
│   ├── record.py        # 任務 0：Record、load_records、calc_risk、risk_level、校正表
│   ├── array_store.py   # 任務 1：ArrayStore
│   ├── bst.py           # 任務 2：BST
│   ├── linked_list.py   # 任務 3：DoublyLinkedList
│   ├── max_heap.py      # 任務 4：MaxHeap
│   ├── queue_ll.py      # 任務 5：LinkedQueue、ArrayQueue、pick_waitlist
│   ├── patient_index.py # PatientBST（key = patient_id，查病患舊紀錄）
│   ├── booking.py       # IdGenerator、make_appointment（產生新預約 Record）
│   └── system.py        # 任務 7：AppointmentSystem（整合所有結構 + 即存 log）
├── experiments/         # 任務 6
│   ├── common.py        # 抽樣、計時、CSV 格式
│   ├── exp1_search.py   # 實驗一：搜尋＋插入
│   ├── exp2_topk.py     # 實驗二：Top-K
│   ├── exp3_delete.py   # 實驗三：刪除＋Queue
│   ├── run_all.py       # 一次跑三個
│   └── results_exp*.csv # 實驗結果
├── app/                 # 任務 8：Streamlit
│   ├── Home.py          # 首頁：選日期／區域、總覽
│   ├── common.py        # 共用：session_state、樹狀圖
│   └── pages/           # 1 預約查詢、2 風險關懷名單、3 候補與超額預約、4 新增預約、5 效能分析
├── tests/
│   ├── test_core.py        # 任務 0~5
│   ├── test_booking.py     # PatientBST、新增預約
│   ├── test_experiments.py # 任務 6（小資料量）
│   ├── test_system.py      # 任務 7 整合情境 + log 重播
│   └── test_app.py         # 任務 8 各頁面（AppTest）
├── docs/plan.pdf        # 任務 0~8 規劃書
└── demo_core.py
```

執行網頁後，操作紀錄會即存到 `data/logs/<看診日>.csv`（每一筆都 flush + fsync）。
下次開啟、第一次載入那一天時會自動重播，恢復上次的狀態。想重來就刪掉 `data/logs/`。
原始資料 `data/healthcare_noshows.csv` 永遠不會被修改。

## 資料集說明

- 106,987 筆，刪除 5 筆等待天數為負數者，剩 106,982 筆
- **`Showed_up = True` 代表有到診**（跟原始 Kaggle 檔的 `No-show` 意思相反）
- `Date.diff` = 等待天數
- 整體未到診率 20.3%

## 風險計分（規則式）

| 因素 | 條件 → 分數 |
| --- | --- |
| 等待天數 | 0 天 → 0、1~7 → 30、8~14 → 40、15 以上 → 45 |
| 過往未到次數 | 0 → 0、1 → 20、2 以上 → 35 |
| 年齡 | 0~17 → 14、18~35 → 20、36~60 → 10、60 以上 → 0 |

滿分 100。燈號：紅 ≥ 70、黃 40~69、綠 < 40。

實際驗證：

| 燈號 | 人數 | 實際未到率 |
| --- | --- | --- |
| 紅 | 6,759 | 43.7% |
| 黃 | 59,123 | 27.5% |
| 綠 | 41,100 | 6.0% |

**簡訊不計分**：收到簡訊者的未到率（27.7%）反而高於沒收到的（16.7%），因為簡訊多半發給等比較久的人，是干擾因素。

**分數 ≠ 機率**：分數用來排序。要估「預期未到人數」（超額預約）時，請用 `build_calibration()` + `expected_noshow()`，把分數換成同分者的歷史實際未到率再加總。

## 資料結構一覽

| 結構 | 核心知識點 | 系統中的角色 | 對應實驗 |
| --- | --- | --- | --- |
| Array | 線性搜尋 O(n)、刪除要搬移 | 對照組 | 一、三 |
| BST | 左小右大、O(log n)、退化問題 | 依編號查詢 | 一 |
| PatientBST | 同一份資料依不同 key 建索引、節點掛一串資料 | 新增預約時查病患舊紀錄 | — |
| Doubly Linked List | 指標、O(1) 刪除 | 當日名單、退掛 | 三 |
| Max-Heap | 完全二元樹、sift-up／down、優先佇列 | 高風險 Top-K | 二 |
| Queue | FIFO、O(1) 進出 | 候補遞補 | — |

### 主要 API

| 類別 | 方法 |
| --- | --- |
| `ArrayStore` | `linear_search(id)`、`binary_search(id)`、`delete(id)`、`append`、`to_list` |
| `BST` | `insert(record, ll_node)`、`search(id)`、`delete(id)`、`inorder()`、`height()`、`search_path(id)` |
| `DoublyLinkedList` | `append(record)` → 節點、`delete_node(node)`、`filter_by_day(day)`、`to_list` |
| `MaxHeap` | `push`、`pop`、`peek`、`top_k(k)`、`update_key(id, risk)`、`remove(id)`、`build_heap`、`is_valid` |
| `LinkedQueue` | `enqueue`、`dequeue`、`peek`、`is_empty`、`to_list` |
| `PatientBST` | `insert(record)`、`search(patient_id)`、`past_noshow(patient_id, before_day)`、`remove_record(record)`、`height()` |
| `booking` | `IdGenerator(records).next()`、`make_appointment(patients, id_gen, patient_id=..., age=..., scheduled_day=..., appointment_day=...)` → dict |

搜尋類方法一律回傳 `(結果, 比較次數, 耗時ms)`。

## 實測數字（完整資料，demo_core.py）

| 項目 | 結果 |
| --- | --- |
| 線性搜尋 | 比較 53,492 次、約 3.1 ms |
| 二分搜尋 | 比較 16 次、約 0.01 ms |
| BST 搜尋 | 比較 23 次、約 0.007 ms |
| BST 樹高（打亂後插入） | 42（完全平衡約 17） |
| 2016-06-06 當日預估未到 | 957 人（實際 845 人） |

## 實驗結果摘要（全部 106,982 筆，experiments/results_exp*.csv）

| 實驗 | 方法 | 平均比較次數 | 平均搬移 | 平均耗時 |
| --- | --- | --- | --- | --- |
| 搜尋 | 線性 | 59,981 | — | 9.2 ms |
| 搜尋 | 二分 | 15.8 | — | 0.005 ms |
| 搜尋 | BST | 20.7 | — | 0.003 ms |
| 搜尋 | 退化 BST（1 萬筆） | 4,628 | — | 0.40 ms |
| 插入 | 排序陣列 | 16.8 | 99,613 | 16.7 ms |
| 插入 | BST | 21.7 | 0 | 0.003 ms |
| Top-10 | Heap `top_k` | 51 | — | 0.018 ms |
| Top-10 | `sorted()` 全排序 | 1,649,354 | — | 152 ms |
| Top-10 | 重建 heap 再 pop | 201,521 | — | 184 ms |
| 刪除 | 陣列 | 55,653 | 51,245 | 17.7 ms |
| 刪除 | BST + Linked List | 20.8 | 0 | 0.003 ms |
| dequeue | ArrayQueue | — | 106,482 | 0.013 ms |
| dequeue | LinkedQueue | — | 0 | 0.0003 ms |

- K 接近資料量時（例如 1,000 筆取前 1,000），`sorted()` 反而比 heap `top_k` 快：
  這時 top_k 等於要展開整棵 heap，而 `sorted()` 是 C 實作。Top-K 適合 K 遠小於 n 的情況。
- 很慢的組合在 3 秒內提早停止，實際重複次數記在 CSV 的 `runs` 欄。

## 已知注意事項

- BST 一定要**先打亂再插入**，依序插入的樹高會等於資料筆數
- Max-Heap 的 `update_key` 會直接修改 Record 的 `risk`，所有結構共用同一個 Record，數值會同步
- `top_k` 不會破壞原 heap
- 同一個 Record 不要同時放進兩個不同的 MaxHeap 又各自 `update_key`
- 新預約的 `showed_up = None`（還沒看診），`validate_risk`／`build_calibration` 只能用載入的歷史資料
