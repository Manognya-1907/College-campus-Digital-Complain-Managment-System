# Campus Compliance / Ticketing System

Simple role-based campus ticketing system built with:

- FastAPI backend
- SQLite + SQLAlchemy
- JWT authentication
- Streamlit frontend
- Simulated notification logs

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Backend

```bash
uvicorn backend.main:app --reload
```

Backend runs at `http://127.0.0.1:8000`.

## Run Frontend

Open a new terminal:

```bash
streamlit run frontend/streamlit_app.py
```

Frontend runs at `http://localhost:8501`.

## Notes

- Department users should register with their **department name** in the `name` field (example: `IT`, `Library`) to receive assigned tickets from students.
- Notifications are currently simulated using console logs in `backend/notifications.py`.
- To use SMTP email, replace the notification functions with your mail sender logic.
