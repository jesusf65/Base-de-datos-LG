export PYTHONPATH=/app

echo " Ejecutando pre_start.py..."
python app/pre_start.py

python app/initial_data.py

echo " Iniciando FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000