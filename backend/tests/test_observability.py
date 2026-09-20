import json
import logging

import pytest
from observability import JsonFormatter, observed


class FakeContext:
    aws_request_id = "req-123"


def event(method="GET", resource="/subcontractors", claims=None):
    payload = {"httpMethod": method, "resource": resource}
    if claims is not None:
        payload["requestContext"] = {"authorizer": {"claims": claims}}
    return payload


def captured(caplog):
    """The formatter is what produces JSON, so format the captured record
    rather than asserting on the raw message."""
    formatter = JsonFormatter()
    return [json.loads(formatter.format(r)) for r in caplog.records]


class TestJsonFormatter:
    def test_emits_valid_json_with_level_and_message(self):
        record = logging.LogRecord(
            "test", logging.INFO, __file__, 1, "hello", None, None
        )
        parsed = json.loads(JsonFormatter().format(record))
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello"

    def test_context_fields_are_promoted_to_top_level(self):
        # Nested fields would not be queryable in Logs Insights.
        record = logging.LogRecord(
            "test", logging.INFO, __file__, 1, "request", None, None
        )
        record.context = {"status": 403, "durationMs": 12.5}
        parsed = json.loads(JsonFormatter().format(record))
        assert parsed["status"] == 403
        assert parsed["durationMs"] == 12.5

    def test_non_serialisable_values_do_not_blow_up(self):
        record = logging.LogRecord(
            "test", logging.INFO, __file__, 1, "request", None, None
        )
        record.context = {"when": object()}
        json.loads(JsonFormatter().format(record))  # must not raise


class TestObserved:
    def test_passes_the_response_through_untouched(self):
        @observed
        def handler(event, context):
            return {"statusCode": 201, "body": "{}"}

        assert handler(event(), FakeContext()) == {"statusCode": 201, "body": "{}"}

    def test_logs_request_shape(self, caplog):
        @observed
        def handler(event, context):
            return {"statusCode": 200}

        with caplog.at_level(logging.INFO):
            handler(event(method="POST", resource="/subcontractors"), FakeContext())

        entry = captured(caplog)[-1]
        assert entry["method"] == "POST"
        assert entry["route"] == "/subcontractors"
        assert entry["status"] == 200
        assert entry["requestId"] == "req-123"
        assert isinstance(entry["durationMs"], float)

    def test_records_who_made_the_request(self, caplog):
        @observed
        def handler(event, context):
            return {"statusCode": 403}

        with caplog.at_level(logging.INFO):
            handler(
                event(
                    claims={
                        "sub": "user-1",
                        "email": "subbie@example.com",
                        "cognito:groups": ["Subcontractor"],
                    }
                ),
                FakeContext(),
            )

        entry = captured(caplog)[-1]
        assert entry["userId"] == "user-1"
        assert entry["userEmail"] == "subbie@example.com"
        assert entry["userGroups"] == ["Subcontractor"]
        assert entry["status"] == 403

    def test_anonymous_request_logs_without_user_fields(self, caplog):
        @observed
        def handler(event, context):
            return {"statusCode": 200}

        with caplog.at_level(logging.INFO):
            handler(event(), FakeContext())

        entry = captured(caplog)[-1]
        assert entry["userId"] is None
        assert entry["userGroups"] is None

    def test_exception_is_logged_then_re_raised(self, caplog):
        @observed
        def handler(event, context):
            raise RuntimeError("boom")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                handler(event(), FakeContext())

        entry = captured(caplog)[-1]
        assert entry["status"] == 500
        assert "boom" in entry["exception"]
