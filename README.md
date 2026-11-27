# Chiplet Interconnect Simulator

A Python model for comparing chiplet interconnect types, topologies and packet traffic. 
The model supports electrical or optical interconnects, repeatable traffic patterns, 
symbolic results for unknown parameter values, and simple topology presets.

## Run the visualizer

From the workspace folder containing `software_model`:

```powershell
python -m software_model.visualize
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) in a browser. The simulator
uses only the Python standard library; no package installation or virtual
environment is currently required.

## Current model and units

The editable equations are centralized in
[`software_model/formulas.py`](./software_model/formulas.py). Update the formulas and their focused
checks there when changing a model assumption. The interconnect classes and
packet simulator call these shared functions rather than maintaining separate
copies of the equations.

Current assumptions:

- Electrical `data_rate` is the transfer rate per lane in Gtransfer/s.
  Electrical aggregate rate in Gbit/s is
  `data_rate × lane_width × lane_count`, where `lane_width` is the number of
  bits transferred per transfer on each lane.
- Optical `data_rate` is in Gbit/s per wavelength.
  `wavelength_count` is the number of wavelengths carried per fiber, and
  `channel_count` is the number of physical transmit fibers or waveguides.
  Optical aggregate rate is
  `data_rate × wavelength_count × channel_count`.
- Effective bandwidth: `min(aggregate rate, bandwidth_density × area_footprint)`.
- Packet serialization latency: `packet_size_bits / effective_bandwidth`, with
  the Gbit/s-to-ns-to-ps conversion applied.
- Packet energy: `packet_size_bits × energy_per_bit`.
- Packet error probability: `1 - (1 - BER) ** packet_size_bits`, assuming
  independent bit errors.
- End-to-end packet error probability combines independent hop success
  probabilities.

### Final simulation outputs

The dashboard's reported summary metrics use these functions in
[`software_model/formulas.py`](./software_model/formulas.py):

- **Packets delivered:** count of packets for which a route was found and
  simulated. Currently, an unroutable packet raises an error and stops the run;
  partial delivery/drop behavior is TBD.
- **Average latency / packet (ps):**
  `sum(successfully routed packet latencies) / successfully routed packet count`.
  Each packet latency is the sum across its path of base link latency,
  serialization latency, and (for optical links) both conversion latencies.
- **Total energy (pJ):**
  `sum(packet energy across all successfully routed packets)`.
- **Average packet error probability:**
  `sum(per-packet end-to-end error probability) / successfully routed packet count`.
  A packet's end-to-end error probability is
  `1 - product(1 - per-hop packet error probability)`.
- **Offered packet rate (packets/ns):**
  `generated packet count / configured simulation duration in ns`.

Empty simulations report zero for aggregate metrics whose denominator would
otherwise be zero. Unknown parameter values remain symbolic in metrics where
the expression can be evaluated symbolically.

| Quantity | Unit |
| --- | --- |
| Latency and optical conversion latency | ps |
| Electrical transfer rate | Gtransfer/s |
| Optical rate per wavelength and effective bandwidth | Gbit/s |
| Electrical lane width | bits/transfer/lane |
| Electrical lane count | lanes |
| Optical wavelength and fiber/waveguide counts | wavelengths/fiber; fibers/waveguides |
| Bandwidth density | Gbit/s/mm² |
| Area footprint | mm² |
| Energy per bit | pJ/bit |
| Total packet energy | pJ |
| Interconnect reach and link distance | mm |
| Optical wavelength | nm |
| Simulation duration | ns |
| Offered packet rate | packets/ns |

Reach is enforced when both the interconnect reach and link distance are
known. The current simulator routes packets independently and does not model
arrival times, queues, congestion, or contention. A traffic matrix’s duration
is used for offered packet rate; it does not yet schedule packet arrivals.

## Current workflow

The dashboard supports mesh, ring, star, line, and fully connected topology
presets. It uses one interconnect configuration across the system, permits
individual links to be disconnected, sets link distances to a default of
1 mm, and allows each distance to be adjusted. A seeded random traffic matrix
can be reused to compare topology/interconnect configurations.

The Python API also exposes `InterconnectGraph.from_topology(...)` and
`topology_pairs(...)` for use without the dashboard.

## Planned work

- **TBD — Interconnect libraries:** Load multiple electrical and optical
  interconnect definitions from a documented data format; validate parameter
  names, units, and required fields.
- **TBD — Simulation sweeps:** Define sweep dimensions such as topology,
  link distances, data rate, electrical lane width/count, optical wavelength
  and fiber/waveguide counts, packet size, and traffic configuration.
- **TBD — Comparable iterations:** Reuse the same generated traffic matrix
  across every sweep point and record the exact parameters and seed.
- **TBD — Results storage and export:** Save each iteration’s input settings
  and output metrics to CSV/JSON for analysis and reproducibility.
- **TBD — Results exploration:** Compare iterations with sortable tables,
  plots, and filters for latency, energy, error probability, and delivery.
- **TBD — Time-based simulation:** Schedule packet arrivals over simulation
  duration and model contention, queues, and link capacity.
