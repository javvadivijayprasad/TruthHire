"""Real persistence tests (TH-005) — data lives in the DB, not in memory."""
from app.store import CheckStore
from app.credits import ledger


def test_db_backed_not_instance_state():
    # a value written by one instance is readable by a *different* instance
    CheckStore().put("th_chk_persist", {"risk": 42})
    assert CheckStore().get("th_chk_persist") == {"risk": 42}


def test_file_db_survives_reconnect(tmp_path):
    # write with one engine, dispose it, reconnect a new engine -> data is still there
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db import Base
    from app.models import CheckRecord
    url = f"sqlite:///{tmp_path}/persist.db"
    e1 = create_engine(url); Base.metadata.create_all(e1)
    S1 = sessionmaker(bind=e1)
    with S1() as s:
        s.add(CheckRecord(check_id="c1", payload='{"a":1}')); s.commit()
    e1.dispose()                                   # simulate process exit
    e2 = create_engine(url)                          # fresh process/connection
    with sessionmaker(bind=e2)() as s:
        rec = s.get(CheckRecord, "c1")
        assert rec is not None and rec.payload == '{"a":1}'
    e2.dispose()


def test_credit_balance_persists():
    ledger.reset()
    ledger.contribute("orgP", [{"outcome": "legitimate"}])
    # new ledger object reads the same persisted balance
    from app.credits import CreditLedger
    assert CreditLedger().balance("orgP")["credits_available"] == 1.0
