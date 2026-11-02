# boto3 (and botocore)

## What it is

boto3 is the official Python library for calling AWS. You create a **client** for one service (`boto3.client("iam")`) and call its methods, which match the service's API operations (`list_access_keys`, `put_role_policy`). botocore is the lower layer that does the work: it builds the request, signs it, sends it and reads the answer. This repository pins **boto3 1.43.119** and botocore 1.43.119 in `requirements.lock`; the project allows `boto3>=1.35,<2`.

## Why this repository uses it

Almost everything in this repository works on files (the archive, the plan, the findings) and needs no cloud. Containment is the exception: stopping an intruder means changing the account, by attaching a deny policy to a role and turning a user's keys off. That needs the IAM service, so it needs boto3. It is the repository's only run-time dependency, and the only code that changes an account.

## Where it appears

| Path | What it does with boto3 |
| --- | --- |
| `src/detect_respond/infrastructure/boto_revoker.py` | the one adapter that calls IAM: list keys, attach a policy, deactivate a key |
| `src/detect_respond/application/ports.py` | the `Revoker` port that the adapter implements |
| `tests/unit/detect_respond/test_response.py` | tests the adapter with botocore's `Stubber`, no network |
| `pyproject.toml` | `dependencies = ["boto3>=1.35,<2"]` ([toml.md](toml.md)) |
| `requirements.lock` | the exact versions and hashes of boto3 and what it needs ([pip.md](pip.md)) |

## How it works underneath

A client is an object generated at run time from a **service description** (a big data file inside botocore). When you call `update_access_key`, botocore checks your arguments against the description, finds credentials, **signs** the request (a calculated stamp proving who sent it, using AWS Signature Version 4), sends it over HTTPS and turns the JSON or XML answer into a Python `dict`. If AWS refuses, botocore raises `ClientError` with the error code (`AccessDenied`). **Credentials** are searched in a fixed order: environment variables, shared config files and profiles, then the role of the machine. The scripts choose the account by setting `AWS_PROFILE` ([bash.md](bash.md)), and boto3 follows it.

## Walkthrough of this repository's use

From `src/detect_respond/infrastructure/boto_revoker.py`:

```python
        self._iam = client or boto3.client(
            "iam", config=Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)
        )
```

`client or boto3.client(...)` means: use the client that was passed in (a test passes a stubbed one), otherwise build a real one. `Config` is botocore's tuning object. `retries` with mode `standard` retries a failed call up to 5 times with growing waits; `connect_timeout` and `read_timeout` (seconds) stop a call from hanging forever. The project rule is "a timeout and retries on every network call".

From `src/detect_respond/infrastructure/boto_revoker.py`:

```python
        response = self._iam.list_access_keys(UserName=user_name)
        return tuple(item["AccessKeyId"] for item in response["AccessKeyMetadata"])
```

The answer is a dictionary; `AccessKeyMetadata` is a list with one entry per key (active or not). The adapter returns only the ids, as a tuple, so the rest of the program never sees a boto3 type.

From `src/detect_respond/infrastructure/boto_revoker.py`:

```python
        self._iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))
```

Attaches an **inline policy** to a role. The API wants the policy as JSON *text* ([json.md](json.md)), so the dictionary is converted with `json.dumps`. The call is idempotent: a second call with the same name replaces the policy, so containment can be run twice safely. What the policy says is in [aws-iam.md](aws-iam.md).

From `src/detect_respond/infrastructure/boto_revoker.py`:

```python
        self._iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status="Inactive")
```

Turns a key off without deleting it, so it can be examined later as evidence.

**Tests without a network.** `tests/unit/detect_respond/test_response.py` uses `botocore.stub.Stubber`, which replaces the network with prepared answers and checks the exact arguments of each call. If the code calls anything unexpected, or an expected call does not happen, the test fails.

**Layering.** boto3 is imported only in `infrastructure` (and the command line builds the adapter). The import-linter contract "Domain and application know nothing about AWS" fails the build if it appears in `domain` or `application` ([import-linter.md](import-linter.md)). mypy treats boto3 as untyped, with an override ([mypy.md](mypy.md)).

### Every boto3 call, one by one

**Vocabulary.** A boto3 **client** is an object with one Python method per API call of one AWS service ([aws-cli.md](aws-cli.md) shows the same calls from the command line). A method takes **keyword arguments** written in the service's own CamelCase (`Bucket="b"`), and returns a **dictionary** decoded from the service's JSON answer ([json.md](json.md)). An error answer from AWS is raised as an exception (`botocore.exceptions.ClientError`) and not returned. The client finds its credentials by itself, in a fixed order called the **credential provider chain**: environment variables, then the shared credentials file, then the role of the machine or function it runs on; no secret is written in the code.

From `src/detect_respond/infrastructure/boto_revoker.py` (lines 17 to 19):

```python
        self._iam = client or boto3.client(
            "iam", config=Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)
        )
```

`client or boto3.client(...)`: use the client that was passed in (tests pass a stubbed one) and otherwise create the real one. `"iam"` is the service name. IAM is a global service, so no Region is needed for the call itself. `Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=3, read_timeout=10)` builds botocore's tuning object. `retries` with `mode` `"standard"` retries a failed call (a throttling answer, a server error, a dropped connection) up to `max_attempts` attempts in total, waiting a little longer each time, and never retries a mistake in the request itself. `connect_timeout=3` gives up if the connection is not made within 3 seconds; `read_timeout=10` gives up if the answer does not start within 10 seconds. Without them a stuck network would hold the program until the platform's own limit.

From `src/detect_respond/infrastructure/boto_revoker.py` (line 23):

```python
        response = self._iam.list_access_keys(UserName=user_name)
```

`list_access_keys` lists a user's access keys. `UserName` is the user. The answer has `AccessKeyMetadata`, a list with one dictionary per key (`AccessKeyId`, `Status`, `CreateDate`, `UserName`); the code keeps only the ids. The answer is paged when there are many keys (`IsTruncated`), and an IAM user can have at most two keys, so one page is enough.

From `src/detect_respond/infrastructure/boto_revoker.py` (line 28):

```python
        self._iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))
```

`put_role_policy` creates or replaces an inline policy of a role. `RoleName` and `PolicyName` identify it; `PolicyDocument` is the policy as **JSON text**, not a dictionary, which is why the code calls `json.dumps(policy)`. A second call with the same names replaces the first, which is why containment can be repeated safely.

From `src/detect_respond/infrastructure/boto_revoker.py` (line 32):

```python
        self._iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status="Inactive")
```

`update_access_key` changes the state of one key. `UserName` and `AccessKeyId` select it and `Status="Inactive"` switches it off (the other value is `"Active"`). The key is not deleted, so it stays available as evidence, and the call is the same if the key is already inactive.

From `tests/unit/detect_respond/test_response.py` (line 97):

```python
    iam = boto3.client("iam", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
```

In tests a real client is created with made-up credentials and a fixed `region_name` because a client will not start without them. It never sends anything: the next lines wrap it in a `Stubber`.

From `tests/unit/detect_respond/test_response.py` (line 99):

```python
    with Stubber(iam) as stub:
```

`botocore.stub.Stubber` replaces the network of one client with a queue of prepared answers; `with ... as stub` switches it on for the block and off afterwards.

From `tests/unit/detect_respond/test_response.py` (lines 100 to 104):

```python
        stub.add_response(
            "list_access_keys",
            {"AccessKeyMetadata": [{"AccessKeyId": "AKIADRILLEXAMPLE0001"}], "IsTruncated": False},
            {"UserName": "u"},
        )
```

`stub.add_response(method, answer, expected_arguments)` queues one answer: the next call of that method returns `answer` if (and only if) it is made with exactly `expected_arguments`. A different call raises an error and fails the test. Three are queued here, one for each of the three methods above.

From `tests/unit/detect_respond/test_response.py` (line 115):

```python
        stub.assert_no_pending_responses()
```

Fails the test if a queued answer was never used, so the test proves that all three calls were made.

From `tests/unit/detect_respond/test_response.py` (line 119):

```python
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
```

A client built by `BotoRevoker()` with no argument needs a Region. `monkeypatch.setenv` sets the environment variable for this one test and restores it afterwards.

## Try it yourself

```bash
.venv/bin/python -c "import boto3, botocore; print(boto3.__version__, botocore.__version__)"
```

Expect `1.43.119 1.43.119`.

```bash
.venv/bin/python - <<'E'
import boto3
from botocore.stub import Stubber
from detect_respond.infrastructure.boto_revoker import BotoRevoker
c = boto3.client("iam", region_name="us-east-1", aws_access_key_id="x", aws_secret_access_key="x")
with Stubber(c) as s:
    s.add_response("list_access_keys", {"AccessKeyMetadata": [{"AccessKeyId": "AKIAEXAMPLE0000000001", "UserName": "drill-user", "Status": "Active"}]}, {"UserName": "drill-user"})
    print(BotoRevoker(c).list_access_keys("drill-user"))
    s.assert_no_pending_responses()
E
```

Expect `('AKIAEXAMPLE0000000001',)`. No network is touched (the keys `x` are fake): the stub answers instead of AWS.

```bash
.venv/bin/pytest tests/unit/detect_respond/test_response.py -q
```

Expect `21 passed`.

## Mistakes people make

- Putting access keys in code or in a committed file. boto3 finds credentials from a profile or the environment; the scripts use a profile per account.
- Leaving out timeouts. A call with no timeout can hang a responder at the worst moment.
- Calling `delete_access_key` where `update_access_key` would do. Deleting destroys evidence; deactivating stops use.
- Importing boto3 in business logic. It makes the rules impossible to test without the cloud; the layering contract prevents it.
- Revoking only the key. A role session issued earlier stays alive until it expires, which is why containment also attaches a policy to the role.

## Check yourself

1. What is a client? *An object for one service whose methods match its API operations.*
2. Why does the adapter take a `client` argument? *So a test can pass a stubbed client and no network is needed.*
3. What does `Stubber` do? *Replaces the network with prepared answers and checks the arguments of each call.*
4. Why is `put_role_policy` safe to repeat? *It is idempotent: the same name replaces the policy.*
5. Where may boto3 be imported? *In `infrastructure` (and the command line that builds the adapter), never in `domain` or `application`.*

## Further reading

- boto3 documentation (1.43): <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
- botocore stubs: <https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html>
- IAM API reference: <https://docs.aws.amazon.com/IAM/latest/APIReference/>
