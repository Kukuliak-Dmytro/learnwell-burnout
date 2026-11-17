from fastapi import APIRouter, HTTPException, Query
from app.config import FEATURES, LABELS
from app.database.database import connect
from app.database.crud import student_by_id, save_inference
from app.schemas import PredictRequest, PredictResponse
from app.services.model import load_saved_model, probability_matrix
import pandas as pd

router = APIRouter(tags=['Прогнозування'])


@router.get('/example-input', summary='Приклад JSON для прогнозу')
def example_input():
    row = student_by_id(100001)
    if row is None:
        raise HTTPException(status_code=404, detail='Приклад студента не знайдено в БД')
    features = {key: bool(row[key]) if key == 'paid_subscription' else row[key] for key in FEATURES}
    return {'features': features}


@router.get('/example-student', summary='Приклад запиту за ID студента')
def example_student():
    return {'student_id': 100001}


@router.post('/predict', response_model=PredictResponse, summary='Прогноз ризику вигорання Low / Medium / High')
def predict(payload: PredictRequest):
    """Accepts either a record ID from SQLite or twelve features in JSON."""
    if payload.student_id is not None:
        row = student_by_id(payload.student_id)
        if row is None:
            raise HTTPException(status_code=404, detail='Студента з таким ID не знайдено')
        features = {key: bool(row[key]) if key == 'paid_subscription' else row[key] for key in FEATURES}
        actual = row['burnout_risk_level']
        origin = 'database'
    else:
        features = payload.features.model_dump()
        actual = None
        origin = 'json'
    try:
        artifact = load_saved_model()
        model = artifact['pipeline']
        data = pd.DataFrame([features], columns=FEATURES)
        prediction = str(model.predict(data)[0])
        probabilities = dict(zip(LABELS, probability_matrix(model, data)[0]))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Помилка моделі: {exc}') from exc

    prediction_id = save_inference(
        run_id=artifact['run_id'], student_id=payload.student_id,
        actual=actual, prediction=prediction, probabilities=probabilities,
        origin=origin, features=features,
    )
    return PredictResponse(
        prediction_id=prediction_id, run_id=artifact['run_id'],
        source='inference', student_id=payload.student_id,
        prediction=prediction, probabilities=probabilities,
        message='Прогноз та вхідні характеристики збережено в SQLite',
    )


@router.get('/predictions', summary='Останні прогнози для перевірки логування')
def recent_predictions(limit: int = Query(10, ge=1, le=100)):
    with connect() as db:
        rows = db.execute('''SELECT id,source,student_id,actual,predicted,
                   probability_high,created_at FROM predictions ORDER BY id DESC LIMIT ?''', (limit,)).fetchall()
    return {'count':len(rows),'predictions':[dict(r) for r in rows]}
