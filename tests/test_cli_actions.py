import pytest
import subprocess

import yaml
import pennylane_orquestra.gen_workflow as gw
import pennylane_orquestra
from pennylane_orquestra.cli_actions import qe_submit, write_workflow_file

from conftest import backend_specs_default, qasm_circuit_default, operator_string_default

class TestCLIFunctions:
    """Test that workflow generation works as expected."""

    def test_write_workflow_file(self, tmpdir, monkeypatch):
        """Test that filling in the workflow template for getting expectation
        values produces a valid yaml."""
        backend_component = 'qe-forest'

        # Fill in workflow template
        workflow = gw.expval_template(backend_component, backend_specs_default,
                qasm_circuit_default, operator_string_default)

        file_name = 'test_workflow.yaml'
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)
            write_workflow_file(file_name, workflow)

        with open(tmpdir.join(file_name)) as file:
            loaded_yaml = yaml.load(file, Loader=yaml.FullLoader)

        assert workflow == loaded_yaml
