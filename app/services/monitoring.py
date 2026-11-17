
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

from app.config import (
    PROJECT_ROOT,
    DATABASE_PATH,
    FEATURES,
    NUMERIC,
    CATEGORICAL,
    LABELS,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "reports"


def load_data(db_path: Path = DATABASE_PATH):
    db_path = Path(db_path).resolve()

    if not db_path.is_file():
        raise FileNotFoundError(f"База даних не існує: {db_path}")

    con = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    try:
        latest = con.execute(
            """
            SELECT run_id, trained_at, train_size,
                   accuracy, f1_macro, recall_high, precision_high
            FROM training_runs
            ORDER BY trained_at DESC
            LIMIT 1
            """
        ).fetchone()

        if latest is None:
            raise ValueError("У БД відсутній training_runs")

        train_run = dict(latest)

        columns = ", ".join(
            's."' + name + '"' for name in FEATURES
        )

        reference = pd.read_sql_query(
            f"""
            SELECT s.timestamp, {columns},
                   p.actual, p.predicted, p.run_id
            FROM predictions p
            JOIN students_burnout s
                ON s.student_id = p.student_id
            WHERE p.source = 'train'
              AND p.run_id = ?
            ORDER BY p.id
            """,
            con,
            params=(train_run["run_id"],),
        )

        inference = con.execute(
            """
            SELECT i.id AS request_id,
                   i.input_json,
                   i.created_at AS timestamp,
                   i.input_origin,
                   p.actual,
                   p.predicted,
                   p.run_id
            FROM inference_inputs i
            JOIN predictions p
                ON p.id = i.prediction_id
            WHERE p.source = 'inference'
            ORDER BY i.id
            """
        ).fetchall()

    finally:
        con.close()

    if reference.empty:
        raise ValueError(
            "Немає навчальних записів source='train' останнього запуску"
        )

    rows = []

    for record in inference:
        obj = dict(record)
        payload = json.loads(obj.pop("input_json"))

        if not isinstance(payload, dict):
            raise ValueError(
                f"Некоректні ознаки для запиту #{obj['request_id']}"
            )

        if any(name not in payload for name in FEATURES):
            raise ValueError(
                f"У запиті #{obj['request_id']} немає всіх 12 ознак"
            )

        rows.append({
            **obj,
            **{key: payload[key] for key in FEATURES},
        })

    current = pd.DataFrame(
        rows,
        columns=[
            "request_id",
            "timestamp",
            "input_origin",
            "actual",
            "predicted",
            "run_id",
            *FEATURES,
        ],
    )

    for df in (reference, current):
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            utc=True,
            errors="coerce",
        )

        if df["timestamp"].isna().any():
            raise ValueError(
                "Знайдено відсутні або некоректні timestamp"
            )

        for name in NUMERIC:
            df[name] = pd.to_numeric(
                df[name],
                errors="coerce",
            )

        for name in CATEGORICAL:
            df[name] = df[name].astype("string")

    if (
        reference[FEATURES].isna().any().any()
        or current[FEATURES].isna().any().any()
    ):
        raise ValueError(
            "Пропущені значення у вхідних ознаках"
        )

    return reference, current, train_run


def audit_data(reference, current, train_run):
    distinct = (
        int(current[FEATURES].drop_duplicates().shape[0])
        if not current.empty
        else 0
    )

    known = current["actual"].dropna()
    deltas = []

    for name in NUMERIC:
        ref = pd.to_numeric(reference[name])
        cur = pd.to_numeric(current[name])

        ref_sd = float(ref.std())

        if len(cur) and ref_sd > 0:
            standardized_diff = (
                abs(float(cur.mean() - ref.mean())) / ref_sd
            )

            deltas.append({
                "feature": name,
                "standardized_mean_difference": round(
                    standardized_diff, 4
                ),
            })

    deltas.sort(
        key=lambda item: item["standardized_mean_difference"],
        reverse=True,
    )

    return {
        "database": "student_burnout_lab4.db",
        "reference_source": (
            "predictions.source='train' "
            "(latest training_runs.run_id)"
        ),
        "current_source": (
            "inference_inputs + "
            "predictions.source='inference'"
        ),
        "reference_run_id": train_run["run_id"],
        "reference_rows": int(len(reference)),
        "current_rows": int(len(current)),
        "unique_current_feature_vectors": distinct,
        "features_count": len(FEATURES),
        "reference_timestamp_origin": (
            "synthetic 2025 timestamps generated in lab 1"
        ),
        "current_timestamp_origin": "actual API request time",
        "known_current_target_count": int(len(known)),
        "missing_current_target_count": int(
            current["actual"].isna().sum()
        ),
        "reference_target_counts": {
            name: int((reference["actual"] == name).sum())
            for name in LABELS
        },
        "current_known_target_counts": {
            name: int((known == name).sum())
            for name in LABELS
        },
        "current_predicted_counts": {
            name: int((current["predicted"] == name).sum())
            for name in LABELS
        },
        "current_run_ids": current[
            "run_id"
        ].value_counts().to_dict(),
        "previous_holdout_metrics": {
            name: float(train_run[name])
            for name in (
                "accuracy",
                "f1_macro",
                "recall_high",
                "precision_high",
            )
        },
        "numerical_feature_differences_descriptive_only": deltas,
        "data_drift_conclusion": (
            "Недостатньо даних для достовірної оцінки data drift."
        ),
        "target_drift_conclusion": (
            "Недостатньо фактичних значень цільової змінної."
        ),
        "performance_degradation_conclusion": (
            "Недостатньо даних для оцінки деградації моделі."
        ),
        "retraining_conclusion": (
            "Для рішення про перенавчання необхідно "
            "накопичити більше нових даних."
        ),
    }


def prepare(
    db_path: Path = DATABASE_PATH,
    output_dir: Path = DEFAULT_OUTPUT,
):
    reference, current, run = load_data(db_path)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cols = [
        "timestamp",
        *FEATURES,
        "actual",
        "predicted",
        "run_id",
    ]

    reference[cols].to_csv(
        output_dir / "reference_train.csv",
        index=False,
        encoding="utf-8-sig",
    )

    current[
        ["request_id", "input_origin", *cols]
    ].to_csv(
        output_dir / "current_inference.csv",
        index=False,
        encoding="utf-8-sig",
    )

    audit = audit_data(reference, current, run)

    (output_dir / "audit.json").write_text(
        json.dumps(
            audit,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return reference, current, audit


def run_evidently(reference, current, output_dir: Path):
    if current.empty:
        raise ValueError(
            "У inference_inputs немає записів"
        )

    try:
        from evidently import Dataset, DataDefinition, Report
        from evidently.presets import (
            DataDriftPreset,
            DataSummaryPreset,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Evidently не встановлено. "
            "Виконайте: python -m pip install -r requirements.txt"
        ) from exc

    numerical_columns = list(NUMERIC)
    categorical_columns = list(CATEGORICAL)

    reference_features = reference[FEATURES].copy()
    current_features = current[FEATURES].copy()

    for column in numerical_columns:
        reference_features[column] = pd.to_numeric(
            reference_features[column],
            errors="raise",
        ).astype(float)

        current_features[column] = pd.to_numeric(
            current_features[column],
            errors="raise",
        ).astype(float)

    for column in categorical_columns:
        reference_features[column] = (
            reference_features[column].astype(str)
        )
        current_features[column] = (
            current_features[column].astype(str)
        )

    schema = DataDefinition(
        numerical_columns=numerical_columns,
        categorical_columns=categorical_columns,
    )

    reference_data = Dataset.from_pandas(
        reference_features,
        data_definition=schema,
    )

    current_data = Dataset.from_pandas(
        current_features,
        data_definition=schema,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []

    reports = [
        (
            DataDriftPreset(),
            "evidently_data_drift.html",
        ),
        (
            DataSummaryPreset(),
            "evidently_data_quality.html",
        ),
    ]

    for preset, filename in reports:
        result = Report([preset]).run(
            current_data,
            reference_data,
        )

        file = output_dir / filename
        result.save_html(str(file))
        paths.append(file)

    return paths


def main():
    parser = argparse.ArgumentParser(
        description="ЛР5: SQLite -> Evidently AI HTML"
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DATABASE_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Експорт CSV та аудит без Evidently",
    )

    args = parser.parse_args()

    reference, current, audit = prepare(
        args.db,
        args.output,
    )

    print(
        "Еталон:",
        len(reference),
        "| запитів API:",
        len(current),
        "| унікальних:",
        audit["unique_current_feature_vectors"],
    )

    if args.prepare_only:
        print("Збережено CSV та audit.json")
        return

    for path in run_evidently(
        reference,
        current,
        args.output,
    ):
        print("HTML Evidently:", path)

    print("Моніторинг завершено")


if __name__ == "__main__":
    main()
