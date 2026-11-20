"""任務 0：共同基礎 —— Record 類別、讀檔清理、風險計分。

資料來源：data/healthcare_noshows.csv（已清理版 Kaggle Medical Appointment No Shows）
注意：Showed_up = True 代表「有到診」，跟原始檔的 No-show 意思相反。
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "healthcare_noshows.csv"


@dataclass
class Record:
    """一筆門診預約。所有資料結構存的都是這個物件。"""

    appointment_id: int       # 掛號編號（BST 的 key）
    patient_id: int           # 病患編號（算過往未到次數用）
    age: int
    gender: str
    wait_days: int            # 等待天數 = 看診日 - 預約日（CSV 的 Date.diff）
    scheduled_day: str        # 預約日 YYYY-MM-DD
    appointment_day: str      # 看診日 YYYY-MM-DD
    neighbourhood: str
    sms: bool                 # 有沒有收到簡訊（只顯示，不計分）
    chronic: bool             # 高血壓或糖尿病
    showed_up: bool | None    # 實際有沒有到診（驗證風險分數用）；None = 新預約、還沒看診
    past_noshow: int = 0      # 這次之前未到診幾次（load_records 會算）
    risk: float = 0.0         # 風險分數 0~100（load_records 會算）

    def __repr__(self):
        return f"Record(id={self.appointment_id}, risk={self.risk:.1f})"


# ---------------------------------------------------------------------------
# 讀檔與清理
# ---------------------------------------------------------------------------

def _to_bool(text: str) -> bool:
    return text.strip().upper() == "TRUE"


def load_records(path=DEFAULT_CSV, limit=None):
    """讀 CSV → 清理 → 算 past_noshow 和 risk，回傳 Record list。

    清理規則：
      - 刪除等待天數為負數的資料（預約日晚於看診日，不合理）
    limit：只取前 limit 筆（測試用），None 代表全部。
    """
    records = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            wait = int(row["Date.diff"])
            if wait < 0:
                continue
            records.append(Record(
                appointment_id=int(row["AppointmentID"]),
                patient_id=int(float(row["PatientId"])),
                age=int(row["Age"]),
                gender=row["Gender"],
                wait_days=wait,
                scheduled_day=row["ScheduledDay"],
                appointment_day=row["AppointmentDay"],
                neighbourhood=row["Neighbourhood"],
                sms=_to_bool(row["SMS_received"]),
                chronic=_to_bool(row["Hipertension"]) or _to_bool(row["Diabetes"]),
                showed_up=_to_bool(row["Showed_up"]),
            ))
            if limit is not None and len(records) >= limit:
                break

    compute_past_noshow(records)
    for r in records:
        r.risk = calc_risk(r)
    return records


def compute_past_noshow(records):
    """同一位病患依看診日排序，算出「這次之前」未到診的次數。"""
    order = sorted(records, key=lambda r: (r.patient_id, r.appointment_day, r.appointment_id))
    current_patient = None
    count = 0
    for r in order:
        if r.patient_id != current_patient:
            current_patient = r.patient_id
            count = 0
        r.past_noshow = count
        if not r.showed_up:
            count += 1


# ---------------------------------------------------------------------------
# 風險計分（規則式，不是機器學習）
# 權重依資料實際未到診率訂定：
#   等待 0 天 4.7% / 1-7 天 24.1% / 8-14 天 30.5% / 15 天以上 約 33%
#   過往未到 0 次 18.6% / 1 次 28.1% / 2 次以上 35.9%
#   18-35 歲 23.8% / 0-17 歲 22.5% / 36-60 歲 19.1% / 60 歲以上 15.2%
# 簡訊不計分：收到簡訊者未到率反而較高（簡訊多發給等很久的人），屬於干擾因素。
# ---------------------------------------------------------------------------

WAIT_POINTS = [(0, 0), (7, 30), (14, 40), (None, 45)]   # (上限天數, 分數)
PAST_POINTS = {0: 0, 1: 20}                              # 2 次以上 = 35
PAST_MAX = 35
AGE_POINTS = [(17, 14), (35, 20), (60, 10), (None, 0)]   # (上限年齡, 分數)


def calc_risk(record: Record) -> float:
    """回傳 0~100 的風險分數（滿分 = 等待 45 + 過往未到 35 + 年齡 20）。"""
    score = 0
    for upper, pts in WAIT_POINTS:
        if upper is None or record.wait_days <= upper:
            score += pts
            break
    score += PAST_POINTS.get(record.past_noshow, PAST_MAX)
    for upper, pts in AGE_POINTS:
        if upper is None or record.age <= upper:
            score += pts
            break
    return float(score)


def risk_level(score: float) -> str:
    """燈號：紅 ≥ 70、黃 40~69、綠 < 40。"""
    if score >= 70:
        return "紅"
    if score >= 40:
        return "黃"
    return "綠"


def validate_risk(records):
    """任務 0-6：各燈號的實際未到診率，紅應明顯高於綠。回傳 {燈號: (人數, 未到率)}。"""
    groups = {"紅": [0, 0], "黃": [0, 0], "綠": [0, 0]}
    for r in records:
        g = groups[risk_level(r.risk)]
        g[0] += 1
        g[1] += (not r.showed_up)
    return {k: (n, (miss / n if n else 0.0)) for k, (n, miss) in groups.items()}


def build_calibration(records):
    """風險分數 → 實際未到率 的對照表 {score: rate}。

    風險分數只適合「排序」，不是機率。要估「預期未到人數」（超額預約）時，
    用這張表把每個人的分數換成歷史上同分者的實際未到率，再加總。
    """
    stats = {}
    for r in records:
        n, miss = stats.get(r.risk, (0, 0))
        stats[r.risk] = (n + 1, miss + (not r.showed_up))
    return {score: miss / n for score, (n, miss) in stats.items()}


def expected_noshow(records, calibration):
    """預期未到人數 = 每個人「同分者實際未到率」的加總。查不到的分數用整體平均 20%。"""
    return sum(calibration.get(r.risk, 0.2) for r in records)


if __name__ == "__main__":
    import time
    t = time.perf_counter()
    recs = load_records()
    print(f"載入 {len(recs)} 筆，耗時 {time.perf_counter() - t:.2f} 秒")
    for level, (n, rate) in validate_risk(recs).items():
        print(f"{level}燈：{n:6d} 人，實際未到率 {rate:.1%}")
