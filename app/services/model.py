"""Training and persistence of the LР3 multinomial logistic classifier."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config import (
    FEATURES, CATEGORICAL, NUMERIC, TARGET, RANDOM_STATE,
    TEST_SIZE, MODEL_PATH, LABELS,
)
from app.database.database import connect
from app.database.crud import save_training_run

TRAIN_LOCK = threading.Lock()


def make_pipeline():
    """Exact LР3 preprocessing and tuned LogisticRegression C=0.1."""
    prep = ColumnTransformer([
        ('num', Pipeline([
            ('fill', SimpleImputer(strategy='median')),
            ('scale', StandardScaler()),
        ]), NUMERIC),
        ('cat', Pipeline([
            ('fill', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore')),
        ]), CATEGORICAL),
    ], sparse_threshold=0)
    return Pipeline([
        ('prep', prep),
        ('clf', LogisticRegression(C=0.1, class_weight=None, max_iter=1000, random_state=RANDOM_STATE)),
    ])


def probability_matrix(pipeline, data):
    scores = pipeline.predict_proba(data)
    index = {label: position for position, label in enumerate(pipeline.classes_)}
    return [[float(row[index[label]]) for label in LABELS] for row in scores]


def load_saved_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError('Спочатку виконайте POST /train-model')
    artifact = joblib.load(MODEL_PATH)
    if not isinstance(artifact, dict) or 'pipeline' not in artifact or 'run_id' not in artifact:
        raise RuntimeError('Файл моделі не відповідає формату лабораторної №4')
    if artifact.get('features') != FEATURES:
        raise RuntimeError('Збережена модель має несумісний набір ознак')
    return artifact


def train_and_store():
    with TRAIN_LOCK:
        with connect() as db:
            columns = ', '.join(['student_id', TARGET, *FEATURES])
            df = pd.read_sql_query(f'SELECT {columns} FROM students_burnout', db)
        if df.empty or df[TARGET].nunique() < 2:
            raise ValueError('Недостатньо даних для навчання')
        if not set(df[TARGET]).issubset(set(LABELS)):
            raise ValueError('Невідомі класи цільової ознаки')
        X = df[FEATURES].copy()
        y = df[TARGET].copy()
        ids = df['student_id'].astype(int)
        X_tr, X_hold, y_tr, y_hold, ids_tr, ids_hold = train_test_split(
            X, y, ids, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
        )
        model = make_pipeline()
        model.fit(X_tr, y_tr)
        tr_pred = model.predict(X_tr)
        hold_pred = model.predict(X_hold)
        tr_probs = probability_matrix(model, X_tr)
        hold_probs = probability_matrix(model, X_hold)
        scores = {
            'accuracy': float(accuracy_score(y_hold, hold_pred)),
            'f1_macro': float(f1_score(y_hold, hold_pred, labels=LABELS, average='macro', zero_division=0)),
            'recall_high': float(recall_score(y_hold, hold_pred, labels=['High'], average='macro', zero_division=0)),
            'precision_high': float(precision_score(y_hold, hold_pred, labels=['High'], average='macro', zero_division=0)),
        }
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:10]
        params = {'C':0.1,'class_weight':None,'max_iter':1000,'random_state':42}
        artifact = {'pipeline': model, 'run_id':run_id, 'features':FEATURES, 'classes':LABELS, 'parameters':params}
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = MODEL_PATH.with_name(f'{MODEL_PATH.name}.{run_id}.tmp')
        try:
            joblib.dump(artifact, temporary_file)
            save_training_run(
                run_id=run_id, train_ids=ids_tr, train_y=y_tr, train_predictions=tr_pred,
                train_proba=tr_probs, holdout_ids=ids_hold, holdout_y=y_hold,
                holdout_predictions=hold_pred, holdout_proba=hold_probs, scores=scores,
                model_file=str(MODEL_PATH.relative_to(MODEL_PATH.parents[1])), parameters=params,
            )
            os.replace(temporary_file, MODEL_PATH)
        finally:
            if temporary_file.exists():
                temporary_file.unlink()
        return {
            'message': 'Модель навчена, збережена; результати навчання та оцінювання записані в SQLite.',
            'run_id': run_id,
            'model': 'Logistic Regression',
            'parameters': params,
            'total_records': len(df),
            'train_records': len(X_tr),
            'holdout_records': len(X_hold),
            'metrics_holdout': scores,
            'model_file': 'models/burnout_logistic_regression.joblib',
            'train_predictions_saved': len(X_tr),
            'holdout_evaluations_saved': len(X_hold),
        }
