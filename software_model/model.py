#for now just loads and prints experiment config json file and interconnect
from pathlib import Path

from .data.interconnect_data_loader import load_interconnects
from .data.experiment_config_loader import load_experiment_configs
from .simulation_setup.generate_graph import generate_graph


def main():

    interconnects_file = Path(__file__).with_name("interconnects.json")
    experiment_options_file = Path(__file__).with_name("experiment_configs.json")

    # Load interconnects
    interconnects, validation_report = load_interconnects(interconnects_file)

    # Load experiment configurations
    options, experiment_configs = load_experiment_configs(
        experiment_options_file
    )

    # Print validation results
    print("\n=== Interconnect Validation ===")
    for report in validation_report:
        print(f"\nInterconnect: {report['interconnect_id']}")
        print(f"Bandwidth: {report['bandwidth']}")
        print(f"Total Latency: {report['total_latency']}")

    # Generate a graph for each interconnect/configuration combination
    graphs = []

    for interconnect in interconnects:
        for config in experiment_configs:
            graph = generate_graph(interconnect, config)

            graphs.append({
                "interconnect_id": interconnect.interconnect_id,
                "config_id": config.config_id,
                "graph": graph,
            })

    print(f"\nGenerated {len(graphs)} graphs.")

    # Print graph summaries
    for result in graphs:
        graph = result["graph"]

        print(
            f"\nInterconnect: {result['interconnect_id']}"
            f"\nConfiguration: {result['config_id']}"
            f"\nVertices: {len(graph.vertices)}"
            f"\nEdges: {len(graph.edges)}"
        )


if __name__ == "__main__":
    main()