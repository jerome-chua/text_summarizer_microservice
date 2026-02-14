# Text Summarizer Microservice

A ZMQ-based microservice that summarizes text using an LLM (Groq) with a simple sentence-extraction fallback.

## Prerequisites

- Python 3.10+
- A [Groq](https://console.groq.com) API key (for LLM summarization)

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv venv
```

### 2. Activate the virtual environment

**macOS / Linux:**

```bash
source venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
venv\Scripts\activate.bat
```

**Windows (PowerShell):**

```powershell
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Create a `.env` file in the project root with your Groq API key:

```
GROQ_API_KEY=your_api_key_here
```

Get an API key at [Groq Console](https://console.groq.com).

## Running the service

With the virtual environment activated:

```bash
python main.py
```

You should see:

```
Text Summarizer Microservice running on: Port 5555
```

The service listens on **TCP port 5555**. Send JSON requests with `text` and optional `max_sentences`; it responds with `summary` (and `fallback_used` when the basic summarizer was used instead of the LLM).
