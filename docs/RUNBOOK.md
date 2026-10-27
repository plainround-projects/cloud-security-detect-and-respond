# Runbook: the commands to run once the sandbox accounts exist

Nothing here has been run against a real account; the offline pipeline (`make validate`) and the rehearsal replay (`make demo-drill`) are what was verified. Run these in sandbox accounts you created for this exercise, with a budget alert, and remove the temporary exception the same day.

## Before you start

Two accounts take part: a **security account** (owns the archive) and a **workload account** (the sandbox being watched). If you only have one account, the archive is no longer outside an administrator's reach, and step 1's "Done when" cannot be shown; create a second account in your organization.

```bash
make install                                    # the Python tooling in .venv
cp .env.example .env                            # fill in the profiles, the two account ids and your address
set -a; source .env; set +a
aws sts get-caller-identity --profile "$SECURITY_PROFILE"
aws sts get-caller-identity --profile "$WORKLOAD_PROFILE"
```

The scripts refuse to run when a profile belongs to a different account than the one you named, and when the caller is the account root user. Use an administrator role or user in each account, never the root user.

## Cost

Approximate list prices, to check on the provider's pricing pages. For a day of work the total is expected to stay under three US dollars; the posture services are the part to watch if you leave them on.

| Item | Price | In one day |
| --- | --- | --- |
| Audit trail, management events | the first copy is free | 0 |
| Archive storage and requests | pay per use | under a cent |
| Keys (archive key and one per alert Region) | about 1 US dollar per key per month, prorated | a few cents |
| Alert topics, email delivery, rules | first million events free, then per event | 0 at this volume |
| AWS Config recording | about 0.003 US dollars per configuration item | a few cents to a dollar, depending on the account |
| Security Hub checks | a per-check price after a free trial | a few cents to a dollar |
| Budget | the first two are free | 0 |

The Terraform creates a budget that alerts at 80 percent of 20 US dollars actual and 100 percent forecast.

## The order, and what each step proves

```bash
make up           # 01-deploy-security.sh, then 02-deploy-workload.sh
make run          # 03-verify-archive.sh, 04-drill-setup.sh, 05-posture-baseline.sh before
make attack       # 07-drill-attack.sh   (note the clock time it prints)
make respond      # 08-contain.sh        (a dry run; make respond APPLY=--apply to do it)
make measure      # 09-collect-and-measure.sh
make down         # 10-teardown.sh, then later: scripts/10-teardown.sh archive
```

| Script | Lesson step | What it does |
| --- | --- | --- |
| `01-deploy-security.sh` | 1 | applies the `security` environment: the archive key, and the bucket with Object Lock (compliance, one day), versioning, deletes denied |
| `02-deploy-workload.sh` | 1 to 3 | applies the `workload` environment: the trail into the archive, detections D1 to D4 in us-east-1, the home Region and ap-southeast-2, posture management, a budget. **Confirm the three email subscriptions**, or no alert reaches you |
| `03-verify-archive.sh` | 1 | performs an action, waits for the log file to appear in the archive, tries to delete it as an administrator of each account (both must be refused), and runs the provider's `validate-logs` |
| `04-drill-setup.sh` | 4 | creates the drill user, the over-privileged role and the drill bucket (the temporary exception), creates the user's key into the CLI profile `drill` without printing it, and writes down what the role can do |
| `05-posture-baseline.sh before` / `after` | 3 | reads the open findings into `evidence/posture/`; after fixing, prints the baseline table and fails on an unfixed critical finding or an acceptance without a reason |
| `06-honeytoken.sh` | stretch | creates the honeytoken user's key, deploys detection D5 for it |
| `07-drill-attack.sh` | 5 | the attacker's half, against the drill resources only: assume the role, look around, create a key, make the drill bucket public, call another Region |
| `08-contain.sh` | 5 | the responder's half: deny the role's older sessions and deactivate the key |
| `09-collect-and-measure.sh` | 5, 6 | copies the archive out, verifies it against its digests, replays the detections, rebuilds the timeline from the logs only, measures both times, writes `evidence/REVIEW.md` |
| `10-teardown.sh` | 6 | deletes the keys and the profile, destroys the workload environment, writes the time the exception was removed |

## The exception, and the order of teardown

The drill creates a user with a key, a role with `PowerUserAccess` and a bucket with Block Public Access off. They exist only while `enable_drill` is true; the OPA rules allow those three things only inside the `drill` module. `make down` removes them and prints the time.

The archive cannot be deleted at once: compliance-mode retention (one day) cannot be shortened by anyone, and the lifecycle expires the files after two days. Run `scripts/10-teardown.sh archive` after that. Until then the bucket and its key keep costing a few cents.

## What you should see

The same shapes the rehearsal prints (`make demo-drill`), with your own times:

```text
11:03:10  AssumeRole         drill-broad-role session "intruder"      OK
11:03:21  ListBuckets        -                                        OK
11:03:42  CreateAccessKey    drill-user                               OK       <- D1 fires
11:04:05  PutBucketAcl       drill-data-<account> (public-read)       OK       <- D2 fires
11:04:31  DescribeInstances  ap-southeast-2                           OK       <- D4 fires
11:09:48  (responder) PutRolePolicy      drill-broad-role                         OK
11:10:02  CreateAccessKey    drill-user                               DENIED   <- D1 fires

time to detect:  32 s  (first action 11:03:10, first alert 11:03:42)
time to contain: 6 min 52 s  (first action 11:03:10, next call refused 11:10:02)
```

Time to detect uses the event time of the first detected call unless you give the times your alerts reached you in `evidence/alerts.json`; with real email delivery it will be longer than the event time. Time to contain needs the attacker to try one more call after the revocation, as the lesson's script does; otherwise the tool says containment was not confirmed.

## Known gaps to confirm with a real account

- **The alert text.** The rule's input transformer inserts `requestParameters` (an object) into the message as JSON text. The format was not confirmed; if the first real email shows the fields badly, change the template in `detections/alert-template.txt`.
- **Event-pattern corners.** The replay implements the pattern language the detections use. The first real alert for each of D1, D2 and D4 is the check that the provider's matcher agrees, especially the nested `$or` of D2 and the read-only rule state of D4.
- **Cross-account encryption.** The archive key policy admits the trail by service principal pinned to the trail's ARN. Whether the trail's first delivery succeeds with that pin alone was not confirmed; `03-verify-archive.sh` fails loudly if no file arrives.
- **`validate-logs` across accounts.** It needs read access to the archive from the credentials you use; if it reports nothing to validate, run it with the security account's profile against the trail's ARN.
- **Posture services.** Security Hub needs a first full scan (minutes to hours) before `05-posture-baseline.sh` shows a complete picture.
