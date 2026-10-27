# Detections

The detections are data: one JSON file per detection in [detections/](../detections), the single source of truth. Terraform deploys the `pattern` of each file as an EventBridge rule, and the Python tooling replays the same pattern over the archive, so the pattern that is tested is the pattern that runs. `make check` fails if a rule in the plan differs from its file (`detect-respond audit-rules`).

| # | Detection | Event to match | Where it runs | First thing the responder does | What prevention would look like |
| --- | --- | --- | --- | --- | --- |
| D1 | New long-lived credential | `CreateAccessKey`, `CreateLoginProfile` | us-east-1 (where global service events arrive) | Ask who made it; disable it | Deny both calls to everything except the identity team's role |
| D2 | Storage made public | `PutBucketPolicy`, `PutBucketAcl`, `DeletePublicAccessBlock`, and `PutPublicAccessBlock` with any setting switched off | the home Region (where the bucket lives) | Re-block; check what was exposed | Block Public Access for the whole account |
| D3 | Broad privilege grant | `AttachUserPolicy`, `AttachRolePolicy`, `AttachGroupPolicy` with `AdministratorAccess` | us-east-1 | Detach; find the caller | A permissions boundary or service control policy |
| D4 | Unexpected Region | any event whose `awsRegion` is not `eu-west-1` or `us-east-1`, read-only calls included | each watched Region (here ap-southeast-2) | Check what was created; stop it | A service control policy on `aws:RequestedRegion` |
| D5 | Honeytoken used (stretch) | any event made with the honeytoken's access key id | us-east-1, once the key id is set | Treat as a confirmed compromise | Nothing: the user has no permissions |

## Properties worth knowing

- **A failed call matches too.** A denied `CreateAccessKey` is an attempt, and an attempt is as telling as a success, so D1 fires on the attacker's last call in the rehearsal as well.
- **A rule sees one Region.** EventBridge delivers an event to the bus of the Region it happened in. IAM events are delivered in us-east-1, S3 bucket-level events in the bucket's Region. D4 therefore only works in Regions where it is deployed; to cover every Region, the log scanner (`detect-respond scan`) runs the same patterns over the whole archive.
- **Read-only calls need the right rule state.** By default a rule does not match read-only management events (`Describe*`, `List*`, `Get*`). D4 sets the rule state `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`, and the plan audit fails if it does not. The lesson's `describe-instances` drill call is read-only, so without this D4 would never fire.
- **A pattern with a typo never fires and gives no error.** The replay tests assert that each detection fires on its positive events and stays quiet on near misses (`DeleteAccessKey`, `PowerUserAccess`, a call in an allowed Region), and the matcher refuses an operator it does not implement.
- **The alert text carries the user, the source address and the request.** Template: [detections/alert-template.txt](../detections/alert-template.txt). The fields written `{name}` are filled when the rule is deployed; the fields written `<name>` are filled by the rule's input transformer when it fires, and by the replay in tests.

## Add a detection

1. Write `detections/d6-<slug>.json` with `id`, `title`, `severity`, `description`, `firstStep`, `prevention`, `deployTo` (`global`, `home` or `watch`) and `pattern`.
2. Add positive and near-miss events to `tests/unit/detect_respond/test_pattern_and_detections.py`.
3. `make validate`: the plan deploys it to the Regions it names, and `audit-rules` proves the deployed pattern is the file.
