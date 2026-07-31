"""Phase 1 smoke test: prove the plug-and-play input layer sees whatever
controller is plugged in. Skips (doesn't fail) when no device is attached,
since CI runners have no controllers -- this is meant to be run locally.
"""

import pytest

from control.input_adapter import list_devices


def test_list_devices_does_not_crash():
    devices = list_devices()
    assert isinstance(devices, list)


def test_at_least_one_controller_when_run_locally():
    devices = list_devices()
    if not devices:
        pytest.skip("No controller/wheel connected -- plug one in to exercise this check.")
    assert all(isinstance(name, str) and name for name in devices)
