import pytest
import subprocess

import yaml
import gen_workflow as gw
from cli_actions import qe_submit

# Data that are inserted into a workflow template
backend_component = 'qe-forest'
resources = {'cpu': '1000m', 'memory': '1Gi', 'disk': '10Gi'}
backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 100}'
qasm_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0];'
operator_string = '[Z0]'

def qe_list_workflow():
    """Function for a CLI call to list workflows.

    This CLI call needs the caller to be logged in to Orquestra. It is an
    inexpensive way of checking that the caller has been authenticated with the
    Orquestra platform.
    """
    process = subprocess.Popen(['qe', 'list', 'workflow'],
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    return process.stdout.readlines()

class TestWorkflowGeneration:
    """Test that workflow generation works as expected."""

    def test_expval_template_can_yaml(self, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values produces a valid yaml."""

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs, qasm_circuit, operator_string)

        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            # Testing that no errors arise here
            d = yaml.dump(workflow, file)

    def test_can_submit(self, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values can be submitted to Orquestra."""
        # Skip if has not been authenticated with Orquestra
        try_resp = qe_list_workflow()
        need_login_msg = 'token has expired, please log in again\n'

        if need_login_msg in try_resp:
            pytest.skip("Has not logged in to the Orquestra platform.")

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs, qasm_circuit, operator_string)
        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

        # Submit a workflow
        response = qe_submit(file_name)
        assert 'Successfully submitted workflow to quantum engine!\n' in response
