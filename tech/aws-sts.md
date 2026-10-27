# AWS STS (Security Token Service)

## What it is

STS is the AWS service that hands out **temporary credentials** and tells you **who you are**. Two of its calls matter here. `AssumeRole` exchanges your identity for the credentials of a role, valid for a limited time (an access key id, a secret key and a **session token**), under a **session name** that you choose. `GetCallerIdentity` returns the account, user id and ARN of whatever credentials you present.

## Why this repository uses it

The drill's attacker works through STS: the stolen user key is used to assume the broad role under the session name `intruder`, and every call after that is made with temporary credentials. That choice shapes the whole response. The audit log names the caller as `.../assumed-role/drill-broad-role/intruder`, so the timeline can be rebuilt from the session name alone, and containment must stop the *session*, not only the user's key. The scripts also use STS to prove which of the two accounts they are talking to.

## Where it appears

| Path | What it does with STS |
| --- | --- |
| `scripts/lib.sh` | `sts get-caller-identity` in `use_account`, to refuse the wrong account or the root user |
| `scripts/07-drill-attack.sh` | `sts assume-role` with the session name `intruder` |
| `infra/modules/drill/main.tf` | the role's trust policy and the user's permission to assume it |
| `src/detect_respond/domain/events.py` | `session_of(role_name)` reads the session name from the caller ARN |
| `src/detect_respond/domain/timeline.py` | recognizes the attacker's session and the `AssumeRole` call that started it |
| `src/detect_respond/domain/containment.py` | the deny policy keys on when the credentials were issued |

## How it works underneath

When a role is assumed, STS creates a **session**. The caller's ARN then looks like `arn:aws:sts::<account>:assumed-role/<role>/<session-name>`. The session name appears in every audit-log entry the session causes. The credentials expire (up to the role's maximum, one hour by default) and cannot be recalled; the only way to stop a session early is to deny it with a policy, which is what containment does. Each credential set records when it was issued (`aws:TokenIssueTime`), and a policy can test that. A **trust policy** on the role decides who may call `AssumeRole`.

## Walkthrough of this repository's use

From `scripts/lib.sh`:

```bash
  identity="$(aws sts get-caller-identity --query '[Account,Arn]' --output text)"
```

`GetCallerIdentity` needs no permission, so it works for any valid credentials. The script compares the account id with the expected one and refuses to run as the account's root user (an ARN ending `:root`). See [bash.md](bash.md).

From `scripts/07-drill-attack.sh`:

```bash
read -r ak sk st < <(aws sts assume-role --role-arn "arn:aws:iam::${ACCOUNT}:role/${DRILL_ROLE}" --role-session-name "$SESSION_NAME" \
  --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)
```

The attacker's first step. The three values are the temporary access key id, secret and session token. They are placed in the environment of one command at a time (`as_role`) and never printed. The session name is `intruder`, set once in `lib.sh` as `SESSION_NAME`.

From `src/detect_respond/domain/events.py`:

```python
        marker = f":assumed-role/{role_name}/"
        if marker in self.principal_arn:
            return self.principal_arn.split(marker, 1)[1]
        return None
```

`session_of` returns the session name when the event was made by a session of the role, otherwise `None`. `split(marker, 1)[1]` cuts the ARN at the marker (once) and keeps the part after it.

From `src/detect_respond/domain/timeline.py`:

```python
    assumed = event.name == "AssumeRole" and str(event.request.get("roleArn", "")).endswith(f":role/{role_name}")
    return assumed and event.request.get("roleSessionName") == session
```

The very first attacker event, the `AssumeRole` call, is made by the *user*, not yet by the session. The timeline recognizes it by the role it asked for and the session name it requested, so the first action is counted. Time to detect and time to contain are measured from it.

## Try it yourself

```bash
env -u AWS_PROFILE AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true aws sts get-caller-identity
```

With no credentials, expect `Unable to locate credentials` (the exact wording differs between CLI versions). With a real profile, the same call prints your account and ARN.

```bash
.venv/bin/python -c "
from detect_respond.domain.events import AuditEvent
e = AuditEvent.from_record({'eventID': 'e', 'eventTime': '2026-10-22T11:03:42Z', 'eventName': 'ListBuckets', 'eventSource': 's3.amazonaws.com', 'userIdentity': {'arn': 'arn:aws:sts::000000000000:assumed-role/drill-broad-role/intruder'}})
print(e.session_of('drill-broad-role'), e.session_of('other-role'))"
```

Expect `intruder None`: the session name is the last part of the ARN, and a different role gives `None`.

```bash
.venv/bin/python -m detect_respond drill --archive fixtures/drill --alerts fixtures/drill/alerts.json | sed -n 1,3p
```

Expect the start of the rebuilt timeline, whose first row is the attacker's `AssumeRole` call for the session `intruder`.

## Mistakes people make

- Printing temporary credentials into a log or a chat. They are secrets until they expire.
- Forgetting that temporary credentials cannot be recalled. Revoke by denying, as containment does.
- Searching the audit log by the user's name only. After the role is assumed, the caller is the session.
- Assuming the role's credentials last forever: they expire; the next call after expiry fails.

## Check yourself

1. What does `AssumeRole` return? *Temporary credentials: an access key id, a secret key and a session token.*
2. What does the ARN of an assumed role look like? *`arn:aws:sts::<account>:assumed-role/<role>/<session>`.*
3. Why can a session not simply be cancelled? *Temporary credentials cannot be recalled; they are stopped by a policy that denies them.*
4. Why does the timeline recognize the `AssumeRole` call separately? *It is made by the user before the session exists, but it is the attacker's first action.*
5. Who decides who may assume a role? *The role's trust policy.*

## Further reading

- STS API reference: <https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html>
- Temporary credentials: <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html>
