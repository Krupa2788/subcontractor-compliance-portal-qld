"""Scheduled re-evaluation of every subcontractor's compliance status.

Storing complianceStatus on the subcontractor record makes list reads cheap,
but that stored value only changes when something writes it. A certificate
that lapses overnight triggers no write, so without this job the record would
claim VALID indefinitely. EventBridge runs this daily to close that gap.
"""

import logging
from datetime import date

from models import derive_compliance_status
from repository import ComplianceDocumentRepository, SubcontractorRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
                "Compliance status changed for %s: %s -> %s",
                subcontractor_id,
                subcontractor.get("complianceStatus"),
                status.value,
            )

    logger.info("Recompute complete: %s checked, %s updated", checked, updated)
    return {"checked": checked, "updated": updated}
