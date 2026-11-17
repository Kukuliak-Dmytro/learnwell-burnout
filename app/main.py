"""Local FastAPI entrypoint for laboratory work 4."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
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
        'steps':['POST /train-model','GET /example-input','POST /predict','GET /predictions'],
    }

@app.get('/health', tags=['Сервіс'], summary='Перевірка доступності сервера')
def health():
    return {'status':'ok'}
