# SourceTrail consensus design

## Goal

SourceTrail is an evidence-trail oracle for claims that are too subjective or source-dependent for deterministic feeds.

The contract is intentionally reusable: apps can define their own source policy and resolution rules while reusing the same question → evidence → resolution → challenge state machine.

## Leader work

The leader receives:

- claim/title
- source policy JSON
- resolution rules JSON
- submitted evidence bundles

The leader must derive:

- answer bucket
- confidence score/band
- source-quality tiers used
- cited sources
- cited domains
- key findings
- contradictions
- stale sources
- concise rationale

## Validator work

Validators do not merely check that the leader returned JSON. They independently re-run the evidence review and compare stable fields.

The validator accepts only when:

1. The answer bucket matches.
2. The confidence band matches.
3. Cited domains overlap enough to show the same evidence trail.
4. Source-quality tiers overlap enough to show equivalent source policy reasoning.
5. Contradiction presence/absence matches.

## Why not strict equality?

Natural-language source review can produce equivalent but not byte-identical rationale. One validator may cite `docs.example.com/changelog` while another cites `example.com/blog/changelog` from the same official source family. SourceTrail compares stable buckets and domain/tier overlap instead of requiring exact prose equality.

## Why not format-only validation?

A format-only validator would accept any JSON with the right fields. SourceTrail makes validators independently inspect the claim and evidence trail, then compare the actual resolution semantics.

## Failure modes handled

- contradictory sources → `contradictions` populated, often `partly_true` or `insufficient_evidence`
- stale sources → `stale_sources` populated and answer may be `stale`
- weak evidence → `insufficient_evidence`
- mixed official/secondary trail → source tiers are stored for downstream consumers
