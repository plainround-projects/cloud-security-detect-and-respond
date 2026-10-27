# alerting

One Region's alerting: a key, an encrypted topic that emails the responder, and one EventBridge rule and target per detection deployed there. The rule pattern is the detection file unchanged; the target's input transformer builds the alert text.

| | |
| --- | --- |
| Inputs | see `variables.tf` |
| Outputs | see `outputs.tf` |
| Provider | `hashicorp/aws` `~> 6.0` |

Instantiate once per Region that matters, passing the Region's provider. Step 2 of the lesson. See docs/DETECTIONS.md.
