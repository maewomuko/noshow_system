"""新增預約：叫出病患舊紀錄 → 算風險 → 產生新 Record。

這裡只負責「產生一筆算好風險的 Record」，
寫進 Linked List / BST / Heap 屬於任務 7 的 AppointmentSystem.add()。

流程：
  1. 等待天數 = 看診日 - 預約日
  2. 用 PatientBST 叫出舊紀錄，算過往未到次數（新病患 = 0）
  3. calc_risk() 算分數、risk_level() 給燈號
"""

from datetime import date

from core.record import Record, calc_risk, risk_level


class IdGenerator:
    """產生不重複的掛號編號：目前最大編號 + 1。"""

    def __init__(self, records):
        self._next = max((r.appointment_id for r in records), default=0) + 1

    def next(self):
        nid = self._next
        self._next += 1
        return nid

    def reserve(self, used_id):
        """標記 used_id 已被使用，之後不會再產生（重播 log 時用）。"""
        if used_id >= self._next:
            self._next = used_id + 1


def wait_days_between(scheduled_day: str, appointment_day: str) -> int:
    """兩個 YYYY-MM-DD 相差幾天。"""
    return (date.fromisoformat(appointment_day) - date.fromisoformat(scheduled_day)).days


def make_appointment(patient_index, id_gen, *, patient_id, age, scheduled_day, appointment_day,
                     gender="F", neighbourhood="", sms=False, chronic=False):
    """產生新預約的 Record（還沒寫進任何結構）。

    回傳 dict：
      record      新的 Record（showed_up = None，代表還沒看診）
      is_new      是否為新病患（查不到舊紀錄）
      history     該病患舊預約筆數
      level       燈號
      comparisons 在病患索引中查詢的比較次數
      ms          查詢耗時
    錯誤（看診日早於預約日、年齡不合理）會丟出 ValueError。
    """
    wait = wait_days_between(scheduled_day, appointment_day)
    if wait < 0:
        raise ValueError("看診日不能早於預約日")
    if not 0 <= age <= 120:
        raise ValueError("年齡不合理")

    history, comparisons, ms = patient_index.search(patient_id)
    past = patient_index.past_noshow(patient_id, appointment_day)

    record = Record(
        appointment_id=id_gen.next(),
        patient_id=patient_id,
        age=age,
        gender=gender,
        wait_days=wait,
        scheduled_day=scheduled_day,
        appointment_day=appointment_day,
        neighbourhood=neighbourhood,
        sms=sms,
        chronic=chronic,
        showed_up=None,          # 未來的預約，還不知道有沒有來
        past_noshow=past,
    )
    record.risk = calc_risk(record)

    return {
        "record": record,
        "is_new": history is None,
        "history": len(history) if history else 0,
        "level": risk_level(record.risk),
        "comparisons": comparisons,
        "ms": ms,
    }
