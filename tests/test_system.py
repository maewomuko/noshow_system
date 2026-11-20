"""任務 7：AppointmentSystem 整合測試（docs/plan.pdf 第 9 頁的情境 + 即存 log）。"""

import hashlib
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.record import DEFAULT_CSV, load_records, risk_level
from core.system import AppointmentSystem

DAY = "2016-06-06"


@pytest.fixture(scope="module")
def records():
    return load_records()


@pytest.fixture(scope="module")
def small_area(records):
    """挑一個 2016-06-06 人數在 20~100 之間的區域，Demo 比較像一間診間。"""
    sys_ = AppointmentSystem(records, log_dir=None)
    for name, count in sys_.neighbourhoods(DAY):
        if 20 <= count <= 100:
            return name
    pytest.skip("找不到合適的區域")


@pytest.fixture
def system(records, small_area, tmp_path):
    # 每個測試重新讀檔，避免 confirm_attend 改到共用 Record 的風險分數
    s = AppointmentSystem(load_records(), log_dir=tmp_path / "logs")
    s.load_day(DAY, small_area)
    s.check_consistency()
    return s


def ids(records):
    return [r.appointment_id for r in records]


def test_load_day(system, small_area):
    assert 20 <= len(system.roster) <= 100
    assert all(r.appointment_day == DAY and r.neighbourhood == small_area for r in system.roster)
    assert len(system.waitlist) == 5
    assert sum(system.level_counts().values()) == len(system.roster)
    assert system.check_consistency()


def test_full_day(records, tmp_path):
    s = AppointmentSystem(load_records(), log_dir=tmp_path)
    s.load_day(DAY)
    assert len(s.roster) == 4528
    assert s.check_consistency()
    assert 900 < s.expected_noshow() < 1000          # README：約 957 人


# ---------------- plan.pdf 第 9 頁的 8 個整合情境 ----------------
# 每個「會改資料的操作」之後都立刻 check_consistency()

def test_top3_order(system):
    """情境 1：載入某天，查 Top-3 → 三人風險由高到低。"""
    top = system.top_risk(3)
    risks = [r.risk for r in top]
    assert risks == sorted(risks, reverse=True)
    assert top[0].risk == max(r.risk for r in system.roster)
    assert system.check_consistency()                # top_k 不能破壞 heap


def test_cancel_top1(system):
    """情境 2：取消第 1 名 → 三個結構都少一人，Top-1 換人。"""
    n = len(system.roster)
    first = system.top_risk(1)[0]
    out = system.cancel(first.appointment_id)
    assert system.check_consistency()
    assert out["ok"]
    assert len(system.roster) == len(system.bst) == len(system.heap) == n - 1
    assert system.top_risk(1)[0].appointment_id != first.appointment_id
    assert system.search(first.appointment_id)[0] is None


def test_cancel_then_refill(system):
    """情境 3：取消後 refill → 人數恢復，候補少一人。"""
    n, w = len(system.roster), len(system.waitlist)
    system.cancel(system.top_risk(1)[0].appointment_id)
    assert system.check_consistency()
    out = system.refill()
    assert system.check_consistency()
    assert out["ok"] and len(system.roster) == n and len(system.waitlist) == w - 1
    assert system.search(out["record"].appointment_id)[0] is out["record"]


def test_refill_empty(system):
    """情境 4：候補已空時 refill → 回傳提示，不會出錯。"""
    while not system.waitlist.is_empty():
        assert system.refill()["ok"]
        assert system.check_consistency()
    n = len(system.roster)
    out = system.refill()
    assert system.check_consistency()
    assert out["ok"] is False and out["message"] == "候補隊伍是空的"
    assert len(system.roster) == n                   # 失敗的操作不能改到資料


def test_confirm_attend(system):
    """情境 5：對 Top-3 的第 2 名 confirm_attend → 他從 Top-3 消失。"""
    second = system.top_risk(3)[1]
    out = system.confirm_attend(second.appointment_id)
    assert system.check_consistency()
    assert out["ok"] and second.risk == 0.0
    assert second.appointment_id not in ids(system.top_risk(3))

    n = len(system.roster)
    bad = system.confirm_attend(-1)
    assert system.check_consistency()
    assert bad["ok"] is False and "找不到掛號編號 -1" in bad["message"]
    assert len(system.roster) == n


def test_add_high_risk(system, records):
    """情境 6：新增一筆高風險預約 → 出現在 Top-K。"""
    # 找一位以前至少沒來 2 次的病患，預約等很久 → 一定是高風險
    pid = next(r.patient_id for r in records if r.past_noshow >= 2 and r.appointment_day < DAY)
    out = system.add(patient_id=pid, age=25, scheduled_day="2016-04-20")
    assert system.check_consistency()
    rec = out["record"]
    assert not out["is_new"] and out["level"] == "紅" and rec.showed_up is None
    assert rec.appointment_id in ids(system.top_risk(len(system.roster)))
    assert rec.appointment_id in ids(system.top_risk(5))


def test_add_new_patient_and_errors(system):
    """情境 6 補充：新病患預約，以及輸入不合理時丟 ValueError 且不改資料。"""
    out = system.add(patient_id=1, age=70, scheduled_day=DAY)
    assert system.check_consistency()
    assert out["is_new"] and out["level"] == "綠"
    n = len(system.roster)
    with pytest.raises(ValueError, match="看診日不能早於預約日"):
        system.add(patient_id=1, age=30, scheduled_day="2016-07-01")
    assert system.check_consistency() and len(system.roster) == n
    with pytest.raises(ValueError, match="只能新增目前載入日期"):
        system.add(patient_id=1, age=30, scheduled_day=DAY, appointment_day="2016-06-07")
    assert system.check_consistency() and len(system.roster) == n


def test_cancel_errors(system):
    """情境 7：取消不存在的 ID／同一筆取消兩次 → 回傳錯誤訊息。"""
    n = len(system.roster)
    first = system.top_risk(1)[0].appointment_id

    out = system.cancel(999_999_999)
    assert system.check_consistency()
    assert out["ok"] is False and "找不到掛號編號 999999999" in out["message"]
    assert len(system.roster) == n

    assert system.cancel(first)["ok"] is True
    assert system.check_consistency()

    out = system.cancel(first)                                            # 取消兩次
    assert system.check_consistency()
    assert out["ok"] is False
    assert f"找不到掛號編號 {first}" in out["message"] and "可能已取消" in out["message"]
    assert len(system.roster) == n - 1


def test_cancel_refill_50_times(tmp_path):
    """情境 8：連續取消＋遞補 50 次 → check_consistency 全部通過。"""
    s = AppointmentSystem(load_records(), log_dir=tmp_path)
    s.load_day(DAY, waitlist_size=60)                # 候補要 ≥ 50 人
    assert len(s.waitlist) >= 50
    n = len(s.roster)
    rng = random.Random(7)
    for _ in range(50):
        victim = rng.choice(s.roster.to_list())
        assert s.cancel(victim.appointment_id)["ok"]
        assert s.check_consistency()
        assert s.refill()["ok"]
        assert s.check_consistency()
    assert len(s.roster) == n == 4528
    assert len(s.waitlist) == 10


def test_switch_day_keeps_changes(system, small_area):
    first = system.top_risk(1)[0].appointment_id
    added = system.add(patient_id=1, age=40, scheduled_day=DAY)["record"]
    assert system.check_consistency()
    system.cancel(first)
    assert system.check_consistency()
    system.load_day("2016-06-07")
    assert system.check_consistency()
    system.load_day(DAY, small_area)
    assert system.check_consistency()
    assert system.search(first)[0] is None
    assert system.search(added.appointment_id)[0] is added


# ---------------- 即存 log ----------------

def test_log_replay(small_area, tmp_path):
    log_dir = tmp_path / "logs"
    a = AppointmentSystem(load_records(), log_dir=log_dir)
    a.load_day(DAY, small_area)
    top = a.top_risk(3)
    a.cancel(top[0].appointment_id)
    a.confirm_attend(top[1].appointment_id)
    refilled = a.refill()["record"]
    added = a.add(patient_id=1, age=30, scheduled_day=DAY)["record"]
    assert (log_dir / f"{DAY}.csv").exists()
    state_a = {r.appointment_id: r.risk for r in a.roster}

    # 「關機」後重開：新的系統、同一個 log 資料夾
    b = AppointmentSystem(load_records(), log_dir=log_dir)
    info = b.load_day(DAY, small_area)
    assert info["replayed"] == 4
    assert {r.appointment_id: r.risk for r in b.roster} == state_a
    assert b.search(top[0].appointment_id)[0] is None
    assert b.search(refilled.appointment_id)[0] is not None
    b.check_consistency()

    # 新產生的編號不會跟 log 裡的重複
    new = b.add(patient_id=2, age=30, scheduled_day=DAY)["record"]
    assert new.appointment_id > max(refilled.appointment_id, added.appointment_id)


def test_log_replay_with_other_filter(small_area, tmp_path):
    """在某區域取消，重開後載入整天，取消仍然有效。"""
    a = AppointmentSystem(load_records(), log_dir=tmp_path)
    a.load_day(DAY, small_area)
    victim = a.top_risk(1)[0].appointment_id
    a.cancel(victim)
    b = AppointmentSystem(load_records(), log_dir=tmp_path)
    b.load_day(DAY)
    assert b.search(victim)[0] is None and len(b.roster) == 4527
    b.check_consistency()


def test_no_log_when_disabled(records, small_area):
    s = AppointmentSystem(load_records(), log_dir=None)
    s.load_day(DAY, small_area)
    s.cancel(s.top_risk(1)[0].appointment_id)       # 不會寫檔也不會出錯
    assert s.log_path() is None


def test_original_csv_untouched(small_area, tmp_path):
    before = hashlib.sha256(DEFAULT_CSV.read_bytes()).hexdigest()
    s = AppointmentSystem(load_records(), log_dir=tmp_path)
    s.load_day(DAY, small_area)
    s.cancel(s.top_risk(1)[0].appointment_id)
    s.refill()
    s.add(patient_id=1, age=30, scheduled_day=DAY)
    assert hashlib.sha256(DEFAULT_CSV.read_bytes()).hexdigest() == before


def test_overview_and_compare(system):
    rows = system.overview()
    assert len(rows) == len(system.roster) and rows[0]["燈號"] == risk_level(rows[0]["風險"])
    target = rows[-1]["掛號編號"]
    cmp_ = system.compare_search(target)
    assert cmp_["record"].appointment_id == target
    assert cmp_["path"][-1] == target and cmp_["bst"]["comparisons"] == len(cmp_["path"])
    assert len(system.heap_preview(3)) <= 7
