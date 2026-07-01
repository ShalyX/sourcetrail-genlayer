# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
from dataclasses import dataclass
import json


ERROR_EXPECTED = "[EXPECTED]"
ERROR_LLM = "[LLM_ERROR]"

ANSWER_TRUE = "true"
ANSWER_FALSE = "false"
ANSWER_PARTLY = "partly_true"
ANSWER_INSUFFICIENT = "insufficient_evidence"
ANSWER_STALE = "stale"


@allow_storage
@dataclass
class Question:
    creator: Address
    title: str
    claim: str
    source_policy_json: str
    resolution_rules_json: str
    deadline_iso: str
    status: str
    evidence_count: u256
    created_at: str
    resolution_id: str


@allow_storage
@dataclass
class EvidenceBundle:
    question_id: str
    submitter: Address
    position: str
    evidence_json: str
    notes: str
    created_at: str


@allow_storage
@dataclass
class Resolution:
    question_id: str
    answer: str
    confidence_band: str
    source_tiers_json: str
    cited_sources_json: str
    cited_domains_json: str
    key_findings_json: str
    contradictions_json: str
    stale_sources_json: str
    rationale: str
    resolved_at: str


@allow_storage
@dataclass
class Challenge:
    question_id: str
    challenger: Address
    reason: str
    counter_evidence_json: str
    status: str
    created_at: str


class SourceTrail(gl.Contract):
    """Evidence-trail oracle for claims that deterministic feeds cannot settle.

    SourceTrail is not a schema validator and not a generic LLM wrapper. The
    leader derives a source-backed answer, validators independently derive their
    own answer from the same claim/source policy/evidence, then compare stable
    evidence-trail fields: answer bucket, confidence band, cited domains, source
    tiers, and contradiction flags.
    """

    owner: Address
    questions: TreeMap[str, Question]
    evidence_bundles: TreeMap[str, EvidenceBundle]
    resolutions: TreeMap[str, Resolution]
    challenges: TreeMap[str, Challenge]
    question_order: DynArray[str]
    evidence_order: DynArray[str]
    resolution_order: DynArray[str]
    challenge_order: DynArray[str]
    counters: TreeMap[str, u256]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.counters["questions"] = u256(0)
        self.counters["evidence"] = u256(0)
        self.counters["resolutions"] = u256(0)
        self.counters["challenges"] = u256(0)

    @gl.public.write
    def create_question(self, title: str, claim: str, source_policy_json: str, resolution_rules_json: str, deadline_iso: str) -> str:
        if len(title.strip()) < 4:
            raise gl.UserError(f"{ERROR_EXPECTED} title too short")
        if len(claim.strip()) < 16:
            raise gl.UserError(f"{ERROR_EXPECTED} claim too short")
        source_policy = self._parse_json_array(source_policy_json, "source_policy_json")
        resolution_rules = self._parse_json_array(resolution_rules_json, "resolution_rules_json")
        if len(source_policy) == 0:
            raise gl.UserError(f"{ERROR_EXPECTED} source policy required")
        if len(resolution_rules) == 0:
            raise gl.UserError(f"{ERROR_EXPECTED} resolution rules required")

        question_id = self._next_id("question", "questions")
        self.questions[question_id] = Question(
            creator=gl.message.sender_address,
            title=title.strip(),
            claim=claim.strip(),
            source_policy_json=self._canonical_json(source_policy),
            resolution_rules_json=self._canonical_json(resolution_rules),
            deadline_iso=deadline_iso.strip(),
            status="open",
            evidence_count=u256(0),
            created_at=self._now_iso(),
            resolution_id="",
        )
        self.question_order.append(question_id)
        return question_id

    @gl.public.write
    def submit_evidence(self, question_id: str, position: str, evidence_json: str, notes: str) -> str:
        question = self._require_question(question_id)
        if question.status != "open":
            raise gl.UserError(f"{ERROR_EXPECTED} question is not open")
        if position not in (ANSWER_TRUE, ANSWER_FALSE, ANSWER_PARTLY, ANSWER_INSUFFICIENT):
            raise gl.UserError(f"{ERROR_EXPECTED} invalid position")
        evidence = self._parse_json_array(evidence_json, "evidence_json")
        if len(evidence) == 0:
            raise gl.UserError(f"{ERROR_EXPECTED} at least one evidence item required")
        if len(notes.strip()) < 12:
            raise gl.UserError(f"{ERROR_EXPECTED} notes too short")

        evidence_id = self._next_id("evidence", "evidence")
        self.evidence_bundles[evidence_id] = EvidenceBundle(
            question_id=question_id,
            submitter=gl.message.sender_address,
            position=position,
            evidence_json=self._canonical_json(evidence),
            notes=notes.strip(),
            created_at=self._now_iso(),
        )
        question.evidence_count = u256(int(question.evidence_count) + 1)
        self.questions[question_id] = question
        self.evidence_order.append(evidence_id)
        return evidence_id

    @gl.public.write
    def resolve_question(self, question_id: str) -> str:
        question = self._require_question(question_id)
        if question.status not in ("open", "challenged"):
            raise gl.UserError(f"{ERROR_EXPECTED} question cannot be resolved")
        if int(question.evidence_count) == 0:
            raise gl.UserError(f"{ERROR_EXPECTED} evidence required before resolution")

        evidence_json = self._evidence_for_question(question_id)

        def leader_fn():
            return self._derive_resolution(question, evidence_json)

        def validator_fn(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            validator_resolution = leader_fn()
            return self._compare_resolutions(leaders_res.calldata, validator_resolution)

        resolution_data = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        resolution_id = self._store_resolution(question_id, resolution_data)
        question.status = "resolved"
        question.resolution_id = resolution_id
        self.questions[question_id] = question
        return resolution_id

    @gl.public.write
    def challenge_resolution(self, question_id: str, reason: str, counter_evidence_json: str) -> str:
        question = self._require_question(question_id)
        if question.status != "resolved":
            raise gl.UserError(f"{ERROR_EXPECTED} only resolved questions can be challenged")
        if len(reason.strip()) < 20:
            raise gl.UserError(f"{ERROR_EXPECTED} challenge reason too short")
        counter_evidence = self._parse_json_array(counter_evidence_json, "counter_evidence_json")
        if len(counter_evidence) == 0:
            raise gl.UserError(f"{ERROR_EXPECTED} counter evidence required")

        challenge_id = self._next_id("challenge", "challenges")
        self.challenges[challenge_id] = Challenge(
            question_id=question_id,
            challenger=gl.message.sender_address,
            reason=reason.strip(),
            counter_evidence_json=self._canonical_json(counter_evidence),
            status="open",
            created_at=self._now_iso(),
        )
        question.status = "challenged"
        self.questions[question_id] = question
        self.challenge_order.append(challenge_id)
        return challenge_id

    @gl.public.view
    def get_question(self, question_id: str) -> dict:
        question = self._require_question(question_id)
        return {
            "creator": str(question.creator),
            "title": question.title,
            "claim": question.claim,
            "source_policy": json.loads(question.source_policy_json),
            "resolution_rules": json.loads(question.resolution_rules_json),
            "deadline_iso": question.deadline_iso,
            "status": question.status,
            "evidence_count": int(question.evidence_count),
            "created_at": question.created_at,
            "resolution_id": question.resolution_id,
        }

    @gl.public.view
    def get_evidence(self, evidence_id: str) -> dict:
        bundle = self.evidence_bundles[evidence_id]
        if bundle.question_id == "":
            raise gl.UserError(f"{ERROR_EXPECTED} evidence not found")
        return {
            "question_id": bundle.question_id,
            "submitter": str(bundle.submitter),
            "position": bundle.position,
            "evidence": json.loads(bundle.evidence_json),
            "notes": bundle.notes,
            "created_at": bundle.created_at,
        }

    @gl.public.view
    def get_resolution(self, resolution_id: str) -> dict:
        resolution = self.resolutions[resolution_id]
        if resolution.question_id == "":
            raise gl.UserError(f"{ERROR_EXPECTED} resolution not found")
        return {
            "question_id": resolution.question_id,
            "answer": resolution.answer,
            "confidence_band": resolution.confidence_band,
            "source_tiers": json.loads(resolution.source_tiers_json),
            "cited_sources": json.loads(resolution.cited_sources_json),
            "cited_domains": json.loads(resolution.cited_domains_json),
            "key_findings": json.loads(resolution.key_findings_json),
            "contradictions": json.loads(resolution.contradictions_json),
            "stale_sources": json.loads(resolution.stale_sources_json),
            "rationale": resolution.rationale,
            "resolved_at": resolution.resolved_at,
        }

    def _derive_resolution(self, question: Question, evidence_json: str) -> dict:
        prompt = f"""
You are a GenLayer validator for SourceTrail, a reusable evidence-trail oracle.

TASK:
Resolve the claim using the source policy, resolution rules, and submitted evidence.
Do not merely validate JSON shape. Independently inspect the evidence trail,
identify source quality, cite sources/domains, and flag contradictions or stale data.

TITLE: {question.title}
CLAIM: {question.claim}
SOURCE POLICY JSON: {question.source_policy_json}
RESOLUTION RULES JSON: {question.resolution_rules_json}
SUBMITTED EVIDENCE JSON: {evidence_json}

Return JSON exactly with:
{{
  "answer": "true|false|partly_true|insufficient_evidence|stale",
  "confidence": 0-100,
  "source_tiers": ["official|primary|secondary|community|unknown"],
  "cited_sources": ["url or evidence reference"],
  "key_findings": ["short finding"],
  "contradictions": ["short contradiction"],
  "stale_sources": ["url or evidence reference"],
  "rationale": "short evidence-backed explanation"
}}
"""
        raw = gl.nondet.exec_prompt(prompt, response_format="json")
        return self._normalize_resolution(raw)

    def _compare_resolutions(self, leader: dict, validator: dict) -> bool:
        if not isinstance(leader, dict) or not isinstance(validator, dict):
            return False
        if leader.get("answer") != validator.get("answer"):
            return False
        if leader.get("confidence_band") != validator.get("confidence_band"):
            return False

        leader_domains = self._string_set(leader.get("cited_domains", []))
        validator_domains = self._string_set(validator.get("cited_domains", []))
        if not self._sets_overlap_enough(leader_domains, validator_domains, 50):
            return False

        leader_tiers = self._string_set(leader.get("source_tiers", []))
        validator_tiers = self._string_set(validator.get("source_tiers", []))
        if not self._sets_overlap_enough(leader_tiers, validator_tiers, 50):
            return False

        leader_contradictions = self._string_set(leader.get("contradictions", []))
        validator_contradictions = self._string_set(validator.get("contradictions", []))
        if len(leader_contradictions) == 0 and len(validator_contradictions) > 0:
            return False
        if len(leader_contradictions) > 0 and len(validator_contradictions) == 0:
            return False

        return True

    def _normalize_resolution(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            raise gl.UserError(f"{ERROR_LLM} resolution must be an object")
        answer = str(raw.get("answer", "")).strip().lower()
        if answer not in (ANSWER_TRUE, ANSWER_FALSE, ANSWER_PARTLY, ANSWER_INSUFFICIENT, ANSWER_STALE):
            raise gl.UserError(f"{ERROR_LLM} invalid answer")
        confidence = self._coerce_int(raw.get("confidence", 0))
        source_tiers = self._normalize_allowed_tiers(raw.get("source_tiers", []))
        cited_sources = self._normalize_string_array(raw.get("cited_sources", []))
        key_findings = self._normalize_string_array(raw.get("key_findings", []))
        contradictions = self._normalize_string_array(raw.get("contradictions", []))
        stale_sources = self._normalize_string_array(raw.get("stale_sources", []))
        rationale = str(raw.get("rationale", "")).strip()
        if len(rationale) < 12:
            raise gl.UserError(f"{ERROR_LLM} rationale too short")
        if len(cited_sources) == 0 and answer not in (ANSWER_INSUFFICIENT,):
            raise gl.UserError(f"{ERROR_LLM} cited sources required")
        return {
            "answer": answer,
            "confidence": confidence,
            "confidence_band": self._confidence_band(confidence),
            "source_tiers": source_tiers,
            "cited_sources": cited_sources,
            "cited_domains": self._domains_from_sources(cited_sources),
            "key_findings": key_findings,
            "contradictions": contradictions,
            "stale_sources": stale_sources,
            "rationale": rationale,
        }

    def _store_resolution(self, question_id: str, resolution_data: dict) -> str:
        resolution_id = self._next_id("resolution", "resolutions")
        self.resolutions[resolution_id] = Resolution(
            question_id=question_id,
            answer=resolution_data["answer"],
            confidence_band=resolution_data["confidence_band"],
            source_tiers_json=self._canonical_json(resolution_data["source_tiers"]),
            cited_sources_json=self._canonical_json(resolution_data["cited_sources"]),
            cited_domains_json=self._canonical_json(resolution_data["cited_domains"]),
            key_findings_json=self._canonical_json(resolution_data["key_findings"]),
            contradictions_json=self._canonical_json(resolution_data["contradictions"]),
            stale_sources_json=self._canonical_json(resolution_data["stale_sources"]),
            rationale=resolution_data["rationale"],
            resolved_at=self._now_iso(),
        )
        self.resolution_order.append(resolution_id)
        return resolution_id

    def _evidence_for_question(self, question_id: str) -> str:
        bundles = []
        for evidence_id in self.evidence_order:
            bundle = self.evidence_bundles[evidence_id]
            if bundle.question_id == question_id:
                bundles.append({
                    "position": bundle.position,
                    "evidence": json.loads(bundle.evidence_json),
                    "notes": bundle.notes,
                    "submitter": str(bundle.submitter),
                })
        return self._canonical_json(bundles)

    def _next_id(self, prefix: str, counter_key: str) -> str:
        current = int(self.counters[counter_key]) + 1
        self.counters[counter_key] = u256(current)
        return prefix + "-" + str(current)

    def _require_question(self, question_id: str) -> Question:
        question = self.questions[question_id]
        if question.status == "":
            raise gl.UserError(f"{ERROR_EXPECTED} question not found")
        return question

    def _parse_json_array(self, text: str, field_name: str) -> list:
        try:
            value = json.loads(text)
        except Exception:
            raise gl.UserError(f"{ERROR_EXPECTED} invalid {field_name}")
        if not isinstance(value, list):
            raise gl.UserError(f"{ERROR_EXPECTED} {field_name} must be an array")
        return value

    def _canonical_json(self, value) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _normalize_string_array(self, value) -> list:
        if not isinstance(value, list):
            return []
        out = []
        for item in value:
            text = str(item).strip().lower()
            if text != "":
                out.append(text)
        return out

    def _normalize_allowed_tiers(self, value) -> list:
        allowed = ["official", "primary", "secondary", "community", "unknown"]
        tiers = []
        for item in self._normalize_string_array(value):
            if item in allowed and item not in tiers:
                tiers.append(item)
        if len(tiers) == 0:
            tiers.append("unknown")
        return tiers

    def _domains_from_sources(self, sources: list) -> list:
        domains = []
        for source in sources:
            text = str(source).strip().lower()
            if "://" in text:
                text = text.split("://", 1)[1]
            domain = text.split("/", 1)[0].split("?", 1)[0]
            if domain != "" and domain not in domains:
                domains.append(domain)
        return domains

    def _string_set(self, items) -> list:
        normalized = self._normalize_string_array(items)
        unique = []
        for item in normalized:
            if item not in unique:
                unique.append(item)
        return unique

    def _sets_overlap_enough(self, left: list, right: list, threshold_percent: int) -> bool:
        if len(left) == 0 and len(right) == 0:
            return True
        if len(left) == 0 or len(right) == 0:
            return False
        overlap = 0
        for item in left:
            if item in right:
                overlap += 1
        smaller = len(left)
        if len(right) < smaller:
            smaller = len(right)
        return overlap * 100 >= smaller * threshold_percent

    def _coerce_int(self, value) -> int:
        try:
            parsed = int(value)
        except Exception:
            return 0
        if parsed < 0:
            return 0
        if parsed > 100:
            return 100
        return parsed

    def _confidence_band(self, confidence: int) -> str:
        if confidence >= 80:
            return "high"
        if confidence >= 55:
            return "medium"
        return "low"

    def _now_iso(self) -> str:
        return str(gl.block.timestamp)
