# Chiplet Interconnect Simulator

This project models packet traffic across a graph of chiplets connected by
electrical or optical interconnects. It includes a Python API and a local
interactive dashboard.

## Run the dashboard

From the workspace folder that contains the `capstone` package, run:

```powershell
python -m capstone.visualize
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). 
## Where formulas live

All model equations are in [`formulas.py`](./formulas.py). Start there when
changing assumptions. The main call sequence is:

```text
simulate_packet(packet)
  -> find a route using known edge latencies and reach
  -> for each edge on that route:
       check reach
       calculate effective bandwidth
       add base + serialization + optional optical-conversion latency
       add packet energy using edge and optional conversion energy
       calculate per-edge packet-error probability
  -> combine edge metrics into per-packet outputs
simulate(packets)
  -> aggregate per-packet outputs into final simulation metrics
```

`network.py` applies these functions once per traversed edge. `SimulationResult`
uses the batch output functions in `formulas.py`. The dashboard API returns
those same `SimulationResult` metrics.

## Exact current equations

In these formulas, `b` is a packet's size in bits; `E` is energy in pJ/bit;
`L` is latency in ps; rates are in Gbit/s; area is in mm²; distance and reach
are in mm. Optical conversion values are per packet bit or per conversion as
indicated by their UI fields (currently entered as pJ/bit and ps).

### Edge eligibility

For an edge with known distance and reach:

```text
edge is routable iff distance_mm <= reach_mm
```

If either value is unknown, the current model leaves the edge eligible. Edges
beyond known maximum reach are omitted from path finding.

### Effective edge bandwidth

```text
electrical_aggregate_rate = data_rate_Gbps * lane_count
optical_aggregate_rate    = data_rate_Gbps * wavelength_count * channel_count
area_limited_rate         = bandwidth_density_Gbps_per_mm2 * area_footprint_mm2
effective_bandwidth       = min(aggregate_rate, area_limited_rate)
```

The technology-specific aggregate rate and area limit are both needed. If any
input is unknown, the result is a symbolic expression rather than a guessed
number.

### Per-edge packet metrics

For each packet traversing each edge:

```text
edge_serialization_latency_ps = 1000 * b / effective_bandwidth_Gbps
```

The factor 1000 converts the result from ns to ps because bit count divided by
Gbit/s yields ns.

```text
electrical_edge_latency_ps =
    base_latency_ps + edge_serialization_latency_ps

optical_edge_latency_ps =
    base_latency_ps
    + edge_serialization_latency_ps
    + electrical_to_optical_conversion_latency_ps
    + optical_to_electrical_conversion_latency_ps
```

```text
electrical_edge_energy_pJ = b * energy_per_bit_pJ

optical_edge_energy_pJ =
    b * (energy_per_bit_pJ
         + electrical_to_optical_conversion_energy_pJ_per_bit
         + optical_to_electrical_conversion_energy_pJ_per_bit)
```

The bit-error model assumes independent bit errors:

```text
edge_packet_error_probability = 1 - (1 - BER) ** b
```

### Per-packet path metrics

For a route containing edges `e1 ... en`:

```text
packet_latency_ps = sum(edge_latency_ps[e] for e in route)
packet_energy_pJ  = sum(edge_energy_pJ[e] for e in route)
packet_error_probability =
    1 - product(1 - edge_packet_error_probability[e] for e in route)
```

The last expression assumes independent error events across edges. The route
finder chooses the path with the lowest estimated latency. When an edge has
unknown bandwidth, the final metric preserves the symbolic serialization
term, but route selection only uses known latency components; that route
choice is therefore provisional until the missing values are supplied.

### Final simulation outputs

For `N` successfully routed packets, with configured duration `T_ns`:

```text
packets_delivered = N
average_latency_ps = sum(packet_latency_ps) / N
total_energy_pJ = sum(packet_energy_pJ)
average_packet_error_probability =
    sum(packet_error_probability) / N
offered_packet_rate_packets_per_ns = generated_packet_count / T_ns
```

For an empty packet batch, average latency, total energy, and average error
probability are reported as zero. Currently, if any generated packet has no
route, simulation raises an error rather than reporting a partial delivery
count.

## Units

| Parameter/output | Unit |
| --- | --- |
| Base and conversion latency; packet latency | ps |
| Data rate; effective bandwidth | Gbit/s |
| Bandwidth density | Gbit/s/mm² |
| Interconnect area | mm² |
| Per-bit and conversion energy | pJ/bit |
| Packet and simulation energy | pJ |
| BER and packet error probability | unitless probability, 0–1 |
| Maximum reach and link distance | mm |
| Optical wavelength | nm |
| Simulation duration | ns |
| Offered packet rate | packets/ns |
| Packet size | bits |

## Current scope and planned work

The dashboard offers mesh, ring, star, line, and fully connected topology
presets. It uses one interconnect configuration system-wide and allows link
distances and connectivity to be adjusted. Seeded traffic matrices can be
reused to compare simulations.

The simulator routes packets independently. It does not yet schedule packet
arrivals, model queues/contention, or enforce aggregate bandwidth over time.
Simulation duration currently only determines offered packet rate.

Planned (TBD):

- Load multiple electrical/optical interconnect definitions from a validated
  data file.
- Run reproducible sweeps over interconnects, topology, distance, data rate,
  packet size, counts, and traffic inputs.
- Store every iteration's configuration and results; export CSV/JSON.
- Compare runs with sortable result tables, plots, and filters.
- Add time-based arrivals, capacity enforcement, queues, and contention.
