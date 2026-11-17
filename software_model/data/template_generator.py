
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
from software_model.data.interconnect_components import (
    RECEIVER_PARTS,
    TRANSMITTER_PARTS,
)
from software_model.data.metrics import Metric, AggregateMetric


def _unwrap_optional(annotation):
    """Return the underlying type of an Optional annotation."""
    origin = get_origin(annotation)

    if origin in (Union, UnionType):
        args = [
            arg for arg in get_args(annotation)
            if arg is not type(None)
        ]
        if len(args) == 1:
            return args[0]

    return annotation


def generate_interconnect_template(
    cls,
    interconnect_type,
    component_parts,
):
    """
    Generate a JSON-compatible template from a dataclass.

    Individual Metric fields are initialized to None.
    AggregateMetric fields contain only a reported field.
    Component fields are generated from the component dictionaries.
    """

    if cls is Metric:
        return None

    if cls is AggregateMetric:
        return {"reported": None}

    if not is_dataclass(cls):
        return None

    template = {}
    type_hints = get_type_hints(cls)

    for field in fields(cls):
        name = field.name
        annotation = _unwrap_optional(type_hints[name])

        # Set the interconnect type.
        if name == "interconnect_type":
            template[name] = interconnect_type.value
            continue

        # Generate component fields from the component dictionary.
        if name == "components" and cls in component_parts:
            parts = component_parts[cls][interconnect_type]

            components = dict.fromkeys(
                component
                for component_list in parts.values()
                for component in component_list
            )

            template[name] = {
                component: {
                    aggregate: None
                    for aggregate, component_list in parts.items()
                    if component in component_list
                }
                for component in components
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

        # All other fields start unreported.
        template[name] = None

    return template


def generate_dummy_json(
    interconnect_cls,
    component_parts,
    output_path=None,
):
    """
    Generate optical and electrical dummy interconnect JSON.

    Optionally writes the generated JSON to a file.
    """

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

    output = {"interconnects": interconnects}

    if output_path is not None:
        output_path = Path(output_path)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(output, file, indent=4)

    return output


component_parts = {
    Transmitter: TRANSMITTER_PARTS,
    Receiver: RECEIVER_PARTS,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate an electrical and optical interconnect JSON template."
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        type=Path,
        help="write the template to this file instead of printing it",
    )
    args = parser.parse_args()

    output = generate_dummy_json(
        Interconnect,
        component_parts,
        args.output_path,
    )

    if args.output_path is None:
        print(json.dumps(output, indent=4))
    else:
        print(f"Template written to {args.output_path}")


if __name__ == "__main__":
    main()