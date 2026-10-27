# drill

The deliberate, temporary weakness for the incident drill: a user, an over-privileged role, a bucket that can be made public, and optionally the honeytoken user. Created only when the environment's enable_drill is true. No access key is created here (it would sit in the state); scripts/04-drill-setup.sh creates it.

| | |
| --- | --- |
| Inputs | see `variables.tf` |
| Outputs | see `outputs.tf` |
| Provider | `hashicorp/aws` `~> 6.0` |

Step 4 of the lesson. The OPA rules allow PowerUserAccess, IAM users and open Block Public Access only inside this module.
