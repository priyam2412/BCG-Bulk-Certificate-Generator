# Bulk Certificate Generator

A FastAPI backend and basic browser frontend for generating certificates in bulk from one predefined PDF template.

The application accepts one request containing multiple recipients, validates each recipient independently, generates a certificate for every valid recipient, records successful and failed results, and provides certificate download links.

## Features

- Bulk certificate generation from one API request
- One predefined certificate template generated as a PDF
- Per-recipient validation
- Per-recipient success and failure status
- Failure isolation: one failed certificate does not stop the remaining recipients
- Database-backed job and recipient tracking
- Job status, progress counts, and detailed results
- Generated certificate PDF downloads
- Basic browser frontend for demonstrating all major features
- Automated tests for the required assignment behavior

## Technology

- Python 3.13
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite for local development
- ReportLab for PDF generation
- Pytest and FastAPI TestClient for testing

## Project structure

```text
BCG/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── services/
│       └── certificate_service.py
├── static/
│   └── index.html
├── tests/
│   ├── conftest.py
│   └── test_app.py
├── generated_certificates/
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt
```

## Setup

Open PowerShell in the project directory:

```powershell
cd "C:\Users\priya\OneDrive\Desktop\BCG"
```

Create the virtual environment if it does not already exist:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, run the following in the current PowerShell session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run the application

Start the FastAPI server:

```powershell
uvicorn app.main:app --reload
```

The server is available at:

- API root: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive Swagger documentation: http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc
- Basic browser frontend: http://127.0.0.1:8000/ui/

Keep the PowerShell window running while using the application.

## Basic frontend

Open http://127.0.0.1:8000/ui/ in a browser.

The frontend allows you to:

1. Enter or edit a JSON array of recipients.
2. Submit a bulk certificate generation job.
3. View the generated job ID.
4. View job status and progress.
5. See successful and failed recipient records.
6. See the error message for an individual failed recipient.
7. Refresh an existing job by entering its job ID.
8. Download successful certificate PDFs.

The page includes an example with one valid recipient and one invalid email address so that both success and failure behavior can be demonstrated immediately.

## API endpoints

### Health check

```http
GET /health
```

Example response:

```json
{
  "status": "ok"
}
```

### Create a certificate generation job

```http
POST /certificate-jobs
Content-Type: application/json
```

Request body:

```json
{
  "recipients": [
    {
      "name": "Alice Sharma",
      "email": "alice@example.com",
      "course_name": "Python Fundamentals",
      "completion_date": "2026-10-10"
    },
    {
      "name": "Bob Kumar",
      "email": "bob@example.com",
      "course_name": "Python Fundamentals",
      "completion_date": "2026-10-10"
    }
  ]
}
```

Example response:

```json
{
  "id": 1,
  "status": "completed",
  "total_recipients": 2,
  "successful_count": 2,
  "failed_count": 0
}
```

PowerShell example:

```powershell
$body = @{
    recipients = @(
        @{
            name = "Alice Sharma"
            email = "alice@example.com"
            course_name = "Python Fundamentals"
            completion_date = "2026-10-10"
        },
        @{
            name = "Bob Kumar"
            email = "bob@example.com"
            course_name = "Python Fundamentals"
            completion_date = "2026-10-10"
        }
    )
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/certificate-jobs" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Get job status and detailed results

```http
GET /certificate-jobs/{job_id}
```

Example response:

```json
{
  "job": {
    "id": 1,
    "status": "completed",
    "total_recipients": 2,
    "successful_count": 1,
    "failed_count": 1
  },
  "recipients": [
    {
      "id": 1,
      "recipient_name": "Alice Sharma",
      "email": "alice@example.com",
      "course_name": "Python Fundamentals",
      "completion_date": "2026-10-10",
      "status": "success",
      "certificate_file": "generated_certificates/Alice_Sharma_1234567890.pdf",
      "error_message": null
    },
    {
      "id": 2,
      "recipient_name": "Bob Kumar",
      "email": "invalid-email",
      "course_name": "Python Fundamentals",
      "completion_date": "2026-10-10",
      "status": "failed",
      "certificate_file": null,
      "error_message": "Invalid email address: invalid-email"
    }
  ]
}
```

Progress is calculated as:

```text
(successful_count + failed_count) / total_recipients * 100
```

### Get certificate results

```http
GET /certificate-jobs/{job_id}/results
```

This returns the per-recipient results for a job.

### Download a generated certificate

```http
GET /certificates/{certificate_id}
```

Successful records return a PDF file. A failed record returns an error because no certificate file is available.

## Validation and failure handling

The application validates recipients individually:

- `name` is required
- `course_name` is required
- `completion_date` is required
- `email` is optional, but if provided it must have a valid format

Invalid recipient input is stored as a failed recipient record. It does not stop valid recipients from being processed.

Certificate-generation exceptions are also isolated to the individual recipient. The failed record stores the error message, while the remaining recipients continue processing.

## Database

The default database is SQLite:

```text
certificates.db
```

The database contains:

- `certificate_jobs`
  - overall job status and counts
- `recipient_certificates`
  - input data, per-recipient status, generated file path, and error message

For tests, the database URL is overridden with `test_certificates.db` and the test schema is reset between tests.

## Certificate output

Generated files are stored in:

```text
generated_certificates/
```

Each PDF uses the same predefined layout and includes:

- Certificate of Completion title
- Recipient name
- Course name
- Completion date

## Run tests

Make sure the virtual environment is activated:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run the complete test suite:

```powershell
pytest -q
```

The tests cover:

- Creating a generation job
- Input validation
- Empty recipient-list handling
- Missing required recipient fields
- Invalid email handling
- PDF certificate generation
- Job status and progress counts
- Individual certificate-generation failure
- Continuing valid processing after a failure
- Retrieving job results
- Downloading generated certificates
- Serving the browser frontend

## Design decisions

### FastAPI

FastAPI was selected because it provides:

- Pydantic request validation
- automatic OpenAPI documentation
- simple dependency injection for database sessions
- straightforward testing with `TestClient`

### Synchronous processing

The current implementation processes the recipient list synchronously inside the request. This keeps the project simple, easy to understand, and easy to debug while meeting the bulk-generation requirement.

For very large production workloads, the processing loop could be moved to a worker queue such as Celery, RQ, or a dedicated task service. The existing job and per-recipient status model is suitable for that future change.

### One predefined template

The assignment requires only one certificate design, so the implementation uses one ReportLab template rather than introducing a template editor or multiple designs.

### Per-recipient status

Storing each recipient as its own database record makes it possible to identify exactly which certificates succeeded, which failed, and why.

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run commands from the project root:

```powershell
cd "C:\Users\priya\OneDrive\Desktop\BCG"
.\.venv\Scripts\Activate.ps1
pytest -q
```

The repository includes `pytest.ini` and `tests/conftest.py` so the project root is available during test collection.

### PowerShell activation is blocked

Use a process-scoped execution-policy change:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Port 8000 is already in use

Start the server on another port:

```powershell
uvicorn app.main:app --reload --port 8001
```

Then open:

```text
http://127.0.0.1:8001/ui/
```
