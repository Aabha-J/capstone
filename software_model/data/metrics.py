
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MeasurementStatus(Enum):
    """Describes the completeness of an aggregate measurement."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass
class Metric:
    """Stores one individual measurement."""

    value: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AggregateMetric:
    """Stores an aggregate measurement."""

    # Only one of these three aggregate results can be populated.
    reported: Optional[Metric] = None
    calculated_total: Optional[Metric] = None
    partial_total: Optional[Metric] = None

    def __post_init__(self):
        """Ensure that only one aggregate result is stored at a time."""
        populated = sum(
            metric is not None
            for metric in (
                self.reported,
                self.calculated_total,
                self.partial_total,
            )
        )

        if populated > 1:
            raise ValueError(
                "Only one of reported, calculated_total, "
                "or partial_total can be populated."
            )

    @property
    def metric(self) -> Optional[Metric]:
        """Return the active aggregate measurement, if one exists."""
        return (
            self.reported
            or self.calculated_total
            or self.partial_total
        )

    @property
    def value(self) -> Optional[float]:
        """Return the aggregate numerical value, or None if unavailable."""
        return self.metric.value if self.metric else None

    @property
    def status(self) -> MeasurementStatus:
        """Return the completeness status of the aggregate measurement."""
        if self.reported is not None or self.calculated_total is not None:
            return MeasurementStatus.COMPLETE
        if self.partial_total is not None:
            return MeasurementStatus.PARTIAL
        return MeasurementStatus.UNAVAILABLE


def calculate_aggregate_sum(
    aggregate: AggregateMetric,
    parts: tuple[Optional[Metric], ...],
    formula: str,
) -> AggregateMetric:
    """Calculate an aggregate from its available component measurements."""

    if aggregate.reported is not None:
        return aggregate

    # Clear previous calculated results before recalculating.
    aggregate.calculated_total = None
    aggregate.partial_total = None

    available = [
        part for part in parts
        if part is not None
    ]

    if not available:
        return aggregate

    unit = available[0].unit

    if any(part.unit != unit for part in available):
        raise ValueError("Component measurement units do not match.")

    total = Metric(
        value=sum(part.value for part in available),
        unit=unit,
        notes=formula,
    )

    if len(available) == len(parts):
        aggregate.calculated_total = total
    else:
        aggregate.partial_total = total

    return aggregate