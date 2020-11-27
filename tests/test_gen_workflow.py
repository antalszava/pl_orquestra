import pytest
import subprocess

import yaml
import pennylane_orquestra.gen_workflow as gw
from pennylane_orquestra.cli_actions import qe_submit

from conftest import (
    resources_default,
    backend_specs_default,
    qasm_circuit_default,
    operator_string_default,
    test_workflow,
)

# Auxiliary functions
def qe_list_workflow():
    """Function for a CLI call to list workflows.

    This CLI call needs the caller to be logged in to Orquestra. It is an
    inexpensive way of checking that the caller has been authenticated with the
    Orquestra platform.
    """
    process = subprocess.Popen(
        ["qe", "list", "workflow"], stdout=subprocess.PIPE, universal_newlines=True
    )
    return process.stdout.readlines()


class TestExpvalTemplate:
    """Test that workflow generation works as expected."""

    def test_can_yaml(self, tmpdir):
        """Test that filling in the workflow template for getting expectation
        values produces a valid yaml."""
        backend_component = "qe-forest"

        # Fill in workflow template
        workflow = gw.expval_template(
            backend_component, backend_specs_default, qasm_circuit_default, operator_string_default
        )

        file_name = tmpdir.join("test_workflow.yaml")

        with open(file_name, "w") as file:
            # Testing that no errors arise here
            d = yaml.dump(workflow, file)

    def test_unsupported_backend_component(self):
        """Test that if an unsupported backend component is input then an error is raised."""
        backend_component = "SomeNonExistentBackend"

        # Fill in workflow template
        with pytest.raises(ValueError, match="The specified backend component is not supported."):
            workflow = gw.expval_template(
                backend_component,
                backend_specs_default,
                qasm_circuit_default,
                operator_string_default,
            )

    def test_matches_template(self):
        """Test that generating a two-step workflow matches the pre-defined
        template."""
        backend_component = "qe-forest"

        # Fill in workflow template
        circuits = [qasm_circuit_default, qasm_circuit_default]
        workflow = gw.expval_template(
            backend_component, backend_specs_default, circuits, operator_string_default
        )

        file_name = "test_workflow.yaml"

        assert workflow['apiVersion'] == test_workflow['apiVersion']
        assert workflow['name'] == test_workflow['name']
        assert workflow['imports'] == test_workflow['imports']

        # Checking the first step
        assert workflow['steps'][0]['name'] == test_workflow['steps'][0]['name']
        assert workflow['steps'][0]['config'] == test_workflow['steps'][0]['config']

        # Checking the inputs
        assert workflow['steps'][0]['inputs'][0]['backend_specs'] == test_workflow['steps'][0]['inputs'][0]['backend_specs']
        assert workflow['steps'][0]['inputs'][3]['operators'] == test_workflow['steps'][0]['inputs'][3]['operators']
        assert workflow['steps'][0]['inputs'][4]['circuit'] == test_workflow['steps'][0]['inputs'][4]['circuit']
        assert workflow['steps'][0]['inputs'] == test_workflow['steps'][0]['inputs']

        # Checking the outputs
        assert workflow['steps'][0]['outputs'] == test_workflow['steps'][0]['outputs']
        assert workflow['types'] == test_workflow['types']

        # Checking the second step
        assert workflow['steps'][1]['name'] == test_workflow['steps'][1]['name']
        assert workflow['steps'][1]['config'] == test_workflow['steps'][1]['config']

        # Checking the inputs
        assert workflow['steps'][1]['inputs'][0]['backend_specs'] == test_workflow['steps'][1]['inputs'][0]['backend_specs']
        assert workflow['steps'][1]['inputs'][3]['operators'] == test_workflow['steps'][1]['inputs'][3]['operators']
        assert workflow['steps'][1]['inputs'][4]['circuit'] == test_workflow['steps'][1]['inputs'][4]['circuit']
        assert workflow['steps'][1]['inputs'] == test_workflow['steps'][1]['inputs']

        # Checking the outputs
        assert workflow['steps'][1]['outputs'] == test_workflow['steps'][1]['outputs']
        assert workflow['types'] == test_workflow['types']
        assert workflow == test_workflow
