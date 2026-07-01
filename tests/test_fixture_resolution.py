import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "source_trail.py"


def source() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def extract_allowed_answers() -> set[str]:
    text = source()
    names = re.findall(r'ANSWER_[A-Z_]+ = "([^"]+)"', text)
    return set(names)


def test_answer_buckets_are_oracle_resolution_buckets():
    assert extract_allowed_answers() == {
        "true",
        "false",
        "partly_true",
        "insufficient_evidence",
        "stale",
    }


def test_prompt_requires_source_trail_not_schema_only_result():
    text = source()
    prompt_section = text.split("def _derive_resolution", 1)[1].split("def _compare_resolutions", 1)[0]
    for phrase in [
        "source policy",
        "resolution rules",
        "submitted evidence",
        "cited_sources",
        "contradictions",
        "stale_sources",
    ]:
        assert phrase in prompt_section
    assert "Do not merely validate JSON shape" in prompt_section


def test_comparator_rejects_answer_confidence_and_contradiction_disagreement():
    text = source()
    comparator = text.split("def _compare_resolutions", 1)[1].split("def _normalize_resolution", 1)[0]
    assert 'leader.get("answer") != validator.get("answer")' in comparator
    assert 'leader.get("confidence_band") != validator.get("confidence_band")' in comparator
    assert "len(leader_contradictions) == 0 and len(validator_contradictions) > 0" in comparator
    assert "len(leader_contradictions) > 0 and len(validator_contradictions) == 0" in comparator


def test_resolution_packet_fields_are_json_backed_and_viewable():
    text = source()
    for storage_field in [
        "source_tiers_json",
        "cited_sources_json",
        "cited_domains_json",
        "key_findings_json",
        "contradictions_json",
        "stale_sources_json",
    ]:
        assert storage_field in text
    view_section = text.split("def get_resolution", 1)[1].split("def _derive_resolution", 1)[0]
    for view_key in [
        '"source_tiers"',
        '"cited_sources"',
        '"cited_domains"',
        '"key_findings"',
        '"contradictions"',
        '"stale_sources"',
    ]:
        assert view_key in view_section


def test_example_evidence_bundle_shape_is_valid_json():
    fixture = [
        {
            "url": "https://docs.example.org/changelog",
            "sourceTier": "official",
            "observedClaim": "The endpoint was added in v1.4.0 before the cutoff.",
            "retrievedAt": "2026-07-01T00:00:00Z",
        }
    ]
    encoded = json.dumps(fixture, separators=(",", ":"), sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded[0]["sourceTier"] == "official"
    assert decoded[0]["url"].startswith("https://")
