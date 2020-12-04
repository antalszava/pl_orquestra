"""
This module contains tests locally checking that the functionality of the
expval step is correct. Running the test cases requires the related packages to
be installed locally.
"""
import pytest
import numpy as np
import expval

from qiskit import QiskitError, IBMQ
from qiskit.providers.ibmq.exceptions import IBMQProviderError

import qeforest
import json
import os
import math

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

tol = 10e-2


@pytest.mark.parametrize("backend_specs", exact_devices)
class TestExpvalExact:
    """Tests getting the expecation value of circuits on devices that support
    exact computations."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_only_measure_circuit(self, op, backend_specs, monkeypatch, tmpdir):
        """Tests that the correct result in obtained for a circuit that only
        contains measurements."""
        local_list = []

        only_measure_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        lst = []

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, only_measure_qasm, op)
        assert lst[0][0] == 1

    def test_run_circuit_and_get_expval_hadamard(self, backend_specs, monkeypatch, tmpdir):
        """Tests that the correct result in obtained for a circuit that
        contains a Hadamard gate."""
        local_list = []

        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        op = '["[Z0]"]'

        lst = []

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, op)
        assert math.isclose(lst[0][0], 0.0, abs_tol=tol)


@pytest.mark.parametrize("backend_specs", sampling_devices)
class TestExpvalSampling:
    """Tests getting the expecation value of circuits on sampling devices."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_only_measure_circuit(self, backend_specs, op, monkeypatch):
        """Tests that the correct result in obtained for a circuit that only
        contains measurements."""
        local_list = []

        simple_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        lst = []

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val[0]))

        expval.run_circuit_and_get_expval(backend_specs, simple_qasm, op)
        assert lst[0] == 1.0

    def test_run_circuit_and_get_expval_hadamard(self, backend_specs, monkeypatch, tmpdir):
        """Tests that the correct result in obtained for a circuit that
        contains a Hadamard gate."""
        local_list = []

        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        op = '["[Z0]"]'

        lst = []

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, op)
        assert math.isclose(lst[0][0], 0.0, abs_tol=tol)


@pytest.fixture
def token():
    t = os.getenv("IBMQX_TOKEN_TEST", None)

    if t is None:
        pytest.skip("Skipping test, no IBMQ token available")

    yield t
    IBMQ.disable_account()


class TestIBMQ:
    """Test the IBMQ device."""

    @pytest.mark.parametrize("op", ['["[Z0]"]', '["[Z1]"]', '["[Z2]"]', '["[]"]'])
    def test_run_circuit_and_get_expval_simple_ibmq(self, token, op, monkeypatch, tmpdir):
        """Test running an empty circuit."""
        local_list = []

        IBMQ.enable_account(token)
        backend_specs = '{"module_name": "qeqiskit.backend", "function_name": "QiskitBackend", "device_name": "ibmq_qasm_simulator", "n_samples": 8192}'

        simple_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[3];\ncreg c[3];\n'

        lst = []

        monkeypatch.setattr(expval, "save_list", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, simple_qasm, op)
        assert math.isclose(lst[0][0], 1.0, abs_tol=tol)
