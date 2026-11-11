
import json
import pytest

from software_model.data.data_classes import (
    Topology,
    TrafficPattern,
)
from software_model.data.experiment_config_loader import (
    expand_values,
    create_experiment_options,
    generate_experiment_configs,
    load_experiment_configs,
)


def get_base_experiment_data():
    """Return a minimal valid experiment options dictionary."""

    return {
        "chiplet_counts": [2],
        "topologies": ["Mesh"],
        "link_distances": [10],

        "traffic_patterns": ["uniform", "hotspot"],
        "packet_sizes": [64],
        "injection_rates": [0.1],

        "hotspot_counts": [1, 2],
        "hotspot_probabilities": [0.1, 0.2],

        "durations": [10000],
        "seeds": [1],
    }


def test_expand_array():
    """Array input should be returned as a list."""

    result = expand_values([1, 2, 4], "chiplet_counts", int)

    assert result == [1, 2, 4]


def test_expand_integer_range():
    """Integer ranges should include the stop value when reachable."""

    result = expand_values(
        {"start": 1, "stop": 5, "step": 2},
        "chiplet_counts",
        int,
    )

    assert result == [1, 3, 5]


def test_expand_float_range():
    """Float ranges should not accumulate floating-point errors."""

    result = expand_values(
        {"start": 0.1, "stop": 0.3, "step": 0.1},
        "injection_rates",
        float,
    )

    assert result == pytest.approx([0.1, 0.2, 0.3])


def test_expand_invalid_range():
    """A range with a zero step should raise an error."""

    with pytest.raises(ValueError, match="step must be positive"):
        expand_values(
            {"start": 1, "stop": 5, "step": 0},
            "chiplet_counts",
            int,
        )


def test_expand_empty_array():
    """Empty option arrays should be rejected."""

    with pytest.raises(ValueError, match="cannot be empty"):
        expand_values([], "chiplet_counts", int)


def test_create_experiment_options():
    """Valid input should create an ExperimentOptions object."""

    options = create_experiment_options(get_base_experiment_data())

    assert options.chiplet_counts == [2]
    assert options.topologies == [Topology.MESH]
    assert options.traffic_patterns == [
        TrafficPattern.UNIFORM,
        TrafficPattern.HOTSPOT,
    ]


def test_invalid_topology():
    """Only Mesh, Ring, and Direct should be accepted."""

    data = get_base_experiment_data()
    data["topologies"] = ["Star"]

    with pytest.raises(ValueError, match="Invalid topologies"):
        create_experiment_options(data)


def test_invalid_traffic_pattern():
    """Only uniform, random, and hotspot should be accepted."""

    data = get_base_experiment_data()
    data["traffic_patterns"] = ["transpose"]

    with pytest.raises(ValueError, match="Invalid traffic_patterns"):
        create_experiment_options(data)


def test_invalid_injection_rate():
    """Injection rates must be between 0 and 1."""

    data = get_base_experiment_data()
    data["injection_rates"] = [1.5]

    with pytest.raises(ValueError, match="Injection rates"):
        create_experiment_options(data)


def test_duplicate_option_values():
    """Duplicate values should not generate duplicate experiments."""

    data = get_base_experiment_data()
    data["chiplet_counts"] = [2, 2]

    with pytest.raises(ValueError, match="duplicate values"):
        create_experiment_options(data)


def test_generate_experiment_configs():
    """Generate combinations, varying hotspot settings only for hotspot traffic."""

    options = create_experiment_options(get_base_experiment_data())

    configs = generate_experiment_configs(options)

    # Uniform: 1 configuration.
    # Hotspot: 2 counts * 2 probabilities = 4 configurations.
    assert len(configs) == 5

    uniform_configs = [
        config for config in configs
        if config.traffic_pattern == TrafficPattern.UNIFORM
    ]

    hotspot_configs = [
        config for config in configs
        if config.traffic_pattern == TrafficPattern.HOTSPOT
    ]

    assert len(uniform_configs) == 1
    assert len(hotspot_configs) == 4

    # Hotspot parameters should not apply to uniform traffic.
    assert uniform_configs[0].hotspot_count is None
    assert uniform_configs[0].hotspot_probability is None

    # Hotspot configurations should contain both parameters.
    for config in hotspot_configs:
        assert config.hotspot_count is not None
        assert config.hotspot_probability is not None


def test_unique_config_ids():
    """Every generated configuration should have a unique ID."""

    options = create_experiment_options(get_base_experiment_data())
    configs = generate_experiment_configs(options)

    config_ids = [config.config_id for config in configs]

    assert len(config_ids) == len(set(config_ids))


def test_load_experiment_configs(tmp_path):
    """Load options from JSON and generate configurations."""

    data = {
        "experiment_options": get_base_experiment_data()
    }

    file_path = tmp_path / "experiment_config.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file)

    options, configs = load_experiment_configs(file_path)

    assert options.chiplet_counts == [2]
    assert len(configs) == 5


def test_missing_experiment_options(tmp_path):
    """Missing experiment_options should raise an error."""

    file_path = tmp_path / "experiment_config.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump({}, file)

    with pytest.raises(ValueError, match="Missing 'experiment_options'"):
        load_experiment_configs(file_path)