# HomeMate

A home maintenance tracker app for managing appliances, vehicles, and home tasks. Includes AI-powered Q&A using local Ollama.

## Setup

```bash
# Create LXC container (Debian 12)
# Inside the LXC:

apt update && apt install -y python3 python3-pip python3-venv git

# Clone or copy this app
cd /opt
git clone <repo> homemate
cd homemate

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db init
flask db migrate -m "initial"
flask db upgrade

# Run (or set up with gunicorn + nginx)
flask run --host=0.0.0.0 --port=5000
```

## Features

### Appliances
- Track appliances (name, model, serial #, location, warranty)
- Upload PDF manuals (stored locally)
- Log maintenance history
- **AI Q&A** — Ask questions about any appliance

### Vehicles
- Track vehicles (make, model, year, VIN, mileage, license plate)
- Log maintenance with mileage
- **AI Q&A** — Ask questions about maintenance, schedules

### Home Tasks
- Recurring tasks (e.g., change HVAC filter every 90 days)
- One-time tasks
- Mark as complete → auto-calculates next due date
- Completion history tracking

### Predictions
- Automatic predictions based on maintenance history
- Shows upcoming maintenance for appliances and vehicles
- Dashboard alerts for overdue items

## AI Q&A Setup

The app uses a local Ollama instance for AI-powered questions.

**Requirements:**
- Ollama installed on a server (e.g., your AI server at `10.0.0.55`)
- A model pulled (e.g., `llama3.2`)

**Pull a model:**
```bash
ollama pull llama3.2
```

**Configure the AI server:**
Edit `ai_helper.py` and change `ollama_url` if your Ollama is at a different IP.

```python
ollama_url = "http://10.0.0.55:11434"
```

## Tech Stack

- Flask
- SQLite (built-in)
- Bootstrap 5 (CDN)
- PyPDF2 (PDF text extraction)
- Ollama (local AI)
