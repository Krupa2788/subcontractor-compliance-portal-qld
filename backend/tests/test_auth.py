import pytest
from auth import (
    AuthorizationError,
    caller_from_event,
    require_access_to,
    require_officer,
)

OFFICER_SUB = "11111111-1111-1111-1111-111111111111"
SUBBIE_SUB = "22222222-2222-2222-2222-222222222222"
OWNED_ID = "sub-abc"
OTHER_ID = "sub-xyz"


def event_with(claims):
    return {"requestContext": {"authorizer": {"claims": claims}}}


def officer_event():
    return event_with(
        {
            "sub": OFFICER_SUB,
            "email": "officer@example.com.au",
            "cognito:groups": ["ComplianceOfficer"],
        }
    )


def subbie_event(subcontractor_id=OWNED_ID):
    return event_with(
        {
            "sub": SUBBIE_SUB,
            "email": "subbie@example.com.au",
            "cognito:groups": ["Subcontractor"],
            "custom:subcontractorId": subcontractor_id,
        }
    )


class TestCallerParsing:
    def test_reads_officer_identity(self):
        caller = caller_from_event(officer_event())
        assert caller.is_officer
        assert not caller.is_subcontractor
        assert caller.email == "officer@example.com.au"
        assert caller.subcontractor_id is None

    def test_reads_subcontractor_identity(self):
        caller = caller_from_event(subbie_event())
        assert caller.is_subcontractor
        assert not caller.is_officer
        assert caller.subcontractor_id == OWNED_ID

    def test_parses_groups_serialised_as_a_string(self):
        # API Gateway flattens the claim to "[GroupA GroupB]".
        caller = caller_from_event(
            event_with({"sub": "x", "cognito:groups": "[ComplianceOfficer]"})
        )
        assert caller.is_officer

    def test_missing_claims_fail_closed(self):
        # A route wired without the authorizer must not yield a usable caller.
        with pytest.raises(AuthorizationError):
            caller_from_event({})
        with pytest.raises(AuthorizationError):
            caller_from_event({"requestContext": {}})

    def test_group_with_no_membership_is_neither_role(self):
        caller = caller_from_event(event_with({"sub": "x", "email": "a@b.c"}))
        assert not caller.is_officer
        assert not caller.is_subcontractor


class TestAccessRules:
    def test_officer_may_act_on_anyone(self):
        caller = caller_from_event(officer_event())
        require_access_to(caller, OWNED_ID)
        require_access_to(caller, OTHER_ID)
        require_officer(caller)

    def test_subcontractor_may_act_on_own_record(self):
        caller = caller_from_event(subbie_event())
        require_access_to(caller, OWNED_ID)

    def test_subcontractor_may_not_touch_another_record(self):
        caller = caller_from_event(subbie_event())
        with pytest.raises(AuthorizationError):
            require_access_to(caller, OTHER_ID)

    def test_subcontractor_is_not_an_officer(self):
        caller = caller_from_event(subbie_event())
        with pytest.raises(AuthorizationError):
            require_officer(caller)

    def test_caller_with_no_group_is_denied(self):
        caller = caller_from_event(event_with({"sub": "x", "email": "a@b.c"}))
        with pytest.raises(AuthorizationError):
            require_access_to(caller, OWNED_ID)
        with pytest.raises(AuthorizationError):
            require_officer(caller)

    def test_subcontractor_without_binding_owns_nothing(self):
        # A Subcontractor login missing custom:subcontractorId must not become
        # a wildcard that matches every record.
        caller = caller_from_event(
            event_with({"sub": "x", "cognito:groups": ["Subcontractor"]})
        )
        assert not caller.owns(OWNED_ID)
        assert not caller.owns(None)
        with pytest.raises(AuthorizationError):
            require_access_to(caller, OWNED_ID)
