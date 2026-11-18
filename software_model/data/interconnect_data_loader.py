import json
import warnings

from pathlib import Path
from dataclasses import fields
from typing import get_args, get_type_hints

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_components import (
    TRANSMITTER_PARTS,
    RECEIVER_PARTS,
)
from software_model.data.metrics import (
    Metric,
    AggregateMetric,
    InterconnectOverall,
)
from software_model.data.formulas import calculate_bandwidth

from software_model.data.interconnect_classes.interconnect import Interconnect
from software_model.data.interconnect_classes.transmitter import Transmitter
from software_model.data.interconnect_classes.receiver import Receiver
from software_model.data.interconnect_classes.channel import Channel

"""
- Missing components are initialized to None.
- Missing aggregate fields use empty aggregate objects.
- Explicit null values remain None.
- Missing measurements generate warnings, not errors.
- Unknown fields and unknown component names still raise errors.
- Reported aggregate values take precedence over their component breakdowns.
- Nested Metric and AggregateMetric structures are supported.
- Interconnect aggregates are calculated after loading.
"""

BANDWIDTH_REL_TOLERANCE = 0.01
BANDWIDTH_ABS_TOLERANCE = 0.125  # 1 Gbps converted to GB/s


# Nested objects belonging to Interconnect.
NESTED_CLASSES = {
    "transmitter": Transmitter,
    "receiver": Receiver,
    "channel": Channel,
}


# Expected component names for each TX/RX aggregate.
COMPONENT_DEFINITIONS = {
    Transmitter: TRANSMITTER_PARTS,
    Receiver: RECEIVER_PARTS,
}


# ==================================================
# JSON loading and validation
# ==================================================

def load_json(file_path):
    """Read JSON input file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_fields(data, cls, label):
    """Reject JSON keys that do not exist in the target dataclass."""

    if not isinstance(data, dict):
        raise TypeError(f"{label} must be a JSON object.")

    valid_fields = {
        field.name
        for field in fields(cls)
        if field.init
    }

    unknown_fields = set(data) - valid_fields

    if unknown_fields:
        raise ValueError(
            f"Unknown parameters in {label}: {sorted(unknown_fields)}"
        )


def contains_type(annotation, target_type):
    """Check whether a type annotation contains a target type."""

    if annotation is target_type:
        return True

    return any(
        contains_type(arg, target_type)
        for arg in get_args(annotation)
    )


# ==================================================
# Measurement construction
# ==================================================

def create_metric(data):
    """Create an individual Metric."""

    if data is None:
        return None

    validate_fields(data, Metric, "Metric")

    if data.get("value") is None:
        raise ValueError("A Metric must have a value.")

    if (
        not isinstance(data["value"], (int, float))
        or isinstance(data["value"], bool)
    ):
        raise TypeError("Metric value must be numeric.")

    if not isinstance(data.get("unit"), str) or not data["unit"].strip():
        raise ValueError("A Metric must have a non-empty unit.")

    if data.get("notes") is not None and not isinstance(data["notes"], str):
        raise TypeError("Metric notes must be a string.")

    return Metric(**data)


def create_measurement(data):
    """
    Create a Metric or nested AggregateMetric.

    JSON containing reported/components represents an AggregateMetric.
    Other measurement objects represent an individual Metric.
    """

    if data is None:
        return None

    if not isinstance(data, dict):
        raise TypeError("A measurement must be a JSON object or null.")

    if "reported" in data or "components" in data:
        return create_aggregate_metric(data)

    return create_metric(data)


def create_aggregate_metric(data, expected_components=None):
    """
    Create an AggregateMetric.

    Missing expected components are initialized to None.
    Supplied components are recursively converted.
    """

    if data is None:
        data = {}

    validate_fields(data, AggregateMetric, "AggregateMetric")

    supplied_components = data.get("components") or {}

    if not isinstance(supplied_components, dict):
        raise TypeError("Aggregate components must be a JSON object.")

    if expected_components is not None:
        expected = set(expected_components)
        supplied = set(supplied_components)

        unknown = supplied - expected

        if unknown:
            raise ValueError(
                f"Unknown aggregate components: {sorted(unknown)}"
            )

        components = {
            name: create_measurement(supplied_components.get(name))
            for name in expected_components
        }
    else:
        components = {
            name: create_measurement(value)
            for name, value in supplied_components.items()
        }

    return AggregateMetric(
        reported=create_metric(data.get("reported")),
        components=components,
    )


def create_interconnect_overall(data):
    """Create an interconnect-level aggregate."""

    if data is None:
        return InterconnectOverall()

    validate_fields(data, InterconnectOverall, "InterconnectOverall")

    unsupported = set(data) - {"reported"}

    if unsupported:
        raise ValueError(
            "Interconnect aggregates can only contain 'reported'. "
            f"Unsupported fields: {sorted(unsupported)}"
        )

    return InterconnectOverall(
        reported=create_metric(data.get("reported"))
    )


# ==================================================
# Missing measurement warnings
# ==================================================

def warn_missing_components(aggregate, label):
    """Warn about unavailable aggregate and component measurements."""

    if aggregate.reported is None:
        warnings.warn(
            f"Missing reported aggregate: {label}",
            stacklevel=2,
        )

    for name, measurement in aggregate.components.items():
        if measurement is None:
            warnings.warn(
                f"Missing component measurement: {label}.{name}",
                stacklevel=2,
            )
        elif isinstance(measurement, AggregateMetric):
            warn_missing_components(
                measurement,
                f"{label}.{name}",
            )


# ==================================================
# Dataclass construction
# ==================================================

def create_dataclass(data, cls, label, interconnect_type=None):
    """Create an Interconnect, Transmitter, Receiver, or Channel."""

    validate_fields(data, cls, label)

    data = data.copy()
    type_hints = get_type_hints(cls)

    kwargs = {}
    parent_type = interconnect_type

    # Parse and validate the interconnect type.
    if "interconnect_type" in type_hints:
        value = data.pop("interconnect_type", interconnect_type)

        if value is None:
            raise ValueError(f"Missing interconnect type in {label}.")

        try:
            parsed_type = (
                value
                if isinstance(value, InterconnectType)
                else InterconnectType(value.strip().lower())
            )
        except (AttributeError, ValueError):
            raise ValueError(f"Invalid interconnect type: {value}")

        if (
            interconnect_type is not None
            and parsed_type != interconnect_type
        ):
            raise ValueError(
                f"{label} interconnect type must match its parent."
            )

        parent_type = parsed_type
        kwargs["interconnect_type"] = parsed_type

    for name, value in data.items():
        annotation = type_hints[name]

        # Nested Interconnect objects.
        if name in NESTED_CLASSES:
            if value is None:
                kwargs[name] = None
            else:
                nested_cls = NESTED_CLASSES[name]

                kwargs[name] = create_dataclass(
                    value,
                    nested_cls,
                    name,
                    interconnect_type=(
                        parent_type
                        if nested_cls in (Transmitter, Receiver)
                        else None
                    ),
                )

        # Interconnect-level aggregates.
        elif contains_type(annotation, InterconnectOverall):
            kwargs[name] = create_interconnect_overall(value)

        # Fields that allow either Metric or AggregateMetric.
        elif (
            contains_type(annotation, Metric)
            and contains_type(annotation, AggregateMetric)
        ):
            kwargs[name] = create_measurement(value)

        # TX/RX aggregate fields.
        elif contains_type(annotation, AggregateMetric):
            if cls not in COMPONENT_DEFINITIONS:
                raise TypeError(
                    f"No component definitions registered for {cls.__name__}."
                )

            definitions = COMPONENT_DEFINITIONS[cls]

            if name not in definitions:
                raise ValueError(
                    f"No component definitions for {cls.__name__}.{name}."
                )

            kwargs[name] = create_aggregate_metric(
                value,
                expected_components=definitions[name],
            )

        # Individual measurements.
        elif contains_type(annotation, Metric):
            kwargs[name] = create_metric(value)

        else:
            kwargs[name] = value

    try:
        obj = cls(**kwargs)
    except TypeError as error:
        raise ValueError(
            f"Invalid {label} parameters: {error}"
        ) from error

    # Warn about missing TX/RX measurements.
    if cls in COMPONENT_DEFINITIONS:
        for aggregate_name in COMPONENT_DEFINITIONS[cls]:
            warn_missing_components(
                getattr(obj, aggregate_name),
                f"{label}.{aggregate_name}",
            )

    return obj


# ==================================================
# Interconnect construction
# ==================================================

def create_interconnect(data):
    """Create and calculate one Interconnect."""

    interconnect = create_dataclass(
        data,
        Interconnect,
        "Interconnect",
    )

    if (
        not isinstance(interconnect.interconnect_id, str)
        or not interconnect.interconnect_id.strip()
    ):
        raise ValueError("Interconnect ID must be a non-empty string.")

    if not isinstance(interconnect.interconnect_type, InterconnectType):
        raise ValueError("Invalid interconnect type.")

    if (
        not isinstance(interconnect.source, str)
        or not interconnect.source.strip()
    ):
        raise ValueError(
            f"Missing or invalid source for {interconnect.interconnect_id}."
        )

    # Calculate energy, power, area, PHY latency, and total latency.
    interconnect.calculate_aggregates()

    return interconnect


# ==================================================
# Bandwidth and latency validation
# ==================================================

def validate_bandwidth(interconnect):
    """Compare reported and calculated bandwidth."""

    reported = interconnect.bandwidth
    reported_value = reported.value if reported else None

    calculated = calculate_bandwidth(interconnect)

    if reported_value is not None and calculated is not None:
        difference = abs(reported_value - calculated)

        tolerance = max(
            BANDWIDTH_ABS_TOLERANCE,
            BANDWIDTH_REL_TOLERANCE * abs(reported_value),
        )

        if difference > tolerance:
            raise ValueError(
                f"[BANDWIDTH DISCREPANCY] "
                f"{interconnect.interconnect_id}: "
                f"Reported = {reported_value}, "
                f"Calculated = {calculated}, "
                f"Difference = {difference}"
            )

    if reported_value is None:
        if calculated is None:
            raise ValueError(
                f"Missing bandwidth for {interconnect.interconnect_id}: "
                "insufficient parameters to calculate it."
            )

        interconnect.bandwidth = Metric(
            value=calculated,
            unit="GB/s",
            notes="Calculated from data rate and lane configuration.",
        )

    return {
        "interconnect_id": interconnect.interconnect_id,
        "reported": reported_value,
        "calculated": calculated,
        "effective_bandwidth": interconnect.bandwidth.value,
        "status": (
            "matched"
            if reported_value is not None and calculated is not None
            else "reported_only"
            if reported_value is not None
            else "calculated_only"
        ),
    }


def validate_total_latency(interconnect):
    """Return the total latency calculation result."""

    aggregate = interconnect.total_latency

    return {
        "reported": (
            aggregate.reported.value
            if aggregate.reported else None
        ),
        "calculated": (
            aggregate.calculated_total.value
            if aggregate.calculated_total else None
        ),
        "partial": (
            aggregate.partial_total.value
            if aggregate.partial_total else None
        ),
        "effective": aggregate.value,
        "status": aggregate.status.value,
    }


# ==================================================
# Main loader
# ==================================================

def load_interconnects(file_path):
    """
    Load interconnect JSON data.

    Returns:
        interconnects: Loaded Interconnect objects.
        validation_report: Bandwidth and latency validation results.
    """

    raw_data = load_json(file_path)

    if not isinstance(raw_data, dict):
        raise ValueError("JSON root must be an object.")

    if "interconnects" not in raw_data:
        raise ValueError("Missing 'interconnects' in JSON.")

    entries = raw_data["interconnects"]

    if not isinstance(entries, list):
        raise ValueError("'interconnects' must be a list.")

    interconnects = []
    validation_report = []

    seen_ids = set()
    seen_sources = set()

    for entry in entries:
        interconnect = create_interconnect(entry)

        # Check duplicate IDs.
        id_key = interconnect.interconnect_id.strip().casefold()

        if id_key in seen_ids:
            raise ValueError(
                f"Duplicate interconnect ID: {interconnect.interconnect_id}"
            )

        seen_ids.add(id_key)

        # Check duplicate sources.
        source_key = interconnect.source.strip().casefold()

        if source_key in seen_sources:
            raise ValueError(
                f"Duplicate source: {interconnect.source}"
            )

        seen_sources.add(source_key)

        bandwidth_report = validate_bandwidth(interconnect)
        latency_report = validate_total_latency(interconnect)

        interconnects.append(interconnect)

        validation_report.append({
            "interconnect_id": interconnect.interconnect_id,
            "bandwidth": bandwidth_report,
            "total_latency": latency_report,
        })

    return interconnects, validation_report