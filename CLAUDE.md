# CLAUDE.md

資料結構期末專題：門診預約管理與未到診風險分析系統。完整說明見 README.md。

## 溝通
- 用繁體中文回覆與撰寫註解
- 使用者在學資料結構，解釋時說明背後的知識點與時間複雜度

## 規則
- **課程要求自己實作資料結構**：core/ 裡不可改用 `heapq`、`bisect`、`collections.deque`、`sortedcontainers` 等現成結構。實驗的對照組可以用 `sorted()`
- 方法一律 `return`，不要在 core/ 裡 `print`（Streamlit 只能顯示回傳值）
- 搜尋類方法回傳 `(結果, 比較次數, 耗時ms)`
- 所有結構存同一份 `Record` 物件
- BST 用迴圈實作，不用遞迴（避免退化樹超過遞迴深度）
- 改動 core/ 後執行 `python -m pytest tests -q`，確認全部通過

## 進度（2026-11-20）
任務 0~8 全部完成，69 個測試通過。剩下：截圖、投影片、彩排（docs/plan.pdf 時程 12/7~12/9）。
以下是原本的任務說明，保留作為規格參考。

## 任務規格
1. 任務 6：experiments/ 三個實驗（資料量 1k／10k／50k／全部，每組跑 1000 次取平均，結果存 CSV）
   - 實驗一：線性 vs 二分 vs BST（再加依序插入的退化 BST）
   - 實驗二：Heap top_k vs sorted() 取前 K（K = 10、100、1000）
   - 實驗三：陣列刪除 vs Linked List 刪除；ArrayQueue vs LinkedQueue
2. 任務 7：core/system.py 的 AppointmentSystem
   - 包含 array、roster(DLL)、bst、heap、waitlist(Queue)
   - 方法：load_day、overview、search、top_risk、confirm_attend、cancel、refill、add、expected_noshow
   - 另外包含 patients（core/patient_index.py 的 PatientBST，key = patient_id）與 id_gen（core/booking.py 的 IdGenerator），開機時用全部資料建好
   - add(patient_id, age, scheduled_day, appointment_day, ...)：
     呼叫 core/booking.py 的 make_appointment(self.patients, self.id_gen, ...) 取得 record
     → node = roster.append(record) → bst.insert(record, node) → heap.push(record) → patients.insert(record)
     回傳 make_appointment 的結果 dict（含 level、is_new、history）
   - cancel：BST 找節點 → roster.delete_node(node.ll_node) → bst.delete → heap.remove → patients.remove_record
   - refill：waitlist.dequeue() 取出的 record 照 add 的 4 個插入步驟寫進 roster、bst、heap、patients
   - 新預約的 showed_up = None（還沒看診），validate_risk / build_calibration 只用載入的歷史資料
   - 每次新增／刪除都要同步 roster、bst、heap，寫 check_consistency() 並在測試中呼叫
3. 任務 8：app/ Streamlit 多頁面，系統物件存在 st.session_state，只呼叫 AppointmentSystem

## 整合測試情境（docs/plan.pdf 第 9 頁，對應 tests/test_system.py）
每個會改資料的操作之後都要呼叫 check_consistency()；錯誤情境要檢查訊息內容。
1. 載入某天，查 Top-3 → 三人風險由高到低（test_top3_order）
2. 取消第 1 名 → 三個結構都少一人，Top-1 換人（test_cancel_top1）
3. 取消後 refill → 人數恢復，候補少一人（test_cancel_then_refill）
4. 候補已空時 refill → 回傳提示，不會出錯（test_refill_empty）
5. 對 Top-3 的第 2 名 confirm_attend → 他從 Top-3 消失（test_confirm_attend）
6. 新增一筆高風險預約 → 出現在 Top-K（test_add_high_risk）
7. 取消不存在的 ID／同一筆取消兩次 → 回傳錯誤訊息（test_cancel_errors）
8. 連續取消＋遞補 50 次 → check_consistency 全部通過（test_cancel_refill_50_times，waitlist_size=60）

## 補充規則（2026-11-20）
- 完整規劃見 docs/plan.pdf，與本檔衝突時以本檔為準
- data/healthcare_noshows.csv 是原始資料，任何程式都不可修改；效能實驗只讀這份
- 即存 log 放在 data/logs/<看診日>.csv，每寫一筆都要 flush() + os.fsync()
- log 記錄操作後的完整 Record（含 appointment_id），不是只記操作名稱
- 重播 log 必須呼叫 AppointmentSystem 本身的方法，不可直接改結構或 CSV
- 實驗必須建立新的結構實例，不可使用 Streamlit session_state 裡的系統
- 每完成一個任務都要跑 python -m pytest tests -q，全部通過才算完成
## 手動修改紀錄（使用者親自改的，不要重做或覆蓋）