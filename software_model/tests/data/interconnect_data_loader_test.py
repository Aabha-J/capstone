
import copy
import json

from dataclasses import asdict

import pytest

from software_model.data.data_classes import Interconnect, InterconnectType
from software_model.data.interconnect_data_loader import load_interconnects


# ==================================================
# 1. Expected test objects
# ==================================================

EXPECTED_INTERCONNECTS = [
    Interconnect(
        interconnect_id="ELEC_001",
        interconnect_type=InterconnectType.ELECTRICAL,
        data_rate_per_lane=32.0,
        lane_width=16,
        bandwidth=512.0,
        energy_per_bit=0.5,
        phy_latency=2.0,
        propagation_delay=3.0,
        total_latency=5.0,
        reach=20.0,
        area=5.0,
        source="Electrical Paper"
    ),
    Interconnect(
        interconnect_id="OPT_001",
        interconnect_type=InterconnectType.OPTICAL,
        data_rate_per_lane=50.0,
        channel_count=4,
        wavelength_count=8,
        bandwidth=1600.0,
        energy_per_bit=0.3,
        phy_latency=2.0,
        propagation_delay=3.0,
        eo_conversion_latency=1.0,
        oe_conversion_latency=1.0,
        total_latency=7.0,
        reach=100.0,
        area=8.0,
        source="Optical Paper"
    )
]


# ==================================================
# 2. Helpers
# ==================================================

def interconnect_to_json(interconnect):
    """Convert an Interconnect object into JSON-compatible data."""

    data = asdict(interconnect)
    data["interconnect_type"] = interconnect.interconnect_type.value

    return data


def create_test_json(tmp_path, interconnect_data):
    """
    Write interconnect dictionaries to a temporary JSON file.

    interconnect_data is a list of JSON-compatible dictionaries.
    """

    file_path = tmp_path / "test_interconnects.json"

    json_data = {
        "interconnects": interconnect_data
    }

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(json_data, file, indent=4)

    return file_path


def load_test_data(tmp_path, interconnect_data):
    """Write temporary JSON and load it using the actual data loader."""

    file_path = create_test_json(tmp_path, interconnect_data)

    return load_interconnects(file_path)


def get_interconnect(interconnects, interconnect_id):
    return next(
        item for item in interconnects
        if item.interconnect_id == interconnect_id
    )


def get_entry(interconnect_data, interconnect_id):
    return next(
        item for item in interconnect_data
        if item["interconnect_id"] == interconnect_id
    )


def get_base_json_data():
    """Generate fresh JSON-compatible data from expected objects."""

    return [
        interconnect_to_json(interconnect)
        for interconnect in EXPECTED_INTERCONNECTS
    ]


# ==================================================
# 3. Clean JSON loading
# ==================================================

def test_load_clean_json(tmp_path):
    interconnect_data = get_base_json_data()

    interconnects, validation_report = load_test_data(
        tmp_path, interconnect_data
    )

    assert len(interconnects) == len(EXPECTED_INTERCONNECTS)

    # Verify every field of every loaded object.
    for actual, expected in zip(interconnects, EXPECTED_INTERCONNECTS):
        assert actual == expected

    # Verify both interconnect types were converted correctly.
    assert {
        interconnect.interconnect_type
        for interconnect in interconnects
    } == {
        InterconnectType.ELECTRICAL,
        InterconnectType.OPTICAL
    }


# ==================================================
# 4. Missing optional parameters
# ==================================================

def test_load_with_missing_optional_parameters(tmp_path):
    data = get_base_json_data()

    electrical = get_entry(data, "ELEC_001")
    optical = get_entry(data, "OPT_001")

    # Reported bandwidth exists, so calculation parameters
    # are not required.
    electrical.pop("data_rate_per_lane")
    electrical.pop("lane_width")

    # Reported total latency exists, so latency components
    # are not required.
    electrical.pop("phy_latency")
    electrical.pop("propagation_delay")

    # Reported optical total latency exists, so its components
    # are not required.
    optical.pop("phy_latency")
    optical.pop("propagation_delay")
    optical.pop("eo_conversion_latency")
    optical.pop("oe_conversion_latency")

    interconnects, _ = load_test_data(tmp_path, data)

    electrical = get_interconnect(interconnects, "ELEC_001")
    optical = get_interconnect(interconnects, "OPT_001")

    assert electrical.data_rate_per_lane is None
    assert electrical.lane_width is None
    assert electrical.phy_latency is None
    assert electrical.propagation_delay is None

    assert optical.phy_latency is None
    assert optical.propagation_delay is None
    assert optical.eo_conversion_latency is None
    assert optical.oe_conversion_latency is None

    # Reported values should still be retained.
    for actual, expected in zip(interconnects, EXPECTED_INTERCONNECTS):
        assert actual.bandwidth == expected.bandwidth
        assert actual.total_latency == expected.total_latency


# ==================================================
# 5. Bandwidth validation
# ==================================================
#parametrize the test to run for both optical and electrical interconnects
@pytest.mark.parametrize(
    "interconnect_id",
    ["OPT_001", "ELEC_001"]
)
def test_bandwidth_discrepancy(tmp_path, interconnect_id):
    data = get_base_json_data()

    entry = get_entry(data, interconnect_id)

    # Introduce a discrepancy.
    entry["bandwidth"] *= 0.5

    with pytest.raises(ValueError, match="BANDWIDTH DISCREPANCY"):
        load_test_data(tmp_path, data)


def test_bandwidth_missing_and_cannot_be_calculated(tmp_path):
    data = get_base_json_data()

    electrical = get_entry(data, "ELEC_001")

    electrical["bandwidth"] = None
    electrical["data_rate_per_lane"] = None
    electrical["lane_width"] = None

    with pytest.raises(ValueError, match="Missing bandwidth"):
        load_test_data(tmp_path, data)


@pytest.mark.parametrize(
    "interconnect_id",
    ["OPT_001", "ELEC_001"]
)
def test_bandwidth_calculated_when_not_reported(
    tmp_path, interconnect_id
):
    data = get_base_json_data()

    entry = get_entry(data, interconnect_id)
    expected_bandwidth = entry["bandwidth"]

    entry["bandwidth"] = None

    interconnects, _ = load_test_data(tmp_path, data)

    actual = get_interconnect(interconnects, interconnect_id)

    assert actual.bandwidth == pytest.approx(expected_bandwidth)


# ==================================================
# 6. Total latency validation
# ==================================================

@pytest.mark.parametrize(
    "interconnect_id",
    ["OPT_001", "ELEC_001"]
)
def test_latency_discrepancy(tmp_path, interconnect_id):
    data = get_base_json_data()

    entry = get_entry(data, interconnect_id)

    # Introduce a discrepancy.
    entry["total_latency"] *= 2

    with pytest.raises(ValueError, match="LATENCY DISCREPANCY"):
        load_test_data(tmp_path, data)


@pytest.mark.parametrize(
    "interconnect_id",
    ["OPT_001", "ELEC_001"]
)
def test_latency_calculated_when_not_reported(
    tmp_path, interconnect_id
):
    data = get_base_json_data()

    entry = get_entry(data, interconnect_id)
    expected_latency = entry["total_latency"]

    entry["total_latency"] = None

    interconnects, _ = load_test_data(tmp_path, data)

    actual = get_interconnect(interconnects, interconnect_id)

    assert actual.total_latency == pytest.approx(expected_latency)


def test_latency_remains_none_when_unavailable(tmp_path):
    data = get_base_json_data()

    electrical = get_entry(data, "ELEC_001")

    electrical["total_latency"] = None
    electrical["phy_latency"] = None
    electrical["propagation_delay"] = None

    interconnects, _ = load_test_data(tmp_path, data)

    actual = get_interconnect(interconnects, "ELEC_001")

    assert actual.total_latency is None


def test_reported_latency_used_when_components_missing(tmp_path):
    data = get_base_json_data()

    optical = get_entry(data, "OPT_001")

    optical["phy_latency"] = None
    optical["propagation_delay"] = None
    optical["eo_conversion_latency"] = None
    optical["oe_conversion_latency"] = None

    interconnects, _ = load_test_data(tmp_path, data)

    actual = get_interconnect(interconnects, "OPT_001")

    assert actual.total_latency == EXPECTED_INTERCONNECTS[1].total_latency


# ==================================================
# 7. Required fields and invalid parameters
# ==================================================

@pytest.mark.parametrize(
    "field",
    ["interconnect_id", "interconnect_type", "source"]
)
def test_missing_required_fields(tmp_path, field):
    data = get_base_json_data()

    del data[0][field]

    with pytest.raises((ValueError, TypeError)):
        load_test_data(tmp_path, data)


def test_invalid_interconnect_type(tmp_path):
    data = get_base_json_data()

    data[0]["interconnect_type"] = "wireless"

    with pytest.raises(ValueError, match="Invalid interconnect type"):
        load_test_data(tmp_path, data)


def test_unknown_parameter(tmp_path):
    data = get_base_json_data()

    data[0]["unknown_parameter"] = 123

    with pytest.raises(ValueError, match="Unknown parameters"):
        load_test_data(tmp_path, data)


# ==================================================
# 8. Duplicate identification
# ==================================================

def test_duplicate_interconnect_id(tmp_path):
    data = get_base_json_data()

    data[1]["interconnect_id"] = data[0]["interconnect_id"]

    with pytest.raises(ValueError, match="Duplicate interconnect ID"):
        load_test_data(tmp_path, data)


def test_duplicate_source(tmp_path):
    data = get_base_json_data()

    data[1]["source"] = data[0]["source"]

    with pytest.raises(ValueError, match="Duplicate source"):
        load_test_data(tmp_path, data)


# ==================================================
# 9. Technology-specific parameters
# ==================================================

@pytest.mark.parametrize(
    "conversion_parameter",
    ["eo_conversion_latency", "oe_conversion_latency"]
)
def test_electrical_cannot_have_conversion_latency(
    tmp_path, conversion_parameter
):
    data = get_base_json_data()

    data[0][conversion_parameter] = 1.0

    with pytest.raises(ValueError, match="must not have"):
        load_test_data(tmp_path, data)


# ==================================================
# 10. Invalid JSON structure
# ==================================================

@pytest.mark.parametrize(
    "invalid_data",
    [
        [],
        {"wrong_key": []},
        {"interconnects": {}},
    ]
)
def test_invalid_json_structure(tmp_path, invalid_data):
    file_path = tmp_path / "test_interconnects.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(invalid_data, file)

    with pytest.raises(ValueError):
        load_interconnects(file_path)


# ==================================================
# 11. Missing JSON file
# ==================================================

def test_missing_json_file(tmp_path):
    file_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        load_interconnects(file_path)
