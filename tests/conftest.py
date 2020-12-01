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
test_batch_res0 = 0.777506938122745
test_batch_res1 = 13.321
test_batch_res2 = 1.234 

# A result dictionary for 3 steps as a result of batched execution
# The step names are not sorted ("class" entry in each nested dictionary): the
# order of results differs from the way they were assumed to be submitted
test_batch_dict = {
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
            "stepName": "run-circuit-and-get-expval-2",
            "taskClass": "run-circuit-and-get-expval-2",
            "taskId": "expval",
            "workflowId": "expval",
        },
        "id": "expval",
        "workflowId": "expval",
    },
    "expval-id000": {
        "class": "run-circuit-and-get-expval-0",
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
            "stepName": "run-circuit-and-get-expval-1",
            "taskClass": "run-circuit-and-get-expval-1",
            "taskId": "expval",
            "workflowId": "expval",
        },
        "id": "expval",
        "workflowId": "expval",
    },
}