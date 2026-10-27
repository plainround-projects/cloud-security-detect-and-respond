# infra

Terraform for the detection and response layer, in two environments because two accounts take part.

| Folder | What lives there |
| --- | --- |
| `modules/` | one reusable piece each: `kms-key`, `log-archive`, `central-trail`, `alerting`, `drill`, `posture`, `budget` (each with its own README) |
| `environments/security/` | the security account: the archive key and bucket. Apply this first. |
| `environments/workload/` | the sandbox account: the trail, the detections in three Regions, posture management, the drill, the budget |

Each environment has `plan-only.tfvars` (placeholders, no credentials) and `sandbox.tfvars.example`. State is local because the sandbox is deleted the same day; use a remote backend with locking in any shared environment.

The workload environment reads `detections/` (the single source of truth for the rules) and uses three provider configurations: the home Region, us-east-1 for global service events and a watched Region. To watch another Region, add a provider and an `alerting` module like the last one.

Offline: `make plan` (from the repository root) initializes each environment without a backend, plans with `plan_only = true` and placeholder credentials, and writes `build/security.json` and `build/workload.json`.
