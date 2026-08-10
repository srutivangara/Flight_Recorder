# The Flight Recorder


## What it does

- Loads 400 labelled training sessions and 150 unlabeled evaluation sessions.
- Verifies append-only SHA-256 hash chains.
- Predicts one of the 8 root-cause classes for evaluation sessions.
- Locates the likely first-cause span.
- Shows the trace as a readable timeline.
- Flags high-risk actions that should require human confirmation.
- Provides an investigation dashboard.

## Key Results

### D1 – Integrity Check
Found **5 doctored sessions** with broken hash chains:
- eval-sess-0001
- eval-sess-0025
- eval-sess-0035
- eval-sess-0061
- eval-sess-0126

### D3 – Predictions
File: `predictions.json`  
Contains `root_cause` + `first_cause_span` for all 150 evaluation sessions.

### D4 – Confirmation Policy
File: `policy.json`  
Confirms only high-risk tools (money movement, external email, file sharing, government filing, infrastructure changes, high expected loss).

## How to run

1. Install Dependencies

Make sure Python 3.x is installed.

pip install -r requirements.txt
2. Start the Application
python app.py
3. Open the Dashboard

Open the following URL in your browser:

http://127.0.0.1:5000

Keep the terminal running while using the application.

## Project Structure
```bash
The-Flight-Recorder/
├── app.py
├── requirements.txt
├── predictions.json
├── policy.json
├── assets/
├── data/
└── README.md
```
## Quick Start

pip install -r requirements.txt
python app.py

## Then open:

http://127.0.0.1:5000
