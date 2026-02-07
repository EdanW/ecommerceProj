Before all (run from main folder) - pip install -r .\backend\requirements.txt
Server (run from main folder) - uvicorn backend.main:app --reload --port 8000
Client (run from frontend folder) - npm run dev