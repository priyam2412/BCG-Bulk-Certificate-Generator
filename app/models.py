from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class CertificateJob(Base):
    __tablename__ = "certificate_jobs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="pending", nullable=False)
    total_recipients = Column(Integer, default=0, nullable=False)
    successful_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recipients = relationship("RecipientCertificate", back_populates="job")


class RecipientCertificate(Base):
    __tablename__ = "recipient_certificates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("certificate_jobs.id"), nullable=False)
    recipient_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    completion_date = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False)
    certificate_file = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job = relationship("CertificateJob", back_populates="recipients")
