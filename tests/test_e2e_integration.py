import pytest
import numpy as np
import math
import yaml
import os

import pennylane as qml
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice
import pennylane_orquestra.gen_workflow as gw
from pennylane_orquestra.cli_actions import qe_submit, workflow_details

from conftest import qe_list_workflow, backend_specs_default, operator_string_default, qasm_circuit_default

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator"}'
qiskit_sampler_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 1000}'


class TestWorkflowSubmissionIntegration:
    """Test that workflow generation works as expected."""

    @pytest.mark.parametrize("backend_component", list(gw.backend_import_db.keys()))
    def test_can_submit_and_query_workflow_details(self, backend_component, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values can be submitted to Orquestra and workflow details can be queried."""
        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        qasm_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; creg c[1];'
        op = ['["[Z0]"]']

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs_default, qasm_circuit_default, op)
        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

        # Submit a workflow
        workflow_id = qe_submit(file_name)

        workflow_msg = workflow_details(workflow_id)
        details_string = "".join(workflow_msg)
        assert workflow_id in details_string

    @pytest.mark.parametrize("backend_component", list(gw.backend_import_db.keys()))
    def test_submit_raises(self, backend_component, tmpdir):
        """Test that submitting a workflow to Orquestra with invalid
        requirements raises an error."""
        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        qasm_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; creg c[1];'

        # This will not be a valid operator: will raise error
        operator = []

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs_default, qasm_circuit, operator)
        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

        # Submit a workflow --- error due to the operator
        with pytest.raises(ValueError, match="Error"):
            workflow_id = qe_submit(file_name)


devices = [
        ('orquestra.forest', 'wavefunction-simulator', True),
        ('orquestra.forest', 'wavefunction-simulator', False),
        ('orquestra.qiskit', 'statevector_simulator', True),
        ('orquestra.qiskit', 'statevector_simulator', False),
        ('orquestra.qiskit', 'qasm_simulator', False),
]

class TestOrquestraIntegration:
    """Test the Orquestra integration with PennyLane.
    
    Note: these test cases connect to the Orquestra platform and running each
    of them might require 1-2 minutes.
    """

    @pytest.mark.parametrize("device_name,backend,analytic", devices)
    def test_apply_x(self, device_name, backend, analytic):
        """Test a simple circuit that applies PauliX on the first wire."""
        dev = qml.device(device_name, wires=3, backend_name=backend, analytic=analytic)

        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.PauliZ(0))

        assert circuit() == -1

    def test_compute_expval_including_identity(self):
        """Test a simple circuit that involves computing the expectation value of the
        Identity operator."""
        dev = qml.device('orquestra.qiskit', wires=3)

        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            qml.PauliX(1)
            qml.PauliX(2)
            return qml.expval(qml.Identity(0)), qml.expval(qml.PauliZ(1)), qml.expval(qml.Identity(2))

        assert np.allclose(circuit(), np.array([1, -1, 1]))


@pytest.fixture
def token():
    t = os.getenv("IBMQX_TOKEN_TEST", None)

    if t is None:
        pytest.skip("Skipping test, no IBMQ token available")

    yield t
    IBMQ.disable_account()

class TestOrquestraIBMQIntegration:
    def test_apply_x(self, token):
        """Test a simple circuit that applies PauliX on the first wire."""
        dev = qml.device('orquestra.ibmq', wires=3, token=token)

        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.PauliZ(0))

        assert math.isclose(circuit(), -1, abs_tol=10e-5)
