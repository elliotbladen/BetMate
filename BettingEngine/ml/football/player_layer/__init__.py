"""Player availability and line-up infrastructure for football shadow pricing.

This package does not change the established EPL/Championship price.  It records
the pre-match evidence needed to train and evaluate a future player correction
layer honestly.
"""

from .availability import AvailabilityStore, AvailabilityStatus, SnapshotStage

__all__ = ["AvailabilityStore", "AvailabilityStatus", "SnapshotStage"]
