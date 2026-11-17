"""Paths and classifier settings used throughout the project."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = Path(os.environ.get('LEARNWELL_DB_PATH', PROJECT_ROOT / 'data' / 'student_burnout_lab4.db'))
MODEL_PATH = Path(os.environ.get('LEARNWELL_MODEL_PATH', PROJECT_ROOT / 'models' / 'burnout_logistic_regression.joblib'))
MODEL_NAME = 'Logistic Regression'
RANDOM_STATE = 42
TEST_SIZE = 0.10
TARGET = 'burnout_risk_level'
FEATURES = [
    'major_category', 'year_of_study', 'pre_semester_gpa',
    'weekly_genai_hours', 'primary_use_case', 'prompt_engineering_skill',
    'tool_diversity', 'paid_subscription', 'traditional_study_hours',
    'perceived_ai_dependency', 'institutional_policy',
    'anxiety_level_during_exams',
]
CATEGORICAL = [
    'major_category', 'year_of_study', 'primary_use_case',
    'prompt_engineering_skill', 'institutional_policy',
]
NUMERIC = [col for col in FEATURES if col not in CATEGORICAL]
LABELS = ['Low', 'Medium', 'High']
