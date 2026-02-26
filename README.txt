## Requirements
- Python 3.12.x (Python 3.14 is currently not supported due to Scapy compatibility.)
- Node.js 18+ (includes npm)

## Recommended flow 
# 1. Create virtual environment (Python 3.12 required)
python3.12 -m venv venv

# 2. Activate
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

# 3. Install backend dependencies
pip install -r backend/requirements.txt

# 4. Run backend
uvicorn backend.main:app --reload --port 8000

# 5. Run frontend
cd frontend
npm install
npm run dev


## Model part for exploration
# generate data (run from project root) - python -m ds_insights_and_utils.generate_synthetic_data
# train model (run from project root) - python -m ds_insights_and_utils.train_model
# compare against baselines (run from project root) - python -m ds_insights_and_utils.evaluate_baselines
