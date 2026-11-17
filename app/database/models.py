"""DDL for the deployment stage; LР3 tables are archived without data loss."""

CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('train','inference')),
    student_id INTEGER,
    actual TEXT,
    predicted TEXT NOT NULL,
    probability_low REAL,
    probability_medium REAL,
    probability_high REAL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

CREATE_INFERENCE_INPUTS = """
CREATE TABLE IF NOT EXISTS inference_inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER NOT NULL UNIQUE REFERENCES predictions(id),
    run_id TEXT NOT NULL,
    student_id INTEGER,
    input_origin TEXT NOT NULL CHECK(input_origin IN ('json','database')),
    input_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
)
"""

CREATE_TRAINING_RUNS = """
CREATE TABLE IF NOT EXISTS training_runs (
    run_id TEXT PRIMARY KEY,
    trained_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    model_name TEXT NOT NULL,
    train_size INTEGER NOT NULL,
    holdout_size INTEGER NOT NULL,
    accuracy REAL NOT NULL,
    f1_macro REAL NOT NULL,
    recall_high REAL NOT NULL,
    precision_high REAL NOT NULL,
    parameters_json TEXT NOT NULL,
    features_json TEXT NOT NULL,
    model_file TEXT NOT NULL
)
"""

CREATE_HOLDOUT_EVALUATIONS = """
CREATE TABLE IF NOT EXISTS holdout_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES training_runs(run_id),
    student_id INTEGER NOT NULL,
    actual TEXT NOT NULL,
    predicted TEXT NOT NULL,
    probability_high REAL NOT NULL
)
"""
