# Лабораторна робота №5 — моніторинг ML-моделі 

## Запуск  

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.services.monitoring --output reports
```

Після успішного виконання в `reports/` будуть:
- `evidently_data_drift.html` —  HTML-звіт Evidently AI;
- `evidently_data_quality.html` —  HTML-звіт Evidently AI;
- `reference_train.csv`, `current_inference.csv` — експорт для відтворення;
- `audit.json` — перевірені обсяги, описові показники та обмеження даних.

Для запуску лише експорту та перевірки джерел без бібліотеки Evidently:

```powershell
.\.venv\Scripts\python.exe -m app.services.monitoring --output reports --prepare-only
```

**Важливо:** якщо немає інтернету для `pip install evidently`, HTML-файли Evidently
не створяться. Не підміняйте їх HTML/Plotly. Після встановлення бібліотеки
повторіть команду без `--prepare-only` і перевірте HTML у браузері.

Ноутбук `notebooks/Lab5_Monitoring.ipynb` містить ті ж кроки, виклик Evidently
і Markdown-висновки. Сама ЛР4 (`FastAPI`, `POST /predict`, `POST /train-model`)
залишилася такою, як була у вихідному архіві.

## Пояснення 4 пунктів аналізу методички

- **Data drift**: поточна вибірка надто мала та повністю повторювана —
  статистичні тести Evidently не можна трактувати як доказ реального зсуву.
- **Найбільші відхилення**: у `audit.json` є *лише описове*, не статистичне
  ранжування числових ознак за різницею середніх у одиницях σ еталону.
- **Target drift**: 2 справжні мітки `actual`, обидві High, не дають
  підстав робити висновок про розподіл класів у поточному потоці.
- **Деградація та перенавчання**: даних недостатньо, рішення не обґрунтоване.



## Бонус: FastAPI /monitor

У терміналі VS Code з папки `lab5` запустіть:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

http://127.0.0.1:8000/monitor — моніторинг Data Drift.

http://127.0.0.1:8000/monitor?report=quality — Data Quality.

http://127.0.0.1:8000/docs — FastAPI.
