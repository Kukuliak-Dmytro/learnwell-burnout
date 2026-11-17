"""Валідація джерел ЛР5 без створення додаткових API-запитів."""
from pathlib import Path
import sqlite3
from app.config import DATABASE_PATH, FEATURES
from app.services.monitoring import load_data, audit_data


def test_reference_and_current_come_from_sqlite():
    reference, current, training_run = load_data()
    with sqlite3.connect(str(DATABASE_PATH)) as db:
        ref_count = db.execute(
            "SELECT count(*) FROM predictions WHERE source='train' AND run_id=?",
            (training_run['run_id'],)
        ).fetchone()[0]
        current_count = db.execute("SELECT count(*) FROM inference_inputs").fetchone()[0]
    assert len(reference) == ref_count
    assert len(current) == current_count
    assert all(key in reference.columns and key in current.columns for key in FEATURES)
    assert reference['timestamp'].notna().all() and current['timestamp'].notna().all()


def test_original_database_has_only_original_inference():
    reference, current, run = load_data()
    audit = audit_data(reference, current, run)
    assert len(reference) == 45000
    assert len(current) == 4
    assert audit['unique_current_feature_vectors'] == 1
    assert audit['known_current_target_count'] == 2
    assert set(current['actual'].dropna().unique()) == {'High'}
