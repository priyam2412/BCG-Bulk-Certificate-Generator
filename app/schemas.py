from typing import Optional

from pydantic import BaseModel, Field


class RecipientInput(BaseModel):
    name: Optional[str] = Field(default=None)
    email: Optional[str] = None
    course_name: Optional[str] = Field(default=None)
    completion_date: Optional[str] = Field(default=None)


class CertificateJobCreate(BaseModel):
    recipients: list[RecipientInput]


class RecipientResult(BaseModel):
    id: int
    recipient_name: str
    email: Optional[str]
    course_name: str
    completion_date: str
    status: str
    certificate_file: Optional[str] = None
    error_message: Optional[str] = None


class CertificateJobRead(BaseModel):
    id: int
    status: str
    total_recipients: int
    successful_count: int
    failed_count: int


class CertificateJobDetail(BaseModel):
    job: CertificateJobRead
    recipients: list[RecipientResult]
