"""Smoke tests on a disposable SQLite copy; never alter the supplied database."""
import importlib
import os
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('learnwell_lab4')
    temp_db = tmp / 'student_burnout_test.db'
    shutil.copy2(ROOT / 'data' / 'student_burnout_lab4.db', temp_db)
    os.environ['LEARNWELL_DB_PATH'] = str(temp_db)
    os.environ['LEARNWELL_MODEL_PATH'] = str(tmp / 'model.joblib')
    import app.config, app.database.database, app.database.crud, app.services.model
    import app.endpoints.training, app.endpoints.inference, app.main
    for module in [app.config, app.database.database, app.database.crud,
                   app.services.model, app.endpoints.training,
                   app.endpoints.inference, app.main]:
        importlib.reload(module)
    with TestClient(app.main.app) as api:
        yield api
    os.environ.pop('LEARNWELL_DB_PATH', None)
    os.environ.pop('LEARNWELL_MODEL_PATH', None)


def test_training_and_database(client):
    assert client.get('/health').json()['status'] == 'ok'
    from app.database.database import connect
    with connect() as db:
        train_before = db.execute("SELECT COUNT(*) FROM predictions WHERE source='train'").fetchone()[0]
        hold_before = db.execute('SELECT COUNT(*) FROM holdout_evaluations').fetchone()[0]
    response = client.post('/train-model')
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['model'] == 'Logistic Regression'
    assert result['total_records'] == 50000
    assert result['train_records'] == 45000
    assert result['holdout_records'] == 5000
    assert result['train_predictions_saved'] == 45000
    assert 0.0 <= result['metrics_holdout']['f1_macro'] <= 1.0

    from app.database.database import connect
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM predictions WHERE source='train'").fetchone()[0] == train_before + 45000
        assert db.execute('SELECT COUNT(*) FROM holdout_evaluations').fetchone()[0] == hold_before + 5000
        assert db.execute('SELECT COUNT(*) FROM lab3_predictions').fetchone()[0] == 250000
        assert db.execute('SELECT COUNT(*) FROM students_burnout_features WHERE timestamp IS NULL').fetchone()[0] == 0


def test_inference_from_id_and_json(client):
    from app.database.database import connect
    with connect() as db:
        inference_before = db.execute("SELECT COUNT(*) FROM predictions WHERE source='inference'").fetchone()[0]
        inputs_before = db.execute('SELECT COUNT(*) FROM inference_inputs').fetchone()[0]
    r1 = client.post('/predict', json={'student_id':100001})
    assert r1.status_code == 200, r1.text
    assert r1.json()['prediction'] in {'Low','Medium','High'}
    assert abs(sum(r1.json()['probabilities'].values())-1) < 1e-8

    example = client.get('/example-input').json()
    assert list(example) == ['features']
    r2 = client.post('/predict', json=example)
    assert r2.status_code == 200, r2.text
    assert r1.json()['prediction'] == r2.json()['prediction']
    assert r2.json()['prediction_id'] != r1.json()['prediction_id']

    from app.database.database import connect
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM predictions WHERE source='inference'").fetchone()[0] == inference_before + 2
        assert db.execute('SELECT COUNT(*) FROM inference_inputs').fetchone()[0] == inputs_before + 2
        assert db.execute('SELECT COUNT(*) FROM inference_inputs WHERE input_origin="database"').fetchone()[0] >= 1
        assert db.execute('SELECT COUNT(*) FROM inference_inputs WHERE input_origin="json"').fetchone()[0] >= 1
    assert client.post('/predict',json={'student_id':-2}).status_code == 422
    assert client.post('/predict',json={'student_id':9999999}).status_code == 404
    assert client.post('/predict',json={'student_id':100001,'features':example['features']}).status_code == 422
    assert client.get('/predictions').status_code == 200
