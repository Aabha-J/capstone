from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MeasurementStatus(Enum):
    """Describes the completeness of a measurement."""

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
    """Stores a reported aggregate and its component measurements."""

    reported: Optional[Metric] = None
    components: dict[
        str,
        Optional[Metric | AggregateMetric],
    ] = field(default_factory=dict)


@dataclass
class InterconnectOverall:
    """Stores an interconnect's overall measurement and full component breakdown."""

    # Overall measurement
    reported: Optional[Metric] = None
    calculated_total: Optional[Metric] = None
    partial_total: Optional[Metric] = None

    # Original inputs, including nested component breakdowns
    components: dict[
        str,
        Optional[Metric | AggregateMetric | InterconnectOverall],
    ] = field(default_factory=dict)

    formula: Optional[str] = None

    def __post_init__(self):
        """Ensure that only one overall result is populated."""
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
        """Return the active overall measurement, if one exists."""
        return (
            self.reported
            or self.calculated_total
            or self.partial_total
        )

    @property
    def value(self) -> Optional[float]:
        """Return the overall numerical value."""
        return self.metric.value if self.metric else None

    @property
    def status(self) -> MeasurementStatus:
        """Return the completeness status of the overall measurement."""
        if self.reported is not None or self.calculated_total is not None:
            return MeasurementStatus.COMPLETE

        if self.partial_total is not None:
            return MeasurementStatus.PARTIAL

        return MeasurementStatus.UNAVAILABLE

    @staticmethod
    def _resolve(
        measurement: Optional[
            Metric | AggregateMetric | InterconnectOverall
        ],
    ) -> tuple[Optional[Metric], MeasurementStatus]:
        """Recursively resolve a measurement without discarding its breakdown."""

        if measurement is None:
            return None, MeasurementStatus.UNAVAILABLE

        if isinstance(measurement, Metric):
            if measurement.value is None:
                return None, MeasurementStatus.UNAVAILABLE

            return measurement, MeasurementStatus.COMPLETE

        # A reported aggregate takes precedence over its components.
        if isinstance(measurement, AggregateMetric):
            if measurement.reported is not None:
                return InterconnectOverall._resolve(measurement.reported)

            parts = measurement.components

        else:
            # An InterconnectOverall may already have a resolved result.
            if measurement.reported is not None:
                return InterconnectOverall._resolve(measurement.reported)

            if measurement.calculated_total is not None:
                return (
                    measurement.calculated_total,
                    MeasurementStatus.COMPLETE,
                )

            if measurement.partial_total is not None:
                return (
                    measurement.partial_total,
                    MeasurementStatus.PARTIAL,
                )

            parts = measurement.components

        # Resolve nested components.
        available = []
        complete = True

        for part in parts.values():
            metric, status = InterconnectOverall._resolve(part)

            if metric is not None:
                available.append(metric)

            if status != MeasurementStatus.COMPLETE:
                complete = False

        if not available:
            return None, MeasurementStatus.UNAVAILABLE

        unit = available[0].unit

        if any(metric.unit != unit for metric in available):
            raise ValueError("Component measurement units do not match.")

        total = Metric(
            value=sum(metric.value for metric in available),
            unit=unit,
        )

        if complete and len(available) == len(parts):
            return total, MeasurementStatus.COMPLETE

        return total, MeasurementStatus.PARTIAL

    def calculate_sum(
        self,
        parts: dict[
            str,
            Optional[Metric | AggregateMetric | InterconnectOverall],
        ],
        formula: str,
    ) -> "InterconnectOverall":
        """Calculate an overall sum while retaining all original inputs."""

        # Preserve the complete input hierarchy.
        self.components = parts.copy()
        self.formula = formula

        # A reported overall total takes precedence.
        if self.reported is not None:
            return self

        # Clear previous calculated results before recalculating.
        self.calculated_total = None
        self.partial_total = None

        available = []
        complete = True

        for part in parts.values():
            metric, status = self._resolve(part)

            if metric is not None:
                available.append(metric)

            if status != MeasurementStatus.COMPLETE:
                complete = False

        if not available:
            return self

        unit = available[0].unit

        if any(metric.unit != unit for metric in available):
            raise ValueError("Component measurement units do not match.")

        total = Metric(
            value=sum(metric.value for metric in available),
            unit=unit,
            notes=formula,
        )

        if complete and len(available) == len(parts):
            self.calculated_total = total
        else:
            self.partial_total = total

        return self