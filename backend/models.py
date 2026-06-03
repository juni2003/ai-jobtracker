"""
models.py — Pydantic v2 schemas shared by both Pakistan and Remote pipelines.
"""

from pydantic   import BaseModel, Field
from typing     import Optional
from datetime   import datetime
from enum       import Enum


# ── Status Kanban columns ─────────────────────────────────────────────────────
class JobStatus(str, Enum):
    inbox        = "Inbox"
    applied      = "Applied"
    interviewing = "Interviewing"
    rejected     = "Rejected"
    ghosted      = "Ghosted"
    offer        = "Offer"


# ── Job type marker ───────────────────────────────────────────────────────────
class JobType(str, Enum):
    pakistan = "pakistan"
    remote   = "remote"


# ── Base schema (fields every job has) ───────────────────────────────────────
class JobBase(BaseModel):
    title               : str
    company             : str
    location            : Optional[str] = None   # raw location string
    office_city         : Optional[str] = None   # extracted city name
    is_remote           : bool          = False
    apply_link          : Optional[str] = None
    contact_email       : Optional[str] = None
    salary              : Optional[str] = None
    experience_required : Optional[str] = None   # e.g. "0-1 years", "Fresh"
    post_date           : Optional[str] = None
    description_snippet : Optional[str] = None   # first 300 chars of description
    source              : Optional[str] = None   # "adzuna" / "rozee" / "remotive" etc.
    source_url          : Optional[str] = None
    job_type            : JobType       = JobType.pakistan


# ── Insert schema ─────────────────────────────────────────────────────────────
class JobCreate(JobBase):
    status    : JobStatus = JobStatus.inbox
    scraped_at: datetime  = Field(default_factory=datetime.utcnow)


# ── API response schema ───────────────────────────────────────────────────────
class JobOut(JobBase):
    id        : str
    status    : JobStatus
    scraped_at: datetime

    model_config = {"from_attributes": True}


# ── Status update body ────────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: JobStatus
