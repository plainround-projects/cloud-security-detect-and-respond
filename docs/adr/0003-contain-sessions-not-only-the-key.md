# 0003. Containment denies the role's older sessions as well as deactivating the key

Status: accepted, 2026-10-27.

## Context

Deactivating the leaked user key stops new `AssumeRole` calls with it, but the attacker already holds temporary credentials for the role, and those stay valid until they expire. The lesson's common mistake is revoking only the key.

## Decision

`detect-respond contain` does two things together: it attaches an inline policy to the role that denies every call made with credentials issued before now (`aws:TokenIssueTime` earlier than the moment of containment), and it deactivates the user's access keys (inactive, not deleted, so the evidence stays). It is a dry run unless `--apply` is given, prints the same actions as CLI commands, and takes its clock and its IAM client through ports so it is tested with fakes and with the SDK's stubber.

## Alternatives

- **Delete the role.** Stops everything, but destroys the evidence and the means to reuse the role afterward.
- **Detach the role's policies.** Works, but an in-flight session may still hold a cached decision for a short time; the explicit deny is immediate.

## Consequences

- New sessions, issued after the moment, are not affected, so the role works again once the cause is fixed; the deny can be removed or left.
- The containment time is measured from the log: the first call the revocation refuses. If the attacker never retries, the measure says it could not confirm containment instead of inventing a number.
- An automated response that runs this on a high-severity alert is the lesson's first stretch goal. It is not built: automated containment of a role needs its own guardrails (allow lists, rate limits, a human override) and its own tests.
