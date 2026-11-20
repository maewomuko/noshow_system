"""任務 8：Streamlit 各頁的冒煙測試（AppTest 在背景跑頁面，不開瀏覽器）。

log 寫到暫存資料夾，不會動到 data/logs。
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

from core.system import AppointmentSystem  # noqa: E402

APP = ROOT / "app"
PAGES = ["Home.py", "pages/1_預約查詢.py", "pages/2_風險關懷名單.py",
         "pages/3_候補與超額預約.py", "pages/4_新增預約.py", "pages/5_效能分析.py"]


@pytest.fixture(scope="module")
def system(tmp_path_factory):
    s = AppointmentSystem.load(log_dir=tmp_path_factory.mktemp("logs"))
    s.load_day("2016-06-06", "JARDIM CAMBURI")
    return s


def run_page(page, system):
    at = AppTest.from_file(str(APP / page), default_timeout=60)
    at.session_state["system"] = system          # 共用同一個系統，省掉每頁重新讀檔
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, system):
    run_page(page, system)


def test_home_load_day(system):
    at = run_page("Home.py", system)
    at.selectbox[0].set_value("2016-06-07").run()
    at.button[0].click().run()
    assert not at.exception
    assert system.day == "2016-06-07" and system.neighbourhood is None
    assert any("已載入" in s.value for s in at.success)
    system.load_day("2016-06-06", "JARDIM CAMBURI")      # 還原給其他測試


def test_care_confirm_and_cancel(system):
    at = run_page("pages/2_風險關懷名單.py", system)
    top = system.top_risk(1)[0]
    at.button(key=f"ok_{top.appointment_id}").click().run()
    assert not at.exception and top.risk == 0.0
    victim = system.top_risk(1)[0].appointment_id
    at.button(key=f"cancel_{victim}").click().run()
    assert not at.exception and system.search(victim)[0] is None
    system.check_consistency()


def test_refill_button(system):
    at = run_page("pages/3_候補與超額預約.py", system)
    before = len(system.waitlist)
    at.button[0].click().run()
    assert not at.exception and len(system.waitlist) == before - 1
    system.check_consistency()


def test_add_form(system):
    at = run_page("pages/4_新增預約.py", system)
    n = len(system.roster)
    at.number_input[0].set_value(1)                       # 新病患
    at.button[0].click().run()
    assert not at.exception and len(system.roster) == n + 1
    assert any("已新增" in s.value for s in at.success)
    system.check_consistency()
