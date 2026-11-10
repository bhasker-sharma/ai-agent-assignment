from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Decision = Literal["FILE", "DO_NOT_FILE", "NEEDS_MORE_INFO"]
RdrType = Literal[
    "Inspection - Incorrect Violation",
    "Inspection - Assigned to Wrong Carrier",
    "Inspection - Citation with Associated Violation",
    "Inspection - Duplicate Record",
    "Inspection - Incorrect Information",
    "Crash Preventability Determination",
]


class Case(BaseModel):
    """One case from a case file. Extra fields (e.g. crash_type, injuries) are kept and reviewed."""

    model_config = ConfigDict(extra="allow")

    case_id: str
    record_type: str
    event_date: date
    staff_note: str = ""
    evidence_files: list[str] = Field(default_factory=list)
    # Only for POST /review, where one case arrives without its case file. Defaults to today.
    as_of_date: date | None = None


class CaseFile(BaseModel):
    """A case file such as data/cases/dev_cases.json."""

    as_of_date: date
    cases: list[Case]


class Citation(BaseModel):
    source: str
    section: str


class ReviewResult(BaseModel):
    """One entry of predictions.json, matching data/output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    decision: Decision
    rdr_type: RdrType | None
    reason: str
    citations: list[Citation]
    evidence_used: list[str]
    draft_narrative: str | None
    confidence: float = Field(ge=0, le=1)
