"""SQLite connection and non-destructive schema migration."""
import sqlite3
from contextlib import contextmanager
from app.config import DATABASE_PATH
from app.database.models import (
    CREATE_PREDICTIONS, CREATE_INFERENCE_INPUTS,
    CREATE_TRAINING_RUNS, CREATE_HOLDOUT_EVALUATIONS,
)

@contextmanager
def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE_PATH), timeout=60)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA busy_timeout=60000')
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database():
    if not DATABASE_PATH.exists():
        raise RuntimeError(f'Не знайдено базу даних: {DATABASE_PATH}')
    with connect() as db:
        tables = {r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'students_burnout' not in tables:
            raise RuntimeError('У SQLite відсутня таблиця students_burnout')
        original_columns = {r['name'] for r in db.execute('PRAGMA table_info(students_burnout)')}
        if 'timestamp' not in original_columns:
            raise RuntimeError('Таблиця students_burnout повинна містити timestamp з ЛР1')

        # Old LР3 predictions used source=train/test. Preserve them in an archive,
        # while the new LР4 predictions table admits source=train/inference only.
        if 'predictions' in tables:
            cols = {r['name'] for r in db.execute('PRAGMA table_info(predictions)')}
            if 'probability_high' not in cols:
                if 'lab3_predictions' not in tables:
                    db.execute('ALTER TABLE predictions RENAME TO lab3_predictions')
                else:
                    raise RuntimeError('Конфлікт таблиць predictions та lab3_predictions')

        db.execute(CREATE_PREDICTIONS)
        db.execute(CREATE_INFERENCE_INPUTS)
        db.execute(CREATE_TRAINING_RUNS)
        db.execute(CREATE_HOLDOUT_EVALUATIONS)
        db.execute('CREATE INDEX IF NOT EXISTS ix_predictions_source_time ON predictions(source, id DESC)')
        db.execute('CREATE INDEX IF NOT EXISTS ix_predictions_run ON predictions(run_id)')
        db.execute('CREATE INDEX IF NOT EXISTS ix_holdout_run ON holdout_evaluations(run_id)')
        db.execute('CREATE INDEX IF NOT EXISTS ix_burnout_student_id ON students_burnout(student_id)')

        # Preserve the prepared table from LР2 and make its date available for audit.
        if 'students_burnout_features' in tables:
            fields = {r['name'] for r in db.execute('PRAGMA table_info(students_burnout_features)')}
            if 'timestamp' not in fields:
                db.execute('ALTER TABLE students_burnout_features ADD COLUMN timestamp TEXT')
            db.execute('''UPDATE students_burnout_features
                SET timestamp=(SELECT s.timestamp FROM students_burnout AS s
                               WHERE s.student_id=students_burnout_features.student_id)
                WHERE timestamp IS NULL''')
