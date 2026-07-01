# SourceTrail

SourceTrail is a standalone GenLayer Intelligent Contract primitive for evidence-backed claim resolution.

It is the next, more oracle-heavy contract after ProofJudge: instead of judging whether a submitted deliverable satisfies criteria, SourceTrail resolves claims that need source inspection, source-quality policy, contradiction handling, stale-source detection, and durable citation trails.

## Submission summary

SourceTrail is a reusable subjective-oracle primitive for builders who need more than a deterministic feed but less than a full custom adjudication app. A caller opens a question with a natural-language claim, allowed source policy, and resolution rules. Participants submit evidence bundles. GenLayer validators independently inspect the source trail and only accept a resolution when their answer bucket, confidence band, cited domains, source-quality tiers, and contradiction flags are equivalent enough.

This makes the contract useful for protocol announcements, GitHub issue/release verification, documentation-change claims, incident/outage checks, integration registries, and agent marketplaces that need source-backed answers.

## Why this is not a thin LLM wrapper

SourceTrail does not ask one model for prose and store it. The consensus boundary is the source-trail equivalence check:

- leader derives a full resolution packet from the claim, source policy, rules, and evidence
- validators independently derive their own resolution packet
- contract compares stable semantic fields, not raw text equality
- disagreement on answer bucket, confidence band, cited domains, source tiers, or contradiction presence rejects the leader result

## Use cases

- Did a protocol/team publish an official announcement before a deadline?
- Did a GitHub issue, pull request, or security advisory materially support a claim?
- Did an API/documentation change actually happen?
- Did a public event or outage occur according to primary/official sources?
- Is a source trail stale, contradictory, or insufficient?

## Contract flow

1. `create_question(...)`
   - stores claim, source policy, resolution rules, deadline, and creator
2. `submit_evidence(...)`
   - stores evidence bundles with the submitter's answer position and notes
3. `resolve_question(...)`
   - runs GenLayer nondeterministic consensus over the full evidence trail
   - stores the durable resolution packet
4. `challenge_resolution(...)`
   - lets a caller attach counter-evidence and move the question back into a challenged state
5. View methods expose question, evidence, and resolution state for downstream apps.

## Stored resolution packet

Each resolution stores:

- `answer`: `true`, `false`, `partly_true`, `insufficient_evidence`, or `stale`
- `confidence_band`: `high`, `medium`, or `low`
- `source_tiers`: official/primary/secondary/community/unknown source quality labels
- `cited_sources`: evidence references used by the resolution
- `cited_domains`: normalized domains used for equivalence checks
- `key_findings`: short findings supporting the answer
- `contradictions`: conflicting claims/sources that materially affect resolution
- `stale_sources`: sources that are outdated or no longer support the claim
- `rationale`: short evidence-backed explanation

## Consensus boundary

- Frontend/backend owns: UI, indexing, evidence upload convenience, previews, and off-chain search UX.
- SourceTrail owns: question state, evidence bundles, source policy, resolution rules, challenge state, and the durable resolution packet.
- External sources own: raw evidence. Validators independently inspect the evidence trail before agreeing with a resolution.

## Validator equivalence model

Validators resolve natural-language claims against source policies and compare stable evidence-trail fields:

- same answer bucket
- same confidence band
- sufficient overlap in cited domains
- sufficient overlap in source-quality tiers
- matching contradiction presence/absence

That lets builders consume a compact on-chain resolution packet without pretending every subjective fact can be reduced to one deterministic API call.

## Repository layout

- `contracts/source_trail.py` — standalone GenLayer Intelligent Contract
- `tests/test_contract_static.py` — local static tests for submission-quality invariants
- `tests/test_fixture_resolution.py` — fixture-level tests for resolution normalization/equivalence semantics
- `scripts/check.sh` — local validation runner
- `scripts/deploy.sh` — deployment helper for Studionet/Bradbury
- `docs/consensus-design.md` — validator/equivalence model
- `docs/examples.md` — reusable oracle examples
- `docs/deployment.md` — deployment prep notes

## Local validation

```bash
python3.12 -m venv .venv312
. .venv312/bin/activate
pip install pytest genvm-linter
./scripts/check.sh
```

Expected checks:

- pytest static/fixture tests
- GenVM AST lint
- GenVM SDK validation

## Deployment prep

Deployment requires a configured GenLayer CLI account/network. See `docs/deployment.md`.

Short version:

```bash
genlayer network list
genlayer network set studionet   # or testnet-bradbury if configured
./scripts/deploy.sh studionet
```

Always inspect the deployment transaction receipt/trace. GenLayer transaction accepted/finalized status alone is not enough; verify execution success.
