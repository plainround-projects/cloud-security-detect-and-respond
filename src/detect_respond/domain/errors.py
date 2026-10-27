"""Named errors of the detection and response tooling."""


class DetectRespondError(Exception):
    """Base class: every error this package raises on purpose."""


class UnsupportedPatternError(DetectRespondError):
    """A detection pattern uses an operator the matcher does not implement; guessing could hide a missed alert."""


class InvalidDetectionError(DetectRespondError):
    """A detection file is missing a field or has the wrong shape."""


class InvalidLogError(DetectRespondError):
    """A log or digest file cannot be read as the audit trail's format."""


class DrillError(DetectRespondError):
    """The events do not contain what the drill measurement needs."""


class PlanError(DetectRespondError):
    """The Terraform plan does not contain what the rule audit needs."""
