#for now just loads and prints experiment config json file and interconnect
from pathlib import Path
from .data.interconnect_data_loader import load_interconnects
from .data.experiment_config_loader import load_experiment_configs


def main():

    interconnects_file = Path(__file__).with_name("interconnects.json")
    experiment_options_file = Path(__file__).with_name("experiment_configs.json")

    # Load interconnects
    interconnects, bandwidth_report = load_interconnects(interconnects_file)

    # Load experiment configurations
    options, experiment_configs = load_experiment_configs(
        experiment_options_file
    )

    # Print interconnects
    print("\n=== Interconnects ===")
    for interconnect in interconnects:
        print(interconnect)

    print("\n=== Bandwidth Validation ===")
    for report in bandwidth_report:
        print(report)

    # Print experiment options
    print("\n=== Experiment Options ===")
    print(options)

    # Print generated experiment configurations
    print(f"\n=== Experiment Configurations ({len(experiment_configs)}) ===")
    for config in experiment_configs:
        print(config)


if __name__ == "__main__":
    main()