# log-archive

The tamper-resistant archive bucket in the security account: Object Lock in compliance mode, versioning, a customer-managed key, Block Public Access, a policy that admits only the workload account's trail and denies deleting objects and versions to every principal, and a lifecycle expiry.

| | |
| --- | --- |
| Inputs | see `variables.tf` |
| Outputs | see `outputs.tf` |
| Provider | `hashicorp/aws` `~> 6.0` |

Step 1 of the lesson. See ADR 0002.
