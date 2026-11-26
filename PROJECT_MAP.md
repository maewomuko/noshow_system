# PROJECT_MAP：專案架構與模組說明

> 分析日期：2026-11-26｜依實際程式碼整理（commit `32c1234` + 未提交的 CLAUDE.md、experiments/common.py 小改動）
> 本檔只描述現況，不含修改建議（建議見 UI_REDESIGN_PLAN.md、ISSUES.md）。

## 1. 一張圖看懂

```
                 data/healthcare_noshows.csv（唯讀，106,987 列 → 清理後 106,982 筆）
                        │ load_records()：刪等待天數 < 0 的 5 筆、算 past_noshow、算 risk
          ┌─────────────┴──────────────┐
          ▼                            ▼
  上半：預約管理系統                 下半：效能實驗（彼此獨立）
  core/system.py                     experiments/exp1~3 → results_exp1~3.csv
  AppointmentSystem（總管）                     │
     │  只被 app/ 呼叫                           │ 只讀 CSV
     ▼                                           ▼
  app/Home.py + pages/1~4 ◄── st.session_state["system"]     app/pages/5_效能分析.py
     │
     └─ 每次修改操作 → data/logs/<看診日>.csv（追加 + flush + fsync）
        第一次載入某天 → 重播 log（呼叫系統自己的方法）
```

## 2. 資料夾與檔案

| 路徑 | 行數 | 角色 |
|---|---|---|
| `data/healthcare_noshows.csv` | — | 原始資料（Kaggle Medical Appointment No Shows，已改名 `Showed_up`）。程式只讀 |
| `data/logs/<日期>.csv` | — | 即存 log（被 `.gitignore` 排除）。目前有 4 個檔，共 52 筆操作 |
| `core/record.py` | 166 | `Record` dataclass、`load_records`、`calc_risk`、`risk_level`、`validate_risk`、`build_calibration`、`expected_noshow` |
| `core/array_store.py` | 87 | `ArrayStore`：線性搜尋、二分搜尋、手動搬移刪除（對照組） |
| `core/bst.py` | 145 | `BST`（key = appointment_id，迴圈實作），節點存 `ll_node` |
| `core/linked_list.py` | 96 | `DoublyLinkedList`：`append` 回傳節點、`delete_node` O(1) |
| `core/max_heap.py` | 207 | `MaxHeap`：陣列 + `pos` 字典；`top_k` 用內部 `_IndexHeap` 輔助堆，不破壞原 heap |
| `core/queue_ll.py` | 104 | `LinkedQueue`（候補用）、`ArrayQueue`（對照組，`pop(0)`）、`pick_waitlist` |
| `core/patient_index.py` | 131 | `PatientBST`（key = patient_id），節點掛該病患所有 Record |
| `core/booking.py` | 84 | `IdGenerator`、`wait_days_between`、`make_appointment`（只產生 Record，不寫入結構） |
| `core/system.py` | 395 | `AppointmentSystem`：整合所有結構 + log 寫入/重播 |
| `app/common.py` | 91 | `get_system()`（session_state）、燈號顏色、`bst_path_dot`、`heap_dot`、`structure_box` |
| `app/Home.py` | 79 | 首頁 |
| `app/pages/1~5_*.py` | 60~91 | 五個功能頁 |
| `experiments/common.py` | 113 | 抽樣、`measure()`、CSV 欄位、`run_and_save` |
| `experiments/exp1_search.py` | 136 | 實驗一：搜尋＋插入 |
| `experiments/exp2_topk.py` | 118 | 實驗二：Top-K |
| `experiments/exp3_delete.py` | 89 | 實驗三：刪除＋Queue |
| `experiments/run_all.py` | 17 | 一次跑三個（約 5 分鐘） |
| `tests/*.py` | 769 | 69 個測試（見 CURRENT_STATE.md） |
| `demo_core.py` | 77 | 文字版示範（README「實測數字」的來源，單次測量） |
| `docs/plan.pdf` | — | 11/19 原始規劃（進度已過時） |
| `docs/作品理解手冊.pdf` | — | 11/20 給組員看的說明手冊（20 頁） |
| `docs/方案評估_三版.pdf` | — | 11/20 報告前三版方案與覆盤（8 頁） |
| `.vscode/tasks.json` | — | VS Code 任務「啟動門診系統」（Streamlit, port 8501） |
| `.claude/skills/noshow-dev/SKILL.md` | — | 本專案 skill |
| `requirements.txt` | 3 | `pytest`、`streamlit`、`graphviz`（未鎖版本；pandas 由 streamlit 帶入） |

執行環境（本機實測）：Python 3.13.16、Streamlit 1.67.0、pandas 3.1.1。

## 3. Record：所有結構共用的同一份物件

| 欄位 | 來源 | 用途 |
|---|---|---|
| `appointment_id` | AppointmentID | BST key、Heap `pos` key |
| `patient_id` | PatientId | PatientBST key |
| `age`、`gender` | Age、Gender | 年齡計分 |
| `wait_days` | Date.diff | 等待天數計分 |
| `scheduled_day`、`appointment_day` | — | 選日期 |
| `neighbourhood` | Neighbourhood | 首頁篩區域 |
| `sms`、`chronic` | SMS_received、Hipertension/Diabetes | **只顯示，不計分** |
| `showed_up` | Showed_up | 驗證；新預約為 `None` |
| `past_noshow` | 計算 | 同一病患在本次之前未到次數 |
| `risk` | 計算 | 0~100；Heap 排序依據 |

風險計分（`core/record.py` `calc_risk`，規則式）：等待天數（0/30/40/45）＋過往未到（0/20/35）＋年齡（14/20/10/0）。燈號：紅 ≥ 70、黃 40~69、綠 < 40。

## 4. AppointmentSystem 內部組成

| 屬性 | 結構 | 範圍 | 建立時機 |
|---|---|---|---|
| `all_records` | Python list | 全部歷史資料 | 開機 |
| `calibration` | dict（分數 → 歷史未到率） | 全部歷史資料 | 開機 |
| `patients` | PatientBST | 全部資料（打亂後插入，seed 42） | 開機 |
| `id_gen` | IdGenerator | 最大編號 + 1；開機掃 log 保留已用編號 | 開機 |
| `roster` | DoublyLinkedList | 當日（依風險降冪串起） | `load_day` |
| `bst` | BST | 當日（打亂後插入），節點存 `ll_node` | `load_day` |
| `heap` | MaxHeap | 當日（`build_heap` O(n)） | `load_day` |
| `array` | ArrayStore | 當日（對照組，給線性搜尋比較） | `load_day` |
| `waitlist` | LinkedQueue | 從隔天抽 5 位，建「今天現場掛號」新 Record | `load_day` |

內部狀態：`_by_day`（日期 → 當日歷史 Record）、`_added`（本次新增）、`_cancelled`（已取消編號）、`_replayed`（已重播日期）、`_replaying`（重播中不寫 log）。

### 方法與呼叫的結構

| 方法 | 動作順序 | 複雜度（主要部分） |
|---|---|---|
| `load_day(day, area, waitlist_size=5)` | 第一次：以全區重建 → 重播 log；再依區域重建 | O(n) |
| `overview()` | 走訪 roster | O(n) |
| `search(id)` | `bst.search` | O(log n) 平均 |
| `compare_search(id)` | BST 搜尋 + `array.linear_search` + `search_path` + `height` | O(log n) + O(n) |
| `top_risk(k)` | `heap.top_k` | O(K log K) |
| `heap_preview(levels=4)` | heap 陣列前 15 格 | O(1) |
| `expected_noshow()` | 每人查校正表加總 | O(n) |
| `level_counts()` | 走訪 roster | O(n) |
| `patient_history(pid)` | `patients.search` | O(log P) |
| `confirm_attend(id, new_risk=0)` | `heap` 查有無 → `bst.search` → `heap.update_key` → log | O(log n) |
| `cancel(id)` | `bst.search` → `roster.delete_node(ll_node)` → `bst.delete` → `heap.remove` → `array.delete` → `patients.remove_record` → log | O(log n)，array 對照組 O(n) |
| `add(...)` | `make_appointment` → `add_record` → log | O(log n) |
| `add_record(r)` | `roster.append` → `bst.insert(r, node)` → `heap.push` → `array.append` → `patients.insert` → `id_gen.reserve` | O(log n) |
| `refill()` | `waitlist.dequeue` → `add_record` → log | O(log n) |
| `check_consistency()` | 見下 | O(n log n) |

`check_consistency()` 實際檢查：roster/bst/heap/array 人數相同；roster 正反向一致；每筆在 BST 找得到且 `node.record is r`、`ll_node.record is r`；在 heap 中；在 PatientBST 該病患 list 中；`heap.is_valid()`；BST 中序遞增。**不檢查 waitlist、不檢查 array 內容順序。**

### Log 格式（`data/logs/<看診日>.csv`）

欄位：`action` + Record 全部 13 個欄位。`action ∈ {add, cancel, confirm, refill}`。沒有時間戳記。重播時：`cancel` → `cancel()`、`confirm` → `confirm_attend(id, risk)`、`add` → `add_record()`、`refill` → `refill(replay_record=…)`。

## 5. Streamlit 頁面與呼叫關係

所有頁面用 `get_system()` 取得 `st.session_state["system"]`；第一次進入時 `AppointmentSystem.load()` + `load_day("2016-06-06")`。log 目錄可用環境變數 `NOSHOW_LOG_DIR` 改寫（測試用）。

| 頁面（檔案） | 讀取 | 修改 | 視覺化 |
|---|---|---|---|
| 首頁 `Home.py` | `days`、`neighbourhoods`、`level_counts`、`expected_noshow`、`overview`、`validate_risk(all_records)` | `load_day` | 5 個 metric、名單表格、燈號未到率長條圖 |
| 1 預約查詢 | `roster.to_list`、`compare_search` | — | metric、BST 搜尋路徑 graphviz |
| 2 風險關懷名單 | `top_risk(k)`、`heap_preview(4)` | `confirm_attend`、`cancel`（按鈕 `on_click`） | 前 K 名逐列按鈕、Heap 前 4 層 graphviz |
| 3 候補與超額預約 | `expected_noshow`、`waitlist.to_list`、`top_risk(1)` | `refill`、`cancel` | metric、候補表格 |
| 4 新增預約 | `all_records`（找示範病患）、`top_risk(n)`、`patient_history` | `add` | metric、病患歷史表格 |
| 5 效能分析 | `experiments/results_exp1~3.csv` | — | `st.line_chart`（可切縱軸、log₁₀） |

註：頁面直接讀 `system.roster`、`system.waitlist`、`system.all_records` 等屬性（唯讀），修改一律透過系統方法。

## 6. 效能實驗

| 設定 | 值（`experiments/common.py`） |
|---|---|
| 資料量 `SIZES` | 1,000 / 10,000 / 50,000 / 全部（106,982） |
| 抽樣 | `sample(records, n, seed=0)`：固定 seed，同一份樣本 |
| 每組重複 | 最多 `MAX_RUNS=1000`；超過 `TIME_BUDGET_S=3.0` 秒且已跑 `MIN_RUNS=5` 次就停 |
| 計時 | `time.perf_counter()`，只算操作本身 |
| CSV 欄位 | experiment, method, n, k, runs, avg_ms, avg_comparisons, avg_moves |

| 實驗 | experiment 值 | method |
|---|---|---|
| 一 | `search` | linear、binary、bst、bst_degenerate（只到 1 萬筆） |
| 一 | `insert` | sorted_array、bst |
| 二 | `topk`（K = 10/100/1000） | heap_top_k、sorted、rebuild_pop |
| 三 | `delete` | array、bst_linked_list |
| 三 | `queue` | array_queue、linked_queue |

## 7. 測試

| 檔案 | 測試數 | 範圍 |
|---|---|---|
| `test_core.py` | 28（含參數化） | Record、Array、BST、DLL、Heap、Queue |
| `test_booking.py` | 9 | PatientBST、make_appointment |
| `test_experiments.py` | 5 | 小資料量跑三個實驗 |
| `test_system.py` | 17 | CLAUDE.md 8 個整合情境 + log 重播 + 原始 CSV 不變 |
| `test_app.py` | 10（含參數化 6 頁） | AppTest 冒煙測試 + 首頁載入、確認/取消、遞補、新增 |
| 合計 | **69** | 2026-11-26 實測全部通過（48.4 秒） |
