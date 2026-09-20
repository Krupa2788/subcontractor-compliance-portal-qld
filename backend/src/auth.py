"""Caller identity and access rules.

API Gateway has already validated the JWT signature and expiry before the
Lambda runs, so the claims here are trustworthy. What it has *not* done is
decide what this particular caller may touch — that is this module's job.
"""

from dataclasses import dataclass

COMPLIANCE_OFFICER = "ComplianceOfficer"
SUBCONTRACTOR = "Subcontractor"


class AuthorizationError(Exception):
    """Caller is authenticated but not allowed to do this."""


@dataclass(frozen=True)
class Caller:
    user_id: str
    email: str
    groups: frozenset
    #: Set only for subcontractor logins: the one record they may act on.
    subcontractor_id: str | None

    @property
    def is_officer(self):
        return COMPLIANCE_OFFICER in self.groups

    @property
    def is_subcontractor(self):
        return SUBCONTRACTOR in self.groups

    def owns(self, subcontractor_id):
        return (
            self.subcontractor_id is not None
            and self.subcontractor_id == subcontractor_id
        )


def caller_from_event(event):
    claims = (
        (event.get("requestContext") or {}).get("authorizer") or {}
    ).get("claims") or {}

    if not claims:
        # Only reachable if a route is wired without the authorizer — fail
        # closed rather than defaulting to an anonymous caller with access.
        raise AuthorizationError("Unauthenticated")

    # cognito:groups arrives as a list when the event is synthesised in tests
    # and as a bracketed string through API Gateway's claim serialisation.
    raw_groups = claims.get("cognito:groups") or []
    if isinstance(raw_groups, str):
        raw_groups = raw_groups.strip("[]").replace(",", " ").split()

    subcontractor_id = claims.get("custom:subcontractorId") or None

    return Caller(
        user_id=claims.get("sub", ""),
        email=claims.get("email", ""),
        groups=frozenset(raw_groups),
        subcontractor_id=subcontractor_id,
    )


def require_officer(caller):
    if not caller.is_officer:
        raise AuthorizationError("Requires the ComplianceOfficer role")


def require_access_to(caller, subcontractor_id):
    """Officers may act on anyone; subcontractors only on themselves."""
    if caller.is_officer:
        return
    if caller.owns(subcontractor_id):
        return
    # Deliberately the same error whether the record is someone else's or does
    # not exist, so this cannot be used to probe which ids are real.
    raise AuthorizationError("Not permitted for this subcontractor")
