"""
This module contains tests locally checking that the functionality of the
expval step is correct. Running the test cases requires the related packages to
be installed locally.
"""
import math
import os

import pytest
from qiskit import IBMQ

import expval
from qeqiskit.noise import get_qiskit_noise_model

exact_devices = [
    '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator"}',
    '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "statevector_simulator"}',
    '{"module_name": "qequlacs.simulator", "function_name": "QulacsSimulator"}',
]

sampling_devices = [
    '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 10000}',
    '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 10000}',
    '{"module_name": "qequlacs.simulator", "function_name": "QulacsSimulator", "n_samples": 10000}',
]

analytic_tol = 10e-10

# The tolerance for sampling is expected to be higher
tol = 10e-2


@pytest.mark.parametrize("backend_specs", exact_devices)
class TestExpvalExact:
    """Tests getting the expecation value of circuits on devices that support
    exact computations."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_only_measure_circuit(self, op, backend_specs, monkeypatch):
        """Tests that the correct result in obtained for a circuit that only
        contains measurements."""
        lst = []

        only_measure_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, only_measure_qasm, op)
        assert lst[0][0] == 1

    def test_run_circuit_and_get_expval_hadamard(self, backend_specs, monkeypatch):
        """Tests that the correct result in obtained for a circuit that
        contains a Hadamard gate."""
        lst = []

        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        op = '["[Z0]"]'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, op)
        assert math.isclose(lst[0][0], 0.0, abs_tol=analytic_tol)


@pytest.mark.parametrize("backend_specs", sampling_devices)
class TestExpvalSampling:
    """Tests getting the expecation value of circuits on sampling devices."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_only_measure_circuit(self, backend_specs, op, monkeypatch):
        """Tests that the correct result in obtained for a circuit that only
        contains measurements."""
        lst = []

        simple_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val[0]))

        expval.run_circuit_and_get_expval(backend_specs, simple_qasm, op)
        assert lst[0] == 1.0

    def test_run_circuit_and_get_expval_hadamard(self, backend_specs, monkeypatch):
        """Tests that the correct result in obtained for a circuit that
        contains a Hadamard gate."""
        lst = []

        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        op = '["[Z0]"]'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, op)
        assert math.isclose(lst[0][0], 0.0, abs_tol=tol)


@pytest.fixture
def token():
    """Get the IBMQX test token."""
    t = os.getenv("IBMQX_TOKEN_TEST", None)

    if t is None:
        pytest.skip("Skipping test, no IBMQ token available")

    yield t
    IBMQ.disable_account()


class TestIBMQ:
    """Test the IBMQ device."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_run_circuit_and_get_expval_simple_ibmq(self, token, op, monkeypatch):
        """Test running an empty circuit."""
        lst = []

        IBMQ.enable_account(token)
        backend_specs = '{"module_name": "qeqiskit.backend", "function_name": "QiskitBackend", "device_name": "ibmq_qasm_simulator", "n_samples": 8192}'

        simple_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, simple_qasm, op)
        assert math.isclose(lst[0][0], 1.0, abs_tol=tol)

class TestNoiseModel:

    def test_run_circuit_and_get_expval_hadamard_noise(self, monkeypatch, token):
        """Tests that the correct result in obtained for a circuit that
        contains a Hadamard gate and is run on a noisy device."""
        lst = []

        backend_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 10000}'
        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        op = '["[Z0]"]'

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))
        monkeypatch.setattr(expval, "load_noise_model", lambda arg: arg)
        monkeypatch.setattr(expval, "load_circuit_connectivity", lambda arg: arg)

        noise_model, connectivity = get_qiskit_noise_model("ibmqx2", api_token=token)
        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, op, noise_model=noise_model, device_connectivity=connectivity)
        assert math.isclose(lst[0][0], 0.0, abs_tol=tol)
