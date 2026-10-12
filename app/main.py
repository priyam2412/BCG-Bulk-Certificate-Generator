from __future__ import annotations

from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import CertificateJob, RecipientCertificate
from app.schemas import CertificateJobCreate, CertificateJobDetail, CertificateJobRead
from app.services.certificate_service import generate_certificate_pdf

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator API")
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


def validate_recipient_data(recipient: RecipientCertificate) -> None:
    if not recipient.recipient_name or not recipient.recipient_name.strip():
        raise ValueError("Recipient name is required")
    if not recipient.course_name or not recipient.course_name.strip():
        raise ValueError("Course name is required")
    if not recipient.completion_date or not recipient.completion_date.strip():
        raise ValueError("Completion date is required")
    if recipient.email and recipient.email.strip():
        try:
            validate_email(recipient.email, check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError(f"Invalid email address: {recipient.email}") from exc


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Bulk Certificate Generator API is running."}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/certificate-jobs", response_model=CertificateJobRead)
def create_certificate_job(
    payload: CertificateJobCreate,
    db: Session = Depends(get_db),
) -> CertificateJob:
    if not payload.recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one recipient is required.",
        )

    job = CertificateJob(
        status="pending",
        total_recipients=len(payload.recipients),
        successful_count=0,
        failed_count=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    for recipient in payload.recipients:
        db.add(
            RecipientCertificate(
                job_id=job.id,
                recipient_name=recipient.name,
                email=recipient.email,
                course_name=recipient.course_name,
                completion_date=recipient.completion_date,
                status="pending",
            )
        )
    db.commit()

    job.status = "processing"
    db.commit()
    db.refresh(job)

    successful_count = 0
    failed_count = 0

    for item in db.query(RecipientCertificate).filter(RecipientCertificate.job_id == job.id).all():
        try:
            validate_recipient_data(item)
            certificate_path = generate_certificate_pdf(
                recipient_name=item.recipient_name,
                course_name=item.course_name,
                completion_date=item.completion_date,
            )
            item.certificate_file = certificate_path
            item.status = "success"
            item.error_message = None
            successful_count += 1
        except Exception as exc:  # pragma: no cover - defensive path
            item.status = "failed"
            item.error_message = str(exc)
            item.certificate_file = None
            failed_count += 1
        finally:
            db.commit()

    job.successful_count = successful_count
    job.failed_count = failed_count
    job.status = "completed"
    db.commit()
    db.refresh(job)

    return job


@app.get("/certificate-jobs/{job_id}", response_model=CertificateJobDetail)
def get_certificate_job(
    job_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    recipients = (
        db.query(RecipientCertificate)
        .filter(RecipientCertificate.job_id == job.id)
        .order_by(RecipientCertificate.id)
        .all()
    )

    return {
        "job": {
            "id": job.id,
            "status": job.status,
            "total_recipients": job.total_recipients,
            "successful_count": job.successful_count,
            "failed_count": job.failed_count,
        },
        "recipients": [
            {
                "id": item.id,
                "recipient_name": item.recipient_name,
                "email": item.email,
                "course_name": item.course_name,
                "completion_date": item.completion_date,
                "status": item.status,
                "certificate_file": item.certificate_file,
                "error_message": item.error_message,
            }
            for item in recipients
        ],
    }


@app.get("/certificate-jobs/{job_id}/results")
def get_certificate_results(
    job_id: int,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    job = db.query(CertificateJob).filter(CertificateJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    recipients = (
        db.query(RecipientCertificate)
        .filter(RecipientCertificate.job_id == job.id)
        .order_by(RecipientCertificate.id)
        .all()
    )

    return [
        {
            "id": item.id,
            "recipient_name": item.recipient_name,
            "email": item.email,
            "course_name": item.course_name,
            "completion_date": item.completion_date,
            "status": item.status,
            "certificate_file": item.certificate_file,
            "error_message": item.error_message,
        }
        for item in recipients
    ]


@app.get("/certificates/{certificate_id}")
def download_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.query(RecipientCertificate).filter(RecipientCertificate.id == certificate_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if not record.certificate_file:
        raise HTTPException(status_code=404, detail="Certificate file is not available")

    file_path = Path(record.certificate_file)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file does not exist")

    return FileResponse(path=file_path, filename=file_path.name, media_type="application/pdf")
