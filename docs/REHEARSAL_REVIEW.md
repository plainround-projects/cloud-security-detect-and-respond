# Incident review: drill

Blameless wording: the role allowed the calls below. Every claim cites an event id from the central archive.

## Timeline, from the logs only

| Time (UTC) | Actor | Call | Target | Result | Event id | Detection |
| --- | --- | --- | --- | --- | --- | --- |
| 11:03:10 | attacker | AssumeRole | drill-broad-role session "intruder" | ok | 00000000-0000-4000-8000-000000000003 | - |
| 11:03:21 | attacker | ListBuckets | - | ok | 00000000-0000-4000-8000-000000000004 | - |
| 11:03:42 | attacker | CreateAccessKey | drill-user | ok | 00000000-0000-4000-8000-000000000005 | D1 |
| 11:04:05 | attacker | PutBucketAcl | drill-data-000000000000 (public-read) | ok | 00000000-0000-4000-8000-000000000006 | D2 |
| 11:04:31 | attacker | DescribeInstances | ap-southeast-2 | ok | 00000000-0000-4000-8000-000000000007 | D4 |
| 11:09:48 | responder | PutRolePolicy | drill-broad-role | ok | 00000000-0000-4000-8000-000000000008 | - |
| 11:09:57 | responder | UpdateAccessKey | drill-user | ok | 00000000-0000-4000-8000-000000000009 | - |
| 11:10:02 | attacker | CreateAccessKey | drill-user | denied | 00000000-0000-4000-8000-000000000010 | D1 |

## Times

- time to detect:  32 s  (first action 11:03:10, first alert 11:03:42)
- time to contain: 6 min 52 s  (first action 11:03:10, next call refused 11:10:02)

## Prevented and only recorded

| Detection | Raised by (event id) | Prevented? | What prevention would look like |
| --- | --- | --- | --- |
| D1 new long-lived credential | 00000000-0000-4000-8000-000000000005, 00000000-0000-4000-8000-000000000010 | no, recorded and alerted only | Deny iam:CreateAccessKey and iam:CreateLoginProfile to everything except the identity team's role, with a service control policy. |
| D2 storage made public | 00000000-0000-4000-8000-000000000006 | no, recorded and alerted only | Turn on Block Public Access for the whole account, so a public policy or ACL cannot succeed in the first place. |
| D4 unexpected Region | 00000000-0000-4000-8000-000000000007 | no, recorded and alerted only | Deny every action outside the allowed Regions with a service control policy on aws:RequestedRegion. |

## Changes that would stop the weakness recurring

- Deny iam:CreateAccessKey and iam:CreateLoginProfile to everything except the identity team's role, with a service control policy.
- Turn on Block Public Access for the whole account, so a public policy or ACL cannot succeed in the first place.
- Deny every action outside the allowed Regions with a service control policy on aws:RequestedRegion.
- Remove the temporary exception (the drill user, the broad role and the drill bucket) and write down the time: `make down`.
