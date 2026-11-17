from fastapi import APIRouter, HTTPException
from app.services.model import train_and_store

router = APIRouter(tags=['Навчання'])


@router.post('/train-model', summary='Навчити логістичну регресію та зберегти результати')
def train_model():
    """Читає 50 000 записів, 90/10 split, навчає модель і логуює прогнозування."""
    try:
        return train_and_store()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
