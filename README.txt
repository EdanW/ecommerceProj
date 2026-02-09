Before all (run from project root) - pip install -r .\backend\requirements.txt
Server (run from project root) - uvicorn backend.main:app --reload --port 8000
Client (run from frontend folder) - npm run dev

* generate data (run from project root) - python -m backend.ds_service.data.generate_synthetic_data