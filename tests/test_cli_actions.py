"""
Unit tests for the ```cli_actions`` module, without sending any requests to
Orquestra.
"""
import pytest
import subprocess
import os

import yaml
import pennylane_orquestra.gen_workflow as gw
import pennylane_orquestra
from pennylane_orquestra.cli_actions import qe_submit, write_workflow_file, loop_until_finished

from conftest import backend_specs_default, qasm_circuit_default, operator_string_default, MockPopen


class TestCLIFunctions:
    """Test functions for CLI actions work as expected."""

    def test_submit_raises_no_success(self, monkeypatch):
        """Test that the qe_submit method raises an error if not a successful
        message was received."""

        no_success_msg = "Not a success message."
        with monkeypatch.context() as m:
            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen(no_success_msg))

            with pytest.raises(ValueError, match=no_success_msg):
                workflow_id = qe_submit("some_filename")

    @pytest.mark.parametrize("response", [["Test Success"], "Test Success"])
    def test_submit_raises_unexpected_resp(self, monkeypatch, response):
        """Test that the qe_submit method raises an error if the workflow id
        could not be obtained."""

        unexp_resp_msg = "Received an unexpected response after submitting workflow."
        with monkeypatch.context() as m:
            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen(response))
            m.setattr(os, "remove", lambda *args, **kwargs: None)

            with pytest.raises(ValueError, match=unexp_resp_msg):
                workflow_id = qe_submit("some_filename")

    def test_write_workflow_file(self, tmpdir, monkeypatch):
        """Test that filling in the workflow template for getting expectation
        values produces a valid yaml."""
        backend_component = "qe-forest"

        # Fill in workflow template
        workflow = gw.gen_expval_workflow(
            backend_component, backend_specs_default, qasm_circuit_default, operator_string_default
        )

        file_name = "test_workflow.yaml"
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)
            write_workflow_file(file_name, workflow)

        with open(tmpdir.join(file_name)) as file:
            loaded_yaml = yaml.load(file, Loader=yaml.FullLoader)

        assert workflow == loaded_yaml

    @pytest.mark.parametrize("res_msg", ["Some message2", "First line\n Second "])
    def test_loop_until_finished_raises(self, res_msg, monkeypatch):
        """Check that certain errors are raised and handled correctly by the
        loop_until_finished function."""
        with monkeypatch.context() as m:
            m.setattr(
                pennylane_orquestra.cli_actions, "workflow_details", lambda *args: "Some message1"
            )
            m.setattr(
                pennylane_orquestra.cli_actions, "workflow_results", lambda *args: res_msg
            )

            # Check that indexing into the message raises an IndexError
            # (this shows that it will be handled internally)
            with pytest.raises(IndexError, match="list index out of range"):
                location = res_msg[1].split()[1]

            # Check that looping eventually times out
            with pytest.raises(TimeoutError, match="were not obtained after"):
                loop_until_finished("Some ID", timeout=1)

    def test_loop_raises_workflow_fail(self, monkeypatch):
        """Check that an error is raised if the workflow exeuction failed."""
        with monkeypatch.context() as m:
            status = "Status:              Failed\n"
            result_message = "Some message2"

            m.setattr(pennylane_orquestra.cli_actions, "workflow_details", lambda *args: status)
            m.setattr(
                pennylane_orquestra.cli_actions,
                "workflow_results",
                lambda *args: result_message,
            )

            # Check that looping raises an error if the workflow details
            # contain a failed status
            with pytest.raises(
                ValueError, match=f"Something went wrong with executing the workflow. {status}"
            ):
                loop_until_finished("Some ID", timeout=1)
