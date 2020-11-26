import pytest
import subprocess

import yaml
import pennylane_orquestra.gen_workflow as gw
from pennylane_orquestra.cli_actions import qe_submit

from conftest import resources_default, backend_specs_default, qasm_circuit_default, operator_string_default

# Auxiliary functions
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

class TestExpvalTemplate:
    """Test that workflow generation works as expected."""

    def test_can_yaml(self, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values produces a valid yaml."""
        backend_component = 'qe-forest'

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs_default,
                qasm_circuit_default, operator_string_default)

        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            # Testing that no errors arise here
            d = yaml.dump(workflow, file)

    def test_unsupported_backend_component(self):
        """Test that if an unsupported backend component is input then an error is raised."""
        backend_component = 'SomeNonExistentBackend'

        # Fill in workflow template
        with pytest.raises(ValueError, match="The specified backend component is not supported."):
            workflow = gw.expval_template(backend_component,
                    backend_specs_default, qasm_circuit_default,
                    operator_string_default)
