# SourceTrail examples

## 1. Protocol announcement oracle

Claim: "Protocol X announced support for Arc Testnet before July 1, 2026."

Source policy:

- prefer official blog/docs/GitHub release
- secondary news is allowed only as supporting evidence
- social screenshots alone are insufficient

Resolution packet stores official cited domains and whether the announcement actually happened before the cutoff.

## 2. GitHub issue fix oracle

Claim: "Issue #42 was materially fixed in release v1.4.0."

Source policy:

- GitHub issue, merged PR, release notes, and commit diff are primary sources
- external blog posts are secondary only

Resolution can be `true`, `partly_true`, or `false` depending on whether the issue was closed, the PR addressed the reported behavior, and release notes included the change.

## 3. Documentation-change oracle

Claim: "The API docs now include the `/agents/register-with-wallet` endpoint."

Source policy:

- official documentation or repository docs are required
- cached mirrors are stale unless timestamped

Useful for agent marketplaces and integration registries that need source-backed state.

## 4. Event/outage oracle

Claim: "Service Y had a public outage on a given day."

Source policy:

- official status page and incident report are primary
- user posts can indicate symptoms but not settle the claim alone

The durable packet records contradictions and stale sources so consumers know why a claim was not cleanly true/false.
