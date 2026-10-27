# kms-key

A customer-managed encryption key with rotation on and an alias. The account root may administer the key but is not given `kms:Decrypt` or `kms:Encrypt`.

| | |
| --- | --- |
| Inputs | see `variables.tf` |
| Outputs | see `outputs.tf` |
| Provider | `hashicorp/aws` `~> 6.0` |

Used for the archive key (security account) and for each Region's alert topic.
