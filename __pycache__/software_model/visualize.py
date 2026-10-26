from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .classes import ElectricalInterconnect, OpticalInterconnect
from .formulas import (
    average_latency_ps,
    average_packet_error_probability,
    offered_packet_rate,
    total_energy_pj,
)
from .network import Chiplet, InterconnectGraph, topology_pairs
from .traffic_generation import RandomTrafficMatrixGenerator

_PAGE = Path(__file__).parent / "visualization" / "index.html"
_MAX_REQUEST_BYTES = 1_000_000
_MAX_CHIPLETS = 16
_MAX_PACKETS = 5_000


def _topology(request: dict[str, Any]) -> dict[str, Any]:
    names = request.get("chiplets")
    if not isinstance(names, list) or not 2 <= len(names) <= _MAX_CHIPLETS:
        raise ValueError(f"chiplets must contain between 2 and {_MAX_CHIPLETS} names.")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Chiplet names must be non-empty strings.")
    if len(set(names)) != len(names):
        raise ValueError("Chiplet names must be unique.")
    topology = request.get("topology")
    nodes = tuple(Chiplet(name) for name in names)
    return {
        "links": [
            [first.name, second.name] for first, second in topology_pairs(nodes, topology)
        ]
    }


def _metric(value: Any) -> float | str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _simulate(request: dict[str, Any]) -> dict[str, Any]:
    names = request.get("chiplets")
    if not isinstance(names, list) or not 2 <= len(names) <= _MAX_CHIPLETS:
        raise ValueError(f"chiplets must contain between 2 and {_MAX_CHIPLETS} names.")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Chiplet names must be non-empty strings.")
    if len(set(names)) != len(names):
        raise ValueError("Chiplet names must be unique.")

    total_packets = request.get("total_packets")
    packet_size = request.get("packet_size_bits")
    simulation_time = request.get("simulation_time")
    seed = request.get("seed")
    if isinstance(total_packets, bool) or not isinstance(total_packets, int) or not 0 <= total_packets <= _MAX_PACKETS:
        raise ValueError(f"total_packets must be an integer from 0 to {_MAX_PACKETS}.")
    if isinstance(packet_size, bool) or not isinstance(packet_size, int) or packet_size <= 0:
        raise ValueError("packet_size_bits must be a positive integer.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer.")
    if isinstance(simulation_time, bool) or not isinstance(simulation_time, (int, float)) or simulation_time <= 0:
        raise ValueError("simulation_time must be a positive number.")

    chiplets = tuple(Chiplet(name) for name in names)
    graph = InterconnectGraph()
    for chiplet in chiplets:
        graph.add_chiplet(chiplet)

    interconnect_config = request.get("interconnect")
    if not isinstance(interconnect_config, dict):
        raise ValueError("interconnect must define one system-wide type and metric set.")
    link_type = interconnect_config.get("type")
    metric_values = interconnect_config.get("metrics")
    if link_type not in ("electrical", "optical") or not isinstance(metric_values, dict):
        raise ValueError("System interconnect needs an electrical/optical type and metric values.")
    allowed_metrics = (
        set(ElectricalInterconnect.parameter_set_type.parameters)
        if link_type == "electrical"
        else set(OpticalInterconnect.parameter_set_type.parameters)
    )
    unsupported_metrics = set(metric_values) - allowed_metrics
    if unsupported_metrics:
        names = ", ".join(sorted(unsupported_metrics))
        raise ValueError(f"Unsupported {link_type} interconnect metric(s): {names}.")
    for metric_name, value in metric_values.items():
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError(f"Metric {metric_name!r} must be numeric or blank.")
    interconnect_type = (
        ElectricalInterconnect if link_type == "electrical" else OpticalInterconnect
    )
    interconnect = interconnect_type(**metric_values)

    links = request.get("links")
    if not isinstance(links, list):
        raise ValueError("links must be a list.")
    expected_pairs = {
        frozenset((names[first], names[second]))
        for first in range(len(names))
        for second in range(first + 1, len(names))
    }
    seen_pairs: set[frozenset[str]] = set()
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Each link must be an object.")
        first, second = link.get("first"), link.get("second")
        pair = frozenset((first, second)) if isinstance(first, str) and isinstance(second, str) else frozenset()
        if pair not in expected_pairs or pair in seen_pairs:
            raise ValueError("Each link must connect a unique pair of different chiplets.")
        seen_pairs.add(pair)
        enabled = link.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("Link enabled must be a boolean.")
        if not enabled:
            continue
        distance = link.get("distance")
        if distance is not None and (
            isinstance(distance, bool) or not isinstance(distance, (int, float))
        ):
            raise ValueError("Link distance must be numeric or blank.")
        graph.add_interconnect(
            next(chiplet for chiplet in chiplets if chiplet.name == first),
            next(chiplet for chiplet in chiplets if chiplet.name == second),
            interconnect,
            distance=distance,
        )
    if seen_pairs != expected_pairs:
        raise ValueError("Topology is incomplete; build the topology again and retry.")

    matrix = RandomTrafficMatrixGenerator.generate(
        chiplets,
        total_packets=total_packets,
        packet_size_bits=packet_size,
        simulation_time=simulation_time,
        seed=seed,
    )
    result = graph.simulate(matrix)
    grouped: dict[tuple[str, ...], list[Any]] = {}
    for packet_result in result.packets:
        key = tuple(chiplet.name for chiplet in packet_result.path)
        group = grouped.setdefault(key, [0, [], [], []])
        group[0] += 1
        group[1].append(packet_result.latency)
        group[2].append(packet_result.energy)
        group[3].append(packet_result.error_probability)

    # Keep dashboard summary values on the same final-output formulas exposed by
    # SimulationResult; use these functions if the reported metric definitions change.
    return {
        "matrix": {
            "chiplets": names,
            "counts": [list(row) for row in matrix.packet_counts],
        },
        "total_packets": matrix.total_packets,
        "delivered_packets": len(result.packets),
        "offered_packet_rate": offered_packet_rate(
            matrix.total_packets, matrix.simulation_time
        ),
        "average_latency": _metric(result.average_latency),
        "total_energy": _metric(result.total_energy),
        "average_error_probability": _metric(result.average_error_probability),
        "routes": [
            {
                "path": list(path),
                "count": values[0],
                "average_latency": _metric(average_latency_ps(values[1])),
            }
            for path, values in grouped.items()
        ],
    }


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        try:
            content = _PAGE.read_bytes()
        except OSError as error:
            self.send_error(500, f"Cannot read visualization page: {error}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        if self.path not in ("/api/simulate", "/api/topology"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > _MAX_REQUEST_BYTES:
                raise ValueError(f"Request body must be between 1 and {_MAX_REQUEST_BYTES} bytes.")
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("Request body must be a JSON object.")
            response = (
                _simulate(request)
                if self.path == "/api/simulate"
                else _topology(request)
            )
            self._send_json(200, response)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError):
            return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[visualizer] {self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), _Handler)
    print("Chiplet visualizer running at http://127.0.0.1:8765 (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping chiplet visualizer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
