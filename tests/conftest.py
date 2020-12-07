"""
Data and auxiliary functions used for testing the PennyLane-Orquestra plugin.
"""
import subprocess
from copy import deepcopy

# Auxiliary classes and functions
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


class MockPopen:
    """A mock class that allows to mock the self.stdout.readlines() call."""

    def __init__(self, msg=None):
        class MockStdOut:
            def __init__(self, msg):
                self.msg = msg

            def readlines(self, *args):
                if self.msg is None:
                    self.msg = ["Successfully submitted workflow to quantum engine!\n", "SomeWorkflow ID"]
                return self.msg

        self.stdout = MockStdOut(msg)


# Auxiliary data

# Default data that are inserted into a workflow template
resources_default = {"cpu": "1000m", "memory": "1Gi", "disk": "10Gi"}
backend_specs_default = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 100}'
qasm_circuit_default = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0];'
operator_string_default = [["[Z0]"], ["[Z0 X1 Y2]"]]

# Test workflow

# 1. step
first_name = "run-circuit-and-get-expval-0"
first_config = {
    "runtime": {
        "language": "python3",
        "imports": ["pl_orquestra", "z-quantum-core", "qe-openfermion", "qe-forest"],
        "parameters": {
            "file": "pl_orquestra/steps/expval.py",
            "function": "run_circuit_and_get_expval",
        },
    }
}

first_out = [{"name": "expval", "type": "expval", "path": "/app/expval.json"}]
first_backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 100}'
first_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0];'
first_ops = ["[Z0]"]
first_in = [
    {"backend_specs": first_backend_specs, "type": "string"},
    {"noise_model": "None", "type": "noise-model"},
    {"device_connectivity": "None", "type": "device-connectivity"},
    {"operators": first_ops, "type": "string"},
    {"circuit": first_circuit, "type": "string"},
]

first_step = {"name": first_name, "config": first_config, "outputs": first_out, "inputs": first_in}

# 2. step
second_name = "run-circuit-and-get-expval-1"
second_config = {
    "runtime": {
        "language": "python3",
        "imports": ["pl_orquestra", "z-quantum-core", "qe-openfermion", "qe-forest"],
        "parameters": {
            "file": "pl_orquestra/steps/expval.py",
            "function": "run_circuit_and_get_expval",
        },
    }
}

second_out = [{"name": "expval", "type": "expval", "path": "/app/expval.json"}]
second_backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 100}'
second_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0];'
second_ops = ["[Z0 X1 Y2]"]
second_in = [
    {"backend_specs": second_backend_specs, "type": "string"},
    {"noise_model": "None", "type": "noise-model"},
    {"device_connectivity": "None", "type": "device-connectivity"},
    {"operators": second_ops, "type": "string"},
    {"circuit": second_circuit, "type": "string"},
]

second_step = {
    "name": second_name,
    "config": second_config,
    "outputs": second_out,
    "inputs": second_in,
}

steps = [first_step, second_step]

types = ["circuit", "expval", "noise-model", "device-connectivity"]

pl_orquestra_import = {
    "name": "pl_orquestra",
    "type": "git",
    "parameters": {"repository": "git@github.com:antalszava/pl_orquestra.git", "branch": "master"},
}

imports_workflow = [
    pl_orquestra_import,
    {
        "name": "z-quantum-core",
        "type": "git",
        "parameters": {
            "repository": "git@github.com:zapatacomputing/z-quantum-core.git",
            "branch": "dev",
        },
    },
    {
        "name": "qe-openfermion",
        "type": "git",
        "parameters": {
            "repository": "git@github.com:zapatacomputing/qe-openfermion.git",
            "branch": "dev",
        },
    },
    {
        "name": "qe-forest",
        "type": "git",
        "parameters": {
            "repository": "git@github.com:zapatacomputing/qe-forest.git",
            "branch": "dev",
        },
    },
]

test_workflow = {
    "apiVersion": "io.orquestra.workflow/1.0.0",
    "name": "expval",
    "imports": imports_workflow,
    "steps": steps,
    "types": types,
}

test_workflow_resources = deepcopy(test_workflow)
test_workflow_resources["steps"][0]["config"]["resources"] = resources_default
test_workflow_resources["steps"][1]["config"]["resources"] = resources_default

# Test workflow result for 3 steps

test_batch_res0 = 0.777506938122745
test_batch_res1 = 13.321
test_batch_res2 = 1.234

step_name0 = "run-circuit-and-get-expval-0"
step_name1 = "run-circuit-and-get-expval-1"
step_name2 = "run-circuit-and-get-expval-2"

# The step names are not in order ("class" entry in each nested dictionary): the
# order of results differs from the way they were assumed to be submitted
test_batch_result = {
    "expval-id2312": {
        "class": "run-circuit-and-get-expval-2",
        "expval": {
            "id": "expval-id/expval",
            "list": [
                {
                    "id": "expval-id",
                    "list": test_batch_res2,
                    "parentId": "expval-id",
                    "parentType": "test",
                    "workflowId": "expval-id",
                    "test": 0,
                }
            ],
            "schema": "test",
            "stepId": "expval",
            "stepName": step_name2,
            "taskClass": "run-circuit-and-get-expval-2",
            "taskId": "expval",
            "workflowId": "expval",
        },
        "id": "expval",
        "workflowId": "expval",
    },
    "expval-id000": {
        "class": step_name0,
        "expval": {
            "id": "expval-id/expval",
            "list": [
                {
                    "id": "expval-id",
                    "list": test_batch_res0,
                    "parentId": "expval-id",
                    "parentType": "test",
                    "workflowId": "expval-id",
                    "test": 0,
                }
            ],
            "schema": "test",
            "stepId": "expval",
            "stepName": "run-circuit-and-get-expval-0",
            "taskClass": "run-circuit-and-get-expval-0",
            "taskId": "expval",
            "workflowId": "expval",
        },
        "id": "expval",
        "workflowId": "expval",
    },
    "expval-id111": {
        "class": "run-circuit-and-get-expval-1",
        "expval": {
            "id": "expval-id/expval",
            "list": [
                {
                    "id": "expval-id",
                    "list": test_batch_res1,
                    "parentId": "expval-id",
                    "parentType": "test",
                    "workflowId": "expval-id",
                    "test": 0,
                }
            ],
            "schema": "test",
            "stepId": "expval",
            "stepName": step_name1,
            "taskClass": "run-circuit-and-get-expval-1",
            "taskId": "expval",
            "workflowId": "expval",
        },
        "id": "expval",
        "workflowId": "expval",
    },
}
