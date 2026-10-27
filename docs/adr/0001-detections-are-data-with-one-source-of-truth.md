# 0001. Detections are data, deployed and replayed from the same file

Status: accepted, 2026-10-27.

## Context

The lesson's stretch asks to "export one detection as code so it is version-controlled and tested". The main risk with a rule is that it silently never fires: a typo in an event name gives no error. A rule that is tested in one place and deployed from another can drift apart.

## Decision

Each detection is a JSON file in `detections/` (id, severity, first step, prevention, where it runs, the EventBridge pattern). Terraform reads the files and deploys each `pattern` unchanged as a rule. The Python tooling reads the same files and replays the pattern over archived events with a small implementation of the event-pattern language. `detect-respond audit-rules` reads the Terraform plan and fails if a deployed rule's pattern differs from its file, if a detection is missing where it should run, or if a rule that must see read-only calls has the wrong state.

## Alternatives

- **Rules written only in Terraform.** Nothing to replay; the only test is to perform the action in an account.
- **Detections written in a general-purpose language (for example a Sigma-style rule engine).** More expressive, but the real-time path in this account is EventBridge, so the rule that runs would not be the rule that was tested.

## Consequences

- Every detection has positive and near-miss tests that run in milliseconds with no account.
- The matcher implements the operators the detections use (exact values, `anything-but`, `prefix`, `suffix`, `exists`, nested objects, `$or`) and raises on anything else. A new operator is a code change with a test, which is the point.
- The matcher is an implementation of the provider's language, so it can differ from it in a corner. The first real alert in an account (`docs/RUNBOOK.md`) is the check that matters.
