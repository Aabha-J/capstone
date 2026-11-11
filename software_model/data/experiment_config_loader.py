import json
import math

from decimal import Decimal, InvalidOperation
from itertools import product
from pathlib import Path

from .data_classes import (
    ExperimentOptions,
    ExperimentConfig,
    Topology,
    TrafficPattern,
)


def load_json(file_path):
    """Read the JSON input file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def expand_values(value, name, value_type):
    """
    Convert an array or range into a list of values.

    Supported formats:
        [1, 2, 3]

        {"start": 1, "stop": 3, "step": 1}

    Range endpoints are inclusive.
    """

    if isinstance(value, list):
        raw_values = value

    elif isinstance(value, dict):
        if set(value) != {"start", "stop", "step"}:
            raise ValueError(
                f"{name} range must contain exactly "
                "'start', 'stop', and 'step'."
            )

        try:
            start = Decimal(str(value["start"]))
            stop = Decimal(str(value["stop"]))
            step = Decimal(str(value["step"]))

        except (InvalidOperation, TypeError):
            raise ValueError(f"Invalid range values for {name}.")

        if not all(number.is_finite() for number in (start, stop, step)):
            raise ValueError(f"{name} range values must be finite.")

        if step <= 0:
            raise ValueError(f"{name} range step must be positive.")

        if start > stop:
            raise ValueError(f"{name} range start cannot exceed stop.")

        if value_type is int:
            if any(number != number.to_integral_value()
                   for number in (start, stop, step)):
                raise ValueError(f"{name} range must use integer values.")

        raw_values = []
        current = start

        while current <= stop:
            raw_values.append(current)
            current += step

    else:
        raise TypeError(
            f"{name} must be an array or a range object."
        )

    if not raw_values:
        raise ValueError(f"{name} cannot be empty.")

    values = []

    for item in raw_values:

        if value_type is int:
            # bool is a subclass of int in Python, so reject it explicitly.
            if isinstance(item, bool):
                raise TypeError(f"{name} values must be integers.")

            try:
                number = Decimal(str(item))
            except (InvalidOperation, TypeError):
                raise TypeError(f"{name} values must be integers.")

            if not number.is_finite() or number != number.to_integral_value():
                raise TypeError(f"{name} values must be integers.")

            parsed = int(number)

        elif value_type is float:
            if isinstance(item, bool):
                raise TypeError(f"{name} values must be numbers.")

            try:
                parsed = float(item)
            except (ValueError, TypeError):
                raise TypeError(f"{name} values must be numbers.")

            if not math.isfinite(parsed):
                raise ValueError(f"{name} values must be finite.")

        else:
            parsed = item

        values.append(parsed)

    # Prevent accidentally generating duplicate configurations.
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicate values.")

    return values


def parse_enum_values(values, name, enum_type):
    """Convert strings into the corresponding enum values."""

    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list.")

    parsed_values = []

    for value in values:
        if not isinstance(value, str):
            raise TypeError(f"{name} values must be strings.")

        try:
            parsed = enum_type(value.strip())
        except ValueError:
            allowed = [item.value for item in enum_type]

            raise ValueError(
                f"Invalid {name} value '{value}'. "
                f"Allowed values: {allowed}"
            )

        parsed_values.append(parsed)

    if len(parsed_values) != len(set(parsed_values)):
        raise ValueError(f"{name} contains duplicate values.")

    return parsed_values


def validate_options(options):
    """Validate simulation option values."""

    if any(value < 1 for value in options.chiplet_counts):
        raise ValueError("Chiplet counts must be at least 1.")

    if any(value < 0 for value in options.link_distances):
        raise ValueError("Link distances cannot be negative.")

    if any(value < 1 for value in options.packet_sizes):
        raise ValueError("Packet sizes must be positive.")

    if any(not 0 <= value <= 1 for value in options.injection_rates):
        raise ValueError("Injection rates must be between 0 and 1.")

    if any(value < 1 for value in options.hotspot_counts):
        raise ValueError("Hotspot counts must be at least 1.")

    if any(
        not 0 <= value <= 1
        for value in options.hotspot_probabilities
    ):
        raise ValueError(
            "Hotspot probabilities must be between 0 and 1."
        )

    if any(value <= 0 for value in options.durations):
        raise ValueError("Durations must be positive.")

    if any(value < 0 for value in options.seeds):
        raise ValueError("Seeds cannot be negative.")


def create_experiment_options(data):
    """Convert JSON experiment options into an ExperimentOptions object."""

    if not isinstance(data, dict):
        raise TypeError("'experiment_options' must be a JSON object.")

    required_fields = {
        "chiplet_counts",
        "topologies",
        "link_distances",
        "traffic_patterns",
        "packet_sizes",
        "injection_rates",
        "hotspot_counts",
        "hotspot_probabilities",
        "durations",
        "seeds",
    }

    missing_fields = required_fields - set(data)
    unknown_fields = set(data) - required_fields

    if missing_fields:
        raise ValueError(
            f"Missing experiment options: {sorted(missing_fields)}"
        )

    if unknown_fields:
        raise ValueError(
            f"Unknown experiment options: {sorted(unknown_fields)}"
        )

    options = ExperimentOptions(
        chiplet_counts=expand_values(
            data["chiplet_counts"], "chiplet_counts", int
        ),
        topologies=parse_enum_values(
            data["topologies"], "topologies", Topology
        ),
        link_distances=expand_values(
            data["link_distances"], "link_distances", float
        ),
        traffic_patterns=parse_enum_values(
            data["traffic_patterns"], "traffic_patterns", TrafficPattern
        ),
        packet_sizes=expand_values(
            data["packet_sizes"], "packet_sizes", int
        ),
        injection_rates=expand_values(
            data["injection_rates"], "injection_rates", float
        ),
        hotspot_counts=expand_values(
            data["hotspot_counts"], "hotspot_counts", int
        ),
        hotspot_probabilities=expand_values(
            data["hotspot_probabilities"],
            "hotspot_probabilities",
            float,
        ),
        durations=expand_values(
            data["durations"], "durations", float
        ),
        seeds=expand_values(
            data["seeds"], "seeds", int
        ),
    )

    validate_options(options)

    return options


def generate_experiment_configs(options):
    """Generate all valid combinations of experiment options."""

    configs = []

    # Hotspot parameters only vary for hotspot traffic.
    for values in product(
        options.chiplet_counts,
        options.topologies,
        options.link_distances,
        options.traffic_patterns,
        options.packet_sizes,
        options.injection_rates,
        options.durations,
        options.seeds,
    ):

        (
            chiplet_count,
            topology,
            link_distance,
            traffic_pattern,
            packet_size,
            injection_rate,
            duration,
            seed,
        ) = values

        if traffic_pattern == TrafficPattern.HOTSPOT:
            hotspot_options = product(
                options.hotspot_counts,
                options.hotspot_probabilities,
            )
        else:
            hotspot_options = [(None, None)]

        for hotspot_count, hotspot_probability in hotspot_options:

            config_id = f"EXP_{len(configs) + 1:05d}"

            configs.append(
                ExperimentConfig(
                    config_id=config_id,
                    chiplet_count=chiplet_count,
                    topology=topology,
                    link_distance=link_distance,
                    traffic_pattern=traffic_pattern,
                    packet_size=packet_size,
                    injection_rate=injection_rate,
                    hotspot_count=hotspot_count,
                    hotspot_probability=hotspot_probability,
                    duration=duration,
                    seed=seed,
                )
            )

    return configs


def load_experiment_configs(file_path):
    """
    Load experiment options from JSON and generate configurations.

    Returns:
        options: ExperimentOptions object
        configs: List of ExperimentConfig objects
    """

    raw_data = load_json(file_path)

    if not isinstance(raw_data, dict):
        raise ValueError("JSON root must be an object.")

    if "experiment_options" not in raw_data:
        raise ValueError("Missing 'experiment_options' in JSON.")

    options = create_experiment_options(raw_data["experiment_options"])
    configs = generate_experiment_configs(options)

    return options, configs