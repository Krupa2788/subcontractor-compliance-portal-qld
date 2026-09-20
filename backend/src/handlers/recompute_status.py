"""Scheduled re-evaluation of every subcontractor's compliance status.

Storing complianceStatus on the subcontractor record makes list reads cheap,
but that stored value only changes when something writes it. A certificate
that lapses overnight triggers no write, so without this job the record would
claim VALID indefinitely. EventBridge runs this daily to close that gap.
"""

from datetime import date

from models import derive_compliance_status
from observability import logger
from repository import ComplianceDocumentRepository, SubcontractorRepository

subcontractors = SubcontractorRepository()
documents = ComplianceDocumentRepository()


def handler(event, context):
    today = date.today()
    checked = 0
    updated = 0

    for subcontractor in subcontractors.list():
        checked += 1
        subcontractor_id = subcontractor["id"]
        status = derive_compliance_status(
            documents.list_by_subcontractor(subcontractor_id), today
        )
        if status.value != subcontractor.get("complianceStatus"):
            subcontractors.set_compliance_status(subcontractor_id, status.value)
            updated += 1
            logger.info(
                "compliance status changed",
                extra={
                    "context": {
                        "subcontractorId": subcontractor_id,
                        "from": subcontractor.get("complianceStatus"),
                        "to": status.value,
                    }
                },
            )

    logger.info(
        "recompute complete",
        extra={"context": {"checked": checked, "updated": updated}},
    )
    return {"checked": checked, "updated": updated}
