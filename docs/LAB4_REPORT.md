# Лабораторна робота №4

**Тема:** Розгортання моделі машинного навчання.  
**Проєкт:** LearnWell Analytics — Student Burnout Risk (GenAI Impact).

## Мета роботи

Створити завершений ML-застосунок, який на основі попередніх лабораторних
навчає модель і виконує класифікацію ризику академічного вигорання студентів
через HTTP-інтерфейс FastAPI зі збереженням дій у SQLite.

## Вихідні дані

Використано набір `ai_student_impact_dataset.csv`, що містить 50 000 записів
студентів. У роботі прогнозується `burnout_risk_level` із категоріями
**Low**, **Medium**, **High**. Вихідна база `student_burnout` сформована в ЛР1,
у ЛР2 виконувалася підготовка даних, у ЛР3 — порівняння трьох моделей,
кросвалідація й оптимізація гіперпараметрів.

## 1. Модель

Після порівняння Logistic Regression, Decision Tree та Random Forest у ЛР3
було вибрано багатокласову **логістичну регресію**. Вона приймає 12 ознак:
`major_category`, `year_of_study`, `pre_semester_gpa`, `weekly_genai_hours`,
`primary_use_case`, `prompt_engineering_skill`, `tool_diversity`,
`paid_subscription`, `traditional_study_hours`, `perceived_ai_dependency`,
`institutional_policy`, `anxiety_level_during_exams`.

Препроцесинг сформовано в `Pipeline`: заповнення пропусків, стандартизація
числових ознак та One-Hot Encoding категоріальних. Класифікатор має
`C=0.1`, `class_weight=None`, `max_iter=1000`, `random_state=42`.

## 2. Схема даних

Використовується копія БД з ЛР3. Таблиця `students_burnout` містить вихідні
ознаки, цільовий клас і `timestamp`. Таблиця `students_burnout_features`
доповнюється `timestamp` для подальшого часового аналізу. Результати
попередньої лабораторної архівуються у `lab3_predictions`, а нові таблиці:

- `predictions`: `id`, `run_id`, `model_name`, `source`, `student_id`, `actual`,
  `predicted`, `probability_low`, `probability_medium`, `probability_high`, `created_at`.
- `inference_inputs`: `id`, `prediction_id`, `run_id`, `student_id`,
  `input_origin`, `input_json`, `created_at`.
- `training_runs`: дата, кількість даних, параметри, метрики, модель.
- `holdout_evaluations`: окремі контрольні прогнози на відкладених записах.

У `predictions.source` допускається тільки `train` або `inference`. Таким чином,
навчальні й запити користувача можна аналізувати окремо.

## 3. Алгоритм навчання

Виклик `POST /train-model` читає 50 000 рядків, ділить їх на 45 000 (90%)
для навчання та 5 000 (10%) для незалежної відкладеної перевірки.
Розбиття стратифіковане за цільовим класом, `random_state=42`.

Після `fit` модель робить прогнози на train і holdout. Зберігаються:
готовий Pipeline у `models/burnout_logistic_regression.joblib`,
45 000 train-прогнозів із `source='train'`, 5 000 holdout-оцінок і метрики:
Accuracy, Macro F1-score, Recall High, Precision High.
Це оцінювання виконується **в межах HTTP-запиту**, без ручного запуску ноутбука.

## 4. Алгоритм прогнозування

`POST /predict` приймає один із двох варіантів: `student_id` з БД або JSON
із усіма 12 ознаками. Модель завантажується з диска, видає один із класів
Low/Medium/High та їхні ймовірності. Параметри запиту зберігаються
в `inference_inputs`, а прогноз — у `predictions` з `source='inference'`.

## 5. Фактичні результати перевірки

При контрольному запуску через `POST /train-model` на 5 000 незалежних
відкладених записах отримано:

| Показник | Значення |
|---|---:|
| Accuracy | 0.5420 |
| Macro F1 | 0.5416 |
| Recall High | 0.4676 |
| Precision High | 0.6736 |

Два запити `/predict` (за `student_id=100001` та через 12 ознак) повернули
`High` з оціненою ймовірністю `0.7529`. Записи отримали `prediction_id`
45001 і 45002. Це відповідає збереженим даним у `predictions` та
`inference_inputs`.

Така точність недостатня для практичного автоматичного втручання в навчання
студентів, тому розгортання слід розглядати як демонстрацію ML API.

## 6. Перевірка й демонстрація

Адреса Swagger UI: `http://127.0.0.1:8000/docs`.
Послідовність демонстрації: `POST /train-model` → `GET /example-input`
→ `POST /predict` → `GET /predictions`.

Для підтвердження роботи SQLite виконується SQL-запит:

```sql
SELECT p.id, p.source, p.predicted, i.input_json
FROM predictions p
JOIN inference_inputs i ON i.prediction_id = p.id
ORDER BY p.id DESC LIMIT 10;
```

## 7. Подальший аналіз

Збереження прогнозів і вхідних параметрів дає змогу оцінювати зміну
розподілу рівнів вигорання, частоту прогнозів High, характеристики
помилок та можливий дрейф даних у разі надходження нових студентів.
Синтетичний `timestamp` з ЛР1 не слід вважати реальною датою обстеження:
для справжнього моніторингу потрібен фактичний час надходження спостереження.

## Висновок

Реалізовано вебслужбу для розгортання багатокласової логістичної регресії.
Сервер організовано за модулями, навчання й прогнозування доступні через HTTP,
модель серіалізується у файл, а результати операцій та їхні вхідні дані
реєструються у реляційній базі SQLite. Додатково впроваджено автоматизовані
тести, валідацію JSON, незалежне holdout-оцінювання та збереження історії ЛР3.
