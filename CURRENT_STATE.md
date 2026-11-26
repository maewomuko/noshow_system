# CURRENT_STATE：目前系統功能及完成狀態

> 分析日期：2026-11-26｜距離 12/10 報告 14 天｜plan.pdf 時程：12/2~12/6 Streamlit、12/7~12/9 彩排
> 所有數字都由本次重新執行程式或讀 CSV 取得，來源標在每一列。

## 1. 總結

| 面向 | 狀態 | 依據 |
|---|---|---|
| 核心資料結構（任務 0~5、5.5） | ✅ 完成 | `core/` 9 個模組 |
| 效能實驗（任務 6） | ✅ 完成，CSV 已產生 | `experiments/results_exp1~3.csv` |
| 系統整合 + 即存 log（任務 7） | ✅ 完成 | `core/system.py` |
| Streamlit 6 頁（任務 8） | ✅ 可用，視覺為 Streamlit 預設淺色 | `app/` |
| 自動測試 | ✅ **69 passed（48.4 秒）** | 2026-11-26 `python -m pytest tests -q` |
| 簡報 | ⚠️ Canva 已有 15 頁草稿「門診預約風險分析」，多處與程式不符 | 見 ISSUES.md「A. 簡報」 |
| Demo 環境 | ⚠️ `data/logs/` 留有 52 筆測試操作，開機會自動重播 | 見 ISSUES.md R1 |
| 版本控制 | git 已建立，1 個 commit；工作區有未提交改動 | `git status` |

## 2. 功能清單（對照程式）

| 功能 | 系統方法 | 頁面 | 結構 | 狀態 |
|---|---|---|---|---|
| 選日期／區域 | `load_day` | 首頁 | 重建全部當日結構 | ✅ |
| 當日總覽、燈號統計 | `overview`、`level_counts` | 首頁 | DLL 走訪 | ✅ |
| 風險分數驗證 | `validate_risk(all_records)` | 首頁 | — | ✅ |
| 預估未到（超額預約） | `expected_noshow` | 首頁、頁 3 | 校正表 dict | ✅ |
| 依編號查詢 + 線性比較 + 路徑圖 | `compare_search` | 頁 1 | BST、Array | ✅ |
| 前 K 名高風險 | `top_risk` | 頁 2 | Max-Heap | ✅（K 上限 30） |
| 確認會到 | `confirm_attend` | 頁 2 | Heap `update_key` | ✅ |
| 取消預約 | `cancel` | 頁 2、頁 3 | BST → DLL → BST → Heap → Array → PatientBST | ✅ |
| 候補遞補 | `refill` | 頁 3 | LinkedQueue + 全部插入 | ✅ |
| 新增預約 | `add` | 頁 4 | PatientBST 查歷史 + 全部插入 | ✅ |
| 病患歷史 | `patient_history` | 頁 4 | PatientBST | ✅ |
| 效能圖表 | 讀 CSV | 頁 5 | — | ✅ |
| 即存 log + 重播 | `_log`、`_replay_log` | 全部修改操作 | CSV 追加 | ✅ |
| 一致性檢查 | `check_consistency` | **只在測試中呼叫，網頁沒有** | — | ✅（測試） |
| 重置當日／清除 log | — | — | — | ❌ 沒有（README 說手動刪 `data/logs/`） |

## 3. 資料驗證（本次重新計算）

| 項目 | 文件寫的 | 實測 | 一致？ |
|---|---|---|---|
| 清理後筆數 | 106,982 | 106,982 | ✅ |
| 看診日數 | 27 | 27 | ✅ |
| 整體未到率 | 20.3% | 20.26% | ✅ |
| 紅／黃／綠 人數 | 6,759 / 59,123 / 41,100 | 同 | ✅ |
| 紅／黃／綠 未到率 | 43.7% / 27.5% / 6.0% | 43.69% / 27.51% / 5.98% | ✅ |
| 簡訊：有／無 未到率 | 27.7% / 16.7% | 27.7% / 16.7% | ✅ |
| 2016-06-06 人數 | 4,528 | 4,528 | ✅ |
| 2016-06-06 預估／實際未到 | 957 / 845 | 956.6 / 845 | ✅ |
| 全資料 BST 樹高（seed 42） | 42 | 42 | ✅ |
| 2016-06-06 當日 BST 樹高 | — | 29（4,528 筆，完全平衡約 13） | — |

## 4. 實驗結果（全部 106,982 筆，`runs` = 實際重複次數）

| 實驗 | method | runs | avg_ms | avg_comparisons | avg_moves |
|---|---|---|---|---|---|
| 搜尋 | linear | 325 | 9.245 | 59,981 | 0 |
| 搜尋 | binary | 1000 | 0.0052 | 15.8 | 0 |
| 搜尋 | bst | 1000 | 0.0031 | 20.7 | 0 |
| 搜尋（n=10,000） | bst_degenerate | 1000 | 0.402 | 4,628 | 0 |
| 插入 | sorted_array | 180 | 16.68 | 16.8 | 99,613 |
| 插入 | bst | 1000 | 0.0030 | 21.7 | 0 |
| Top-10 | heap_top_k | 1000 | 0.018 | 51 | — |
| Top-10 | sorted | **20** | 151.8 | 1,649,354 | — |
| Top-10 | rebuild_pop | **17** | 184.0 | 201,521 | — |
| 刪除 | array | 170 | 17.71 | 55,653 | 51,245 |
| 刪除 | bst_linked_list | 1000 | 0.0032 | 20.8 | 0 |
| dequeue | array_queue | 1000 | 0.0126 | 0 | 106,482 |
| dequeue | linked_queue | 1000 | 0.00026 | 0 | 0 |

不符合直覺、必須在報告中呈現的結果（實驗二，n = 1,000）：

| K | heap_top_k ms / 比較 | sorted ms / 比較 | 結論 |
|---|---|---|---|
| 100 | 0.408 / 1,218 | 0.309 / 8,677 | **耗時 sorted 較快**，比較次數 heap 較少 |
| 1000 | 4.980 / 14,580 | 0.457 / 8,677 | **耗時與比較次數都是 sorted 較好** |

n ≥ 10,000 時，所有 K 值下 heap_top_k 耗時都較短。

## 5. Session State、Log、原始 CSV

| 項目 | 現況 |
|---|---|
| Session State | `app/common.py:get_system()`：`st.session_state["system"]` 不存在才建立；之後每次 rerun 都拿同一物件 → 操作不會被重置 ✅ |
| 跨瀏覽器分頁 | 每個 Streamlit session 各自建立一個系統（各自讀 CSV、各自 id_gen），但共用同一個 `data/logs/` 資料夾 |
| Log 寫入 | `open(path, "a")` + `flush()` + `os.fsync()`；記錄操作後的完整 Record ✅ |
| Log 重播 | 每個日期第一次 `load_day` 時；呼叫系統本身的方法 ✅；重播中不寫 log ✅ |
| 目前 log 內容 | 2016-05-24：4 筆（add 1、refill 3）、2016-05-30：4 筆（add 2、refill 2）、**2016-06-06：43 筆（add 23、refill 12、cancel 4、confirm 4）**、2016-06-08：1 筆（add 1） |
| 原始 CSV | 只有 `open(..., encoding="utf-8")` 讀取；`test_original_csv_untouched` 驗證不被修改 ✅ |

## 6. 文件狀態

| 文件 | 日期 | 狀態 |
|---|---|---|
| `CLAUDE.md` | 11/20 | 進度正確（任務 0~8 完成、69 測試）；「手動修改紀錄」標題下目前是空的 |
| `README.md` | — | 數字與 CSV 一致；「實測數字」是 `demo_core.py` 單次測量，與 CSV 平均值不同 |
| `docs/plan.pdf` | 11/19 | 進度過時（寫 37 個測試、任務 6~8 待做） |
| `docs/作品理解手冊.pdf` | 11/20 | 大致與程式一致，少數說法需修正（見 ISSUES.md） |
| `docs/方案評估_三版.pdf` | 11/20 | 提出的「區域名稱亂碼」經查證不成立；「專案沒有 git」已過時 |
| Canva「門診預約風險分析」 | 11/25 | 15 頁，多處與程式不符（見 ISSUES.md） |
