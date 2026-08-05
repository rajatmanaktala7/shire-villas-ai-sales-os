@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
start http://localhost:8000
uvicorn app:app --reload --host 0.0.0.0 --port 8000
