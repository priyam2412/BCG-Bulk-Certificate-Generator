import os
from pathlib import Path

os.environ["CERTIFICATES_DB_PATH"] = "sqlite:///./test_certificates.db"

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import CertificateJob, RecipientCertificate
from app.services import certificate_service


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(RecipientCertificate).delete()
        db.query(CertificateJob).delete()
        db.commit()
    finally:
        db.close()


client = TestClient(app)


def test_root_endpoint():
    reset_db()
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Bulk Certificate Generator API is running."


def test_health_endpoint():
    reset_db()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_frontend_is_served():
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "Bulk Certificate Generator" in response.text


def test_create_certificate_job_and_get_status():
    reset_db()
    payload = {
        "recipients": [
            {
                "name": "Alice Sharma",
                "email": "alice@example.com",
                "course_name": "Python Fundamentals",
                "completion_date": "2026-10-10",
            },
            {
                "name": "Bob Kumar",
                "email": "invalid-email",
                "course_name": "Python Fundamentals",
                "completion_date": "2026-10-10",
            },
        ]
    }

    response = client.post("/certificate-jobs", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["total_recipients"] == 2
    assert result["successful_count"] == 1
    assert result["failed_count"] == 1
    assert result["status"] == "completed"

    job_detail = client.get(f"/certificate-jobs/{result['id']}")
    assert job_detail.status_code == 200
    detail = job_detail.json()
    assert len(detail["recipients"]) == 2
    assert sum(1 for r in detail["recipients"] if r["status"] == "success") == 1

    success_certificate = next(r for r in detail["recipients"] if r["status"] == "success")
    certificate_response = client.get(f"/certificates/{success_certificate['id']}")
    assert certificate_response.status_code == 200
    assert certificate_response.headers["content-type"].startswith("application/pdf")


def test_input_validation_marks_invalid_recipient_and_continues():
    reset_db()
    payload = {
        "recipients": [
            {"name": "", "course_name": "Python Fundamentals", "completion_date": "2026-10-10"},
            {"name": "Charlie", "email": "charlie@example.com", "course_name": "Python Fundamentals", "completion_date": "2026-10-10"},
        ]
    }

    response = client.post("/certificate-jobs", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["successful_count"] == 1
    assert result["failed_count"] == 1
    assert result["total_recipients"] == 2


def test_certificate_generation_creates_a_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(certificate_service, "OUTPUT_DIR", str(tmp_path))

    certificate_path = certificate_service.generate_certificate_pdf(
        recipient_name="Dana Example",
        course_name="Python Fundamentals",
        completion_date="2026-10-10",
    )

    generated_file = Path(certificate_path)
    assert generated_file.exists()
    assert generated_file.suffix == ".pdf"
    assert generated_file.read_bytes().startswith(b"%PDF")


def test_individual_generation_failure_does_not_stop_other_recipients(monkeypatch):
    reset_db()
    original_generate = certificate_service.generate_certificate_pdf

    def fail_for_one_recipient(recipient_name: str, course_name: str, completion_date: str) -> str:
        if recipient_name == "Fails Generation":
            raise RuntimeError("simulated PDF generation failure")
        return original_generate(recipient_name, course_name, completion_date)

    monkeypatch.setattr("app.main.generate_certificate_pdf", fail_for_one_recipient)
    payload = {
        "recipients": [
            {
                "name": "Fails Generation",
                "course_name": "Python Fundamentals",
                "completion_date": "2026-10-10",
            },
            {
                "name": "Succeeds Generation",
                "course_name": "Python Fundamentals",
                "completion_date": "2026-10-10",
            },
        ]
    }

    response = client.post("/certificate-jobs", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["successful_count"] == 1
    assert result["failed_count"] == 1

    detail = client.get(f"/certificate-jobs/{result['id']}").json()
    failed = next(item for item in detail["recipients"] if item["recipient_name"] == "Fails Generation")
    successful = next(item for item in detail["recipients"] if item["recipient_name"] == "Succeeds Generation")
    assert failed["status"] == "failed"
    assert failed["error_message"] == "simulated PDF generation failure"
    assert successful["status"] == "success"
    assert successful["certificate_file"] is not None


def test_results_endpoint_returns_all_certificate_results():
    reset_db()
    response = client.post(
        "/certificate-jobs",
        json={
            "recipients": [
                {
                    "name": "Results User",
                    "course_name": "Python Fundamentals",
                    "completion_date": "2026-10-10",
                }
            ]
        },
    )
    job_id = response.json()["id"]

    results_response = client.get(f"/certificate-jobs/{job_id}/results")
    assert results_response.status_code == 200
    results = results_response.json()
    assert len(results) == 1
    assert results[0]["recipient_name"] == "Results User"
    assert results[0]["status"] == "success"
    assert results[0]["certificate_file"] is not None


def test_missing_required_recipient_field_is_reported():
    reset_db()
    response = client.post(
        "/certificate-jobs",
        json={
            "recipients": [
                {
                    "name": "Missing Course",
                    "completion_date": "2026-10-10",
                }
            ]
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["failed_count"] == 1
    assert result["successful_count"] == 0


def test_empty_recipients_are_rejected():
    reset_db()
    response = client.post("/certificate-jobs", json={"recipients": []})
    assert response.status_code == 400
    assert "At least one recipient" in response.json()["detail"]
