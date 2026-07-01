import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "source_trail.py"
README = ROOT / "README.md"
CONSENSUS_DOC = ROOT / "docs" / "consensus-design.md"
EXAMPLES_DOC = ROOT / "docs" / "examples.md"


def read_contract() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_contract_exists_and_uses_pinned_genvm_runner():
    source = read_contract()
    first_line = source.splitlines()[0]
    assert first_line == '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
    assert "py-genlayer:test" not in source
    assert "py-genlayer:latest" not in source


def test_contract_declares_oracle_state():
    source = read_contract()
    for name in ["Question", "EvidenceBundle", "Resolution", "Challenge"]:
        assert f"class {name}" in source
    for field in [
        "questions: TreeMap[str, Question]",
        "evidence_bundles: TreeMap[str, EvidenceBundle]",
        "resolutions: TreeMap[str, Resolution]",
        "question_order: DynArray[str]",
    ]:
        assert field in source


def test_contract_has_public_question_evidence_resolution_methods():
    source = read_contract()
    for method in [
        "create_question",
        "submit_evidence",
        "resolve_question",
        "challenge_resolution",
        "get_question",
        "get_evidence",
        "get_resolution",
    ]:
        assert re.search(rf"def {method}\(", source), method


def test_contract_uses_custom_comparative_validator_not_format_only_validation():
    source = read_contract()
    assert "gl.vm.run_nondet_unsafe" in source
    assert "validator_fn" in source
    assert "leader_fn" in source
    assert "_compare_resolutions" in source
    assert "format-only" in source.lower() or "schema validator" in source.lower()
    assert "strict_eq(" not in source


def test_contract_compares_evidence_trail_fields():
    source = read_contract()
    for phrase in [
        "answer",
        "confidence_band",
        "cited_domains",
        "source_tiers",
        "contradictions",
        "_domains_from_sources",
    ]:
        assert phrase in source


def test_contract_uses_storage_types_not_builtin_storage_collections():
    source = read_contract()
    storage_section = source.split("class SourceTrail(gl.Contract):", 1)[1].split("def __init__", 1)[0]
    assert "TreeMap" in storage_section
    assert "DynArray" in storage_section
    assert not re.search(r":\s*dict\b", storage_section)
    assert not re.search(r":\s*list\b", storage_section)


def test_docs_explain_consensus_and_examples():
    readme = README.read_text(encoding="utf-8")
    consensus = CONSENSUS_DOC.read_text(encoding="utf-8")
    examples = EXAMPLES_DOC.read_text(encoding="utf-8")
    combined = readme + consensus
    for phrase in ["evidence-trail", "Validators", "cited domains", "source-quality tiers"]:
        assert phrase in combined
    for phrase in ["protocol announcement", "github issue", "documentation-change", "event/outage"]:
        assert phrase in examples.lower()
