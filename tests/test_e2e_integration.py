import pytest
import numpy as np

import pennylane as qml
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice
import pennylane_orquestra.gen_workflow as gw
from pennylane_orquestra.cli_actions import qe_submit

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator"}'
qiskit_sampler_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 1000}'


class TestWorkflowSubmissionIntegration:
    """Test that workflow generation works as expected."""

    @pytest.mark.skip(reason="TODO: remove testing submission")
    @pytest.mark.parametrize("backend_component", list(gw.backend_import_db.keys()))
    def test_can_submit(self, backend_component, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values can be submitted to Orquestra."""
        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        qasm_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; creg c[1];'

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs, qasm_circuit, operator_string)
        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

        # Submit a workflow
        response = qe_submit(file_name)
        assert 'Successfully submitted workflow to quantum engine!\n' in response

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

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.PauliZ(0))

        assert circuit() == -1