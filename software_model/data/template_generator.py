
import argparse
import json

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import get_args, get_origin, get_type_hints, Union
from types import UnionType

from software_model.data.enums import InterconnectType
from software_model.data.interconnect_classes.interconnect import Interconnect
from software_model.data.interconnect_classes.receiver import Receiver
from software_model.data.interconnect_classes.transmitter import Transmitter
from software_model.data.interconnect_classes.channel import Channel
from software_model.data.interconnect_components import (
    RECEIVER_PARTS,
    TRANSMITTER_PARTS,
)
from software_model.data.metrics import (
    Metric,
    AggregateMetric,
    InterconnectOverall,
)


COMPONENT_PARTS = {
    Transmitter: TRANSMITTER_PARTS,
    Receiver: RECEIVER_PARTS,
}


def unwrap_optional(annotation):
    """Return the non-None type from an Optional or Union annotation."""

    origin = get_origin(annotation)

    if origin in (Union, UnionType):
        args = [
            arg for arg in get_args(annotation)
            if arg is not type(None)
        ]

        if len(args) == 1:
            return args[0]

        return args

    return annotation


def generate_interconnect_template(
    cls,
    interconnect_type,
    component_parts=COMPONENT_PARTS,
):
    """Generate a JSON-compatible template from a dataclass."""

    if cls in (Metric,):
        return None

    if cls is AggregateMetric:
        return {
            "reported": None,
            "components": {},
        }

    if cls is InterconnectOverall:
        return {
            "reported": None,
        }

    if not is_dataclass(cls):
        return None

    template = {}
    type_hints = get_type_hints(cls)

    for field in fields(cls):
        name = field.name
        annotation = unwrap_optional(type_hints[name])

        # Set the interconnect type.
        if name == "interconnect_type":
            template[name] = interconnect_type.value
            continue

        # Generate TX/RX aggregate components.
        if annotation is AggregateMetric:
            if cls in component_parts:
                parts = component_parts[cls][interconnect_type]

                template[name] = {
                    "reported": None,
                    "components": {
                        component: None
                        for component in parts.get(name, [])
                    },
                }
            else:
                template[name] = {
                    "reported": None,
                    "components": {},
                }

            continue

        # Generate interconnect-level aggregates.
        if annotation is InterconnectOverall:
            template[name] = {
                "reported": None,
            }
            continue

        # Generate individual metrics.
        if annotation is Metric:
            template[name] = None
            continue

        # Handle fields that allow Metric or AggregateMetric.
        if isinstance(annotation, list):
            if Metric in annotation and AggregateMetric in annotation:
                template[name] = {
                    "reported": None,
                    "components": {},
                }
                continue

            if Metric in annotation:
                template[name] = None
                continue

            if AggregateMetric in annotation:
                template[name] = {
                    "reported": None,
                    "components": {},
                }
                continue

        # Recursively generate nested dataclasses.
        if is_dataclass(annotation):
            template[name] = generate_interconnect_template(
                annotation,
                interconnect_type,
                component_parts,
            )
            continue

        # Other fields start unreported.
        template[name] = None

    return template


def generate_dummy_json(
    interconnect_cls=Interconnect,
    component_parts=COMPONENT_PARTS,
    output_path=None,
):
    """Generate electrical and optical interconnect templates."""

    interconnects = []

    for interconnect_type in InterconnectType:
        interconnect = generate_interconnect_template(
            interconnect_cls,
            interconnect_type,
            component_parts,
        )

        interconnect["interconnect_id"] = (
            f"{interconnect_type.value}_dummy"
        )

        interconnects.append(interconnect)

    output = {
        "interconnects": interconnects,
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(output, file, indent=4)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Generate electrical and optical interconnect JSON templates."
    )

    parser.add_argument(
        "output_path",
        nargs="?",
        type=Path,
        help="Optional output JSON file path.",
    )

    args = parser.parse_args()

    output = generate_dummy_json(
        Interconnect,
        COMPONENT_PARTS,
        args.output_path,
    )

    if args.output_path is None:
        print(json.dumps(output, indent=4))
    else:
        print(f"Template written to {args.output_path}")


if __name__ == "__main__":
    main()