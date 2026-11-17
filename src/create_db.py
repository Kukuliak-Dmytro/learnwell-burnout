"""
Лабораторна робота 1 — Крок 3: створення реляційної БД
Варіант: Student Burnout Risk — GenAI Impact (LearnWell Analytics)

Що робить цей скрипт:
1. Читає вихідний CSV-файл на 50 000 записів.
2. Додає кожному рядку поле `timestamp` — випадкову дату в межах 2025 року.
3. Записує все в одну таблицю `students_burnout` у локальну базу SQLite.

Чому одна таблиця:
Кожен рядок датасету — це незалежний зріз показників конкретного студента.
Тут немає зв'язку «один-до-багатьох», який вимагав би нормалізації.
Методичка прямо дозволяє обмежитися однією таблицею.
"""

from datetime import datetime, timedelta
import sqlite3
import numpy as np
import pandas as pd

# --- Налаштування ---
CSV_PATH = "ai_student_impact_dataset.csv"
DB_PATH = "student_burnout.db"
TABLE_NAME = "students_burnout"

# Фіксуємо random seed, щоб дати були відтворюваними
np.random.seed(13)


def generate_random_2025_timestamps(n: int) -> list[str]:
  """Генерує n випадкових дат і часу в межах 2025 року (01.01–31.12)."""
  start = datetime(2025, 1, 1)
  end = datetime(2025, 12, 31, 23, 59, 59)
  total_seconds = int((end - start).total_seconds())

  random_offsets = np.random.randint(0, total_seconds, size=n)
  timestamps = [
      start + timedelta(seconds=int(offset)) for offset in random_offsets
  ]
  return [ts.strftime("%Y-%m-%d %H:%M:%S") for ts in timestamps]


def main():
  print(f"Читаємо CSV: {CSV_PATH}")
  df = pd.read_csv(CSV_PATH)
  print(f"Завантажено рядків: {len(df)}, стовпців: {len(df.columns)}")

  # Додаємо синтетичний timestamp
  df["timestamp"] = generate_random_2025_timestamps(len(df))

  # Переводимо назви колонок у нижній регістр для зручності роботи в SQL
  df.columns = [col.lower() for col in df.columns]

  # Перевірка на унікальність студентів
  n_unique = df["student_id"].nunique()
  print(
      f"Унікальних student_id: {n_unique} з {len(df)} записів "
      f"({'кожен студент має 1 запис' if n_unique == len(df) else 'є повтори'})"
  )

  # Записуємо в SQLite
  conn = sqlite3.connect(DB_PATH)
  df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

  # Перевіряємо кількість записаних рядків
  cursor = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
  count = cursor.fetchone()[0]
  print(f"Записано в таблицю '{TABLE_NAME}': {count} рядків")

  conn.close()
  print(f"База даних успішно збережена: {DB_PATH}")


if __name__ == "__main__":
  main()