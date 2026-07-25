from __future__ import annotations

from services.readiness_service import (
    ReadinessCheck,
    ReadinessReport,
)


def test_failed_required_check_blocks_readiness() -> None:
    report = ReadinessReport(
        id="report-1",
        created_at="2026-01-01T00:00:00+00:00",
        project_root=".",
        python_version="3.12.0",
        platform="test",
        checks=[
            ReadinessCheck(
                key="python",
                title="Python",
                status="passed",
                message="OK",
            ),
            ReadinessCheck(
                key="models",
                title="Models",
                status="failed",
                message="Missing",
                required=True,
            ),
        ],
    )

    assert report.ready is False
    assert report.required_failure_count == 1


def test_optional_failure_does_not_block_readiness() -> None:
    report = ReadinessReport(
        id="report-2",
        created_at="2026-01-01T00:00:00+00:00",
        project_root=".",
        python_version="3.12.0",
        platform="test",
        checks=[
            ReadinessCheck(
                key="python",
                title="Python",
                status="passed",
                message="OK",
            ),
            ReadinessCheck(
                key="optional",
                title="Optional",
                status="failed",
                message="Unavailable",
                required=False,
            ),
        ],
    )

    assert report.ready is True


def test_report_serialisation_contains_totals() -> None:
    report = ReadinessReport(
        id="report-3",
        created_at="2026-01-01T00:00:00+00:00",
        project_root=".",
        python_version="3.12.0",
        platform="test",
        checks=[
            ReadinessCheck(
                key="one",
                title="One",
                status="passed",
                message="OK",
            ),
            ReadinessCheck(
                key="two",
                title="Two",
                status="warning",
                message="Warning",
            ),
        ],
    )

    data = report.to_dict()

    assert data["ready"] is True
    assert data["passed_count"] == 1
    assert data["warning_count"] == 1
    assert data["failed_count"] == 0