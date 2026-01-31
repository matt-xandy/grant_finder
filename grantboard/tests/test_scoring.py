from grantboard.app.models import Opportunity
from grantboard.app.pipeline.score import heuristic_score


def test_scoring_high_match():
    opp = Opportunity(
        opportunity_id="1",
        title="Chronic pain education grant",
        link="https://example.com",
        source="Test",
        raw_text="We support chronic pain awareness and education.",
    )
    score, notes = heuristic_score(opp)
    assert score == 5
    assert "alignment" in notes.lower()
