from grantboard.app.models import Opportunity
from grantboard.app.pipeline import dedupe as dedupe_module


def test_dedupe_filters_existing_links(monkeypatch):
    monkeypatch.setattr(dedupe_module, "existing_sheet_links", lambda: {"https://example.com/grant"})
    monkeypatch.setattr(dedupe_module, "existing_db_links", lambda: set())

    opps = [
        Opportunity(
            opportunity_id="1",
            title="Grant",
            link="https://example.com/grant",
            source="Test",
        ),
        Opportunity(
            opportunity_id="2",
            title="Grant 2",
            link="https://example.com/grant-2",
            source="Test",
        ),
    ]

    results = list(dedupe_module.dedupe(opps))
    assert len(results) == 1
    assert results[0].link.endswith("grant-2")
