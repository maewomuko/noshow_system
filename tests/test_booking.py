"""病患索引（PatientBST）與新增預約（make_appointment）的測試。"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.record import Record, load_records
from core.patient_index import PatientBST
from core.booking import IdGenerator, make_appointment, wait_days_between


def make(aid, pid, day, showed=True):
    return Record(appointment_id=aid, patient_id=pid, age=30, gender="F", wait_days=0,
                  scheduled_day=day, appointment_day=day, neighbourhood="X",
                  sms=False, chronic=False, showed_up=showed)


@pytest.fixture(scope="module")
def all_records():
    return load_records()


class TestPatientBST:
    def test_group_and_order(self):
        idx = PatientBST()
        for r in [make(3, 9, "2016-05-05"), make(1, 9, "2016-05-01"),
                  make(2, 5, "2016-05-02"), make(4, 9, "2016-05-03")]:
            idx.insert(r)
        assert len(idx) == 2 and idx.record_count == 4
        recs, _, _ = idx.search(9)
        assert [r.appointment_id for r in recs] == [1, 4, 3]   # 依看診日排序
        assert idx.search(777)[0] is None

    def test_past_noshow(self):
        idx = PatientBST.from_records([
            make(1, 9, "2016-05-01", showed=False),
            make(2, 9, "2016-05-02", showed=True),
            make(3, 9, "2016-05-03", showed=False),
            make(4, 9, "2016-05-10", showed=None)])     # 未來預約不算
        assert idx.past_noshow(9, "2016-05-03") == 1    # 只算 05-03 之前
        assert idx.past_noshow(9, "2016-06-01") == 2
        assert idx.past_noshow(123, "2016-06-01") == 0  # 新病患

    def test_remove_record(self):
        a, b = make(1, 9, "2016-05-01"), make(2, 9, "2016-05-02")
        idx = PatientBST.from_records([a, b])
        assert idx.remove_record(a) and idx.record_count == 1
        assert not idx.remove_record(a)
        assert [r.appointment_id for r in idx.search(9)[0]] == [2]

    def test_full_data(self, all_records):
        shuffled = all_records[:]
        random.Random(1).shuffle(shuffled)
        idx = PatientBST.from_records(shuffled)
        assert len(idx) == len({r.patient_id for r in all_records})
        assert idx.record_count == len(all_records)
        # 索引算出的過往未到次數不應超過 load_records 算的：
        # load_records 會把「同一天、編號較小」的預約也算成之前，索引只算嚴格早於該日的
        for r in random.Random(2).sample(all_records, 2000):
            assert idx.past_noshow(r.patient_id, r.appointment_day) <= r.past_noshow
        assert idx.height() < 60


class TestBooking:
    def test_wait_days(self):
        assert wait_days_between("2016-05-01", "2016-05-22") == 21

    def test_id_generator_unique(self, all_records):
        gen = IdGenerator(all_records)
        ids = {gen.next() for _ in range(5)}
        assert len(ids) == 5 and min(ids) > max(r.appointment_id for r in all_records)

    def test_existing_patient_high_risk(self):
        idx = PatientBST.from_records([make(1, 9, "2016-05-01", False),
                                       make(2, 9, "2016-05-02", False)])
        out = make_appointment(idx, IdGenerator([]), patient_id=9, age=25,
                               scheduled_day="2016-05-10", appointment_day="2016-06-01")
        r = out["record"]
        assert not out["is_new"] and out["history"] == 2
        assert r.past_noshow == 2 and r.wait_days == 22
        assert r.risk == 45 + 35 + 20 and out["level"] == "紅"
        assert r.showed_up is None

    def test_new_patient(self):
        out = make_appointment(PatientBST(), IdGenerator([]), patient_id=1, age=70,
                               scheduled_day="2016-05-01", appointment_day="2016-05-01")
        assert out["is_new"] and out["record"].risk == 0 and out["level"] == "綠"

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            make_appointment(PatientBST(), IdGenerator([]), patient_id=1, age=30,
                             scheduled_day="2016-05-10", appointment_day="2016-05-01")
        with pytest.raises(ValueError):
            make_appointment(PatientBST(), IdGenerator([]), patient_id=1, age=-3,
                             scheduled_day="2016-05-01", appointment_day="2016-05-02")
