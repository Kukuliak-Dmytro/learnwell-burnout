"""Parameterised queries and transaction-safe audit logging."""
import json
from app.config import FEATURES, TARGET, MODEL_NAME
from app.database.database import connect


def student_by_id(student_id: int):
    selection = ', '.join(['student_id', *FEATURES, TARGET])
    with connect() as db:
        row = db.execute(f'SELECT {selection} FROM students_burnout WHERE student_id=?', (student_id,)).fetchone()
        return dict(row) if row is not None else None


def save_training_run(*, run_id, train_ids, train_y, train_predictions, train_proba,
                      holdout_ids, holdout_y, holdout_predictions, holdout_proba,
                      scores, model_file, parameters):
    train_rows = [(
        run_id, MODEL_NAME, 'train', int(student_id), str(actual), str(predicted),
        float(p[0]), float(p[1]), float(p[2]),
    ) for student_id, actual, predicted, p in zip(train_ids, train_y, train_predictions, train_proba)]
    holdout_rows = [(
        run_id, int(student_id), str(actual), str(predicted), float(p[2]),
    ) for student_id, actual, predicted, p in zip(holdout_ids, holdout_y, holdout_predictions, holdout_proba)]
    with connect() as db:
        db.execute('''INSERT INTO training_runs
            (run_id,model_name,train_size,holdout_size,accuracy,f1_macro,recall_high,
             precision_high,parameters_json,features_json,model_file)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (run_id, MODEL_NAME, len(train_rows), len(holdout_rows),
             scores['accuracy'], scores['f1_macro'], scores['recall_high'], scores['precision_high'],
             json.dumps(parameters, ensure_ascii=False), json.dumps(FEATURES, ensure_ascii=False), model_file))
        db.executemany('''INSERT INTO predictions
            (run_id,model_name,source,student_id,actual,predicted,
             probability_low,probability_medium,probability_high)
            VALUES (?,?,?,?,?,?,?,?,?)''', train_rows)
        db.executemany('''INSERT INTO holdout_evaluations
            (run_id,student_id,actual,predicted,probability_high)
            VALUES (?,?,?,?,?)''', holdout_rows)


def save_inference(*, run_id, student_id, actual, prediction, probabilities, origin, features):
    with connect() as db:
        cursor = db.execute('''INSERT INTO predictions
            (run_id,model_name,source,student_id,actual,predicted,
             probability_low,probability_medium,probability_high)
            VALUES (?,?, 'inference', ?,?,?,?,?,?)''',
            (run_id, MODEL_NAME, student_id, actual, prediction,
             probabilities['Low'], probabilities['Medium'], probabilities['High']))
        prediction_id = int(cursor.lastrowid)
        db.execute('''INSERT INTO inference_inputs
            (prediction_id,run_id,student_id,input_origin,input_json) VALUES (?,?,?,?,?)''',
            (prediction_id, run_id, student_id, origin, json.dumps(features, ensure_ascii=False)))
        return prediction_id
