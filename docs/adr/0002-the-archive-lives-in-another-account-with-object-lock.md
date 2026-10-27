# 0002. The log archive lives in another account, under Object Lock in compliance mode

Status: accepted, 2026-10-27.

## Context

An attacker with administrator rights in the compromised account can delete the evidence if it lives there. The lesson asks for a store that an administrator of the first account cannot alter, with integrity protection.

## Decision

Two Terraform environments, one per account. `security` owns the archive: a bucket with Object Lock in compliance mode (one day for the exercise), versioning, a customer-managed key, Block Public Access, and a policy that admits only the workload account's trail (pinned by `aws:SourceArn`) and denies deleting objects and versions to every principal. `workload` owns the trail, with log file validation, delivering to that bucket under that key. The key policy lets the trail encrypt, lets the security account decrypt through the storage service only, and gives the account root no data actions.

## Alternatives

- **A separate bucket in the same account.** An administrator of the account can still delete it.
- **Governance-mode Object Lock.** Anyone with the bypass permission can remove it; the lesson wants the owner unable to.
- **Replication to another account.** A good production addition; it needs the archive to exist first and doubles what the exercise creates.

## Consequences

- Compliance mode cannot be shortened by anyone, so the archive and its bucket stay until the retention and the lifecycle expiry have passed. The runbook says so before the first deploy, and `scripts/10-teardown.sh archive` is a second, later step.
- The deletion deny also blocks Terraform's `force_destroy`; files leave only by lifecycle expiry, a service action the deny does not cover.
- The offline checks (OPA rules on both plans) prove the shape: compliance mode, retention, delete denied to everyone, one pinned writer, a key outside the workload account. That the workload account's administrator really is refused needs two accounts; `scripts/03-verify-archive.sh` does it.
