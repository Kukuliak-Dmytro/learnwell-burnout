"""Local FastAPI entrypoint for laboratory work 4."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from app.services.monitoring import prepare, run_evidently, DEFAULT_OUTPUT
from app.database.database import init_database
from app.endpoints.training import router as training_router
from app.endpoints.inference import router as inference_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield

app = FastAPI(
    title='LearnWell Analytics — Лабораторна робота №4',
    description=(
        'Розгортання моделі логістичної регресії для класифікації академічного '
        'вигорання студентів (Low / Medium / High). Дані та аудиторські логи — SQLite.'
    ),
    version='1.0.0',
    docs_url='/docs',
    redoc_url='/redoc',
    lifespan=lifespan,
)
app.include_router(training_router)
app.include_router(inference_router)

@app.get('/', tags=['Сервіс'], summary='Відомості про API')
def home():
    return {
        'service':'LearnWell Analytics / Student Burnout',
        'algorithm':'Logistic Regression',
        'classes':['Low','Medium','High'],
        'documentation':'/docs',
        'steps':['POST /train-model','GET /example-input','POST /predict','GET /predictions','GET /monitor'],
    }

@app.get('/health', tags=['Сервіс'], summary='Перевірка доступності сервера')
def health():
    return {'status':'ok'}


@app.get('/monitor', response_class=HTMLResponse, tags=['Моніторинг'], summary='HTML-звіт Evidently AI')
def monitor(report: str = Query('drift', pattern='^(drift|quality)$')):
    try:
        reference, current, _ = prepare(output_dir=DEFAULT_OUTPUT)
        run_evidently(reference, current, DEFAULT_OUTPUT)
        filename = 'evidently_data_drift.html' if report == 'drift' else 'evidently_data_quality.html'
        return HTMLResponse((DEFAULT_OUTPUT / filename).read_text(encoding='utf-8'))
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
