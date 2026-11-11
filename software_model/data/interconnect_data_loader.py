import json

from pathlib import Path
from dataclasses import fields

from .data_classes import *
from .formulas import calculate_bandwidth, calculate_total_latency


BANDWIDTH_REL_TOLERANCE = 0.01  # 1%
BANDWIDTH_ABS_TOLERANCE = 1.0   # 1 Gbps


def load_json(file_path):
    """Read JSON input file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def create_interconnect(data):
    """Convert a JSON dictionary into an Interconnect object."""

    if not isinstance(data, dict):
        raise TypeError("Interconnect entry must be a JSON object.")

    # Automatically discover supported dataclass parameters
    valid_fields = {
        f.name for f in fields(Interconnect) if f.init
    }

    # Catch misspelled or unsupported parameters
    unknown_fields = set(data) - valid_fields

    if unknown_fields:
        raise ValueError(
            f"Unknown parameters: {sorted(unknown_fields)}"
        )

    data = data.copy()

    # Convert JSON string into Python enum
    if "interconnect_type" in data:
        try:
            if not isinstance(data["interconnect_type"], str):
                raise ValueError

            data["interconnect_type"] = InterconnectType(
                data["interconnect_type"].strip().lower()
            )

        except ValueError:
            raise ValueError(
                f"Invalid interconnect type: {data['interconnect_type']}"
            )

    try:
        interconnect = Interconnect(**data)
    except TypeError as error:
        raise ValueError(
            f"Invalid interconnect parameters: {error}"
        ) from error

    # Validate identification
    if not isinstance(interconnect.interconnect_id, str) or not interconnect.interconnect_id.strip():
        raise ValueError("Interconnect ID must be a non-empty string.")

    if not isinstance(interconnect.interconnect_type, InterconnectType):
        raise ValueError("Invalid interconnect type.")

    # Validate source
    if not isinstance(interconnect.source, str) or not interconnect.source.strip():
        raise ValueError(
            f"Missing or invalid source for {interconnect.interconnect_id}."
        )

    return interconnect


def validate_bandwidth(interconnect):
    """Validate bandwidth and populate the effective bandwidth."""

    reported = interconnect.bandwidth
    calculated = calculate_bandwidth(interconnect)

    # Compare reported and calculated bandwidth when both exist
    if reported is not None and calculated is not None:

        difference = abs(reported - calculated)

        tolerance = max(
            BANDWIDTH_ABS_TOLERANCE,
            BANDWIDTH_REL_TOLERANCE * abs(reported)
        )

        if difference > tolerance:
            raise ValueError(
                f"[BANDWIDTH DISCREPANCY] "
                f"{interconnect.interconnect_id}: "
                f"Reported = {reported} Gbps, "
                f"Calculated = {calculated} Gbps, "
                f"Difference = {difference} Gbps"
            )

    # Use calculated bandwidth only when no reported value exists
    if reported is None:
        if calculated is None:
            raise ValueError(
                f"Missing bandwidth for {interconnect.interconnect_id}: "
                f"insufficient parameters to calculate it."
            )

        interconnect.bandwidth = calculated

    return {
        "interconnect_id": interconnect.interconnect_id,
        "reported": reported,
        "calculated": calculated,
        "effective_bandwidth": interconnect.bandwidth,
        "status": (
            "matched" if reported is not None and calculated is not None
            else "reported_only" if reported is not None
            else "calculated_only"
        )
    }

def validate_total_latency(interconnect):
    """Validate reported total latency or calculate it if possible."""

    reported = interconnect.total_latency
    calculated = calculate_total_latency(interconnect)

    # Compare when both values are available
    if reported is not None and calculated is not None:

        difference = abs(reported - calculated)

        tolerance = max(
            1e-12,
            0.01 * abs(reported)
        )

        if difference > tolerance:
            raise ValueError(
                f"[LATENCY DISCREPANCY] "
                f"{interconnect.interconnect_id}: "
                f"Reported = {reported}, "
                f"Calculated = {calculated}, "
                f"Difference = {difference}"
            )

    # Calculate only when no reported value exists
    if reported is None and calculated is not None:
        interconnect.total_latency = calculated

    return {
    "reported": reported,
    "calculated": calculated,
    "effective": interconnect.total_latency,
    "status": (
        "matched" if reported is not None and calculated is not None
        else "reported_only" if reported is not None
        else "calculated_only" if calculated is not None
        else "unavailable"
    )
    }

def load_interconnects(file_path):
    """
    Load JSON data and create Interconnect objects.

    Returns:
        interconnects: List of Interconnect objects
        validation_report: List of bandwidth and latency validation results
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

        # Check duplicate IDs
        id_key = interconnect.interconnect_id.strip().casefold()

        if id_key in seen_ids:
            raise ValueError(
                f"Duplicate interconnect ID: "
                f"{interconnect.interconnect_id}"
            )

        seen_ids.add(id_key)

        # Check duplicate sources
        source_key = interconnect.source.strip().casefold()

        if source_key in seen_sources:
            raise ValueError(
                f"Duplicate source '{interconnect.source}' "
                f"for {interconnect.interconnect_id}."
            )

        seen_sources.add(source_key)

        # Check optical-only conversion latency parameters
        if interconnect.interconnect_type == InterconnectType.ELECTRICAL:
            if (
                interconnect.oe_conversion_latency is not None
                or interconnect.eo_conversion_latency is not None
            ):
                raise ValueError(
                    f"Electrical interconnect {interconnect.interconnect_id} "
                    f"must not have oe_conversion_latency or "
                    f"eo_conversion_latency."
                )

        # Validate bandwidth (required)
        bandwidth_report = validate_bandwidth(interconnect)

        # Validate total latency (optional)
        latency_report = validate_total_latency(interconnect)

        interconnects.append(interconnect)

        validation_report.append({
            "interconnect_id": interconnect.interconnect_id,
            "bandwidth": bandwidth_report,
            "total_latency": latency_report
        })

    return interconnects, validation_report