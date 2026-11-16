from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class MeasurementScope(Enum):
    # Aggregate measurements
    INTERCONNECT = "interconnect"
    PHY = "phy"
    TX_RX = "tx_rx"
    TX_RX_LASER = "tx_rx_laser"

    # Transmitter measurements
    TRANSMITTER = "transmitter"
    SERIALIZER = "serializer"
    MODULATOR = "modulator"
    LASER = "laser"
    EO_CONVERSION = "eo_conversion"

    # Receiver measurements
    RECEIVER = "receiver"
    DESERIALIZER = "deserializer"
    PHOTODETECTOR = "photodetector"
    OE_CONVERSION = "oe_conversion"

    # Channel measurements
    CHANNEL = "channel"


class MeasurementOrigin(Enum):
    REPORTED = "reported"
    CALCULATED = "calculated"


class MeasurementStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"

@dataclass
class Metric:
    value: Optional[float] = None
    unit: Optional[str] = None

    scope: Optional[MeasurementScope] = None
    origin: Optional[MeasurementOrigin] = None
    status: MeasurementStatus = MeasurementStatus.UNAVAILABLE

    source: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AggregateMetric:
    # Only one of these three can be populated.
    reported: Optional[Metric] = None
    calculated_total: Optional[Metric] = None
    partial_total: Optional[Metric] = None

    # Individual component measurements; None means unavailable.
    parts: dict[str, Optional[Metric]] = field(default_factory=dict)

    def __post_init__(self):
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
        """Return the active aggregate measurement."""
        return (
            self.reported
            or self.calculated_total
            or self.partial_total
        )

    @property
    def value(self) -> Optional[float]:
        return self.metric.value if self.metric else None

    @property
    def status(self) -> MeasurementStatus:
        if self.metric is None:
            return MeasurementStatus.UNAVAILABLE
        return self.metric.status

    @property
    def missing(self) -> list[str]:
        """Return component names whose measurements are unavailable."""
        return [
            name for name, metric in self.parts.items()
            if metric is None
        ]

    @classmethod
    def from_parts(
        cls,
        parts: dict[str, Optional[Metric]],
        unit: str,
        scope: MeasurementScope,
        formula: str,
    ) -> "AggregateMetric":
        """
        Build an aggregate from its component measurements.

        All parts available -> calculated_total.
        Some parts available -> partial_total.
        No parts available -> neither total is populated.
        """

        known = [
            metric for metric in parts.values()
            if metric is not None
            and metric.value is not None
            and metric.status != MeasurementStatus.UNAVAILABLE
        ]

        missing = [
            name for name, metric in parts.items()
            if metric is None
            or metric.value is None
            or metric.status == MeasurementStatus.UNAVAILABLE
        ]

        if not known:
            return cls(parts=parts)

        value = sum(metric.value for metric in known)

        # A total cannot be complete if any input is partial.
        complete = (
            not missing
            and all(
                metric.status == MeasurementStatus.COMPLETE
                for metric in known
            )
        )

        result = Metric(
            value=value,
            unit=unit,
            scope=scope,
            origin=MeasurementOrigin.CALCULATED,
            status=(
                MeasurementStatus.COMPLETE
                if complete
                else MeasurementStatus.PARTIAL
            ),
            notes=formula,
        )

        if complete:
            return cls(
                calculated_total=result,
                parts=parts,
            )

        return cls(
            partial_total=result,
            parts=parts,
        )


