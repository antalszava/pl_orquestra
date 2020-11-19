import yaml
import gen_workflow as gw
from cli_actions import qe_submit

backend_component = 'qe-forest'
resources = {'cpu': '1000m', 'memory': '1Gi', 'disk': '10Gi'}

backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator", "n_samples": 100}'
qasm_circuit = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0];'
operator_string = '[Z0]'

class TestWorkflowGeneration:

    def test_expval_template_can_yaml(self, tmpdir):
        workflow = gw.expval_template(backend_component, backend_specs, qasm_circuit, operator_string)

        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

    def test_can_submit(self, tmpdir):
        workflow = gw.expval_template(backend_component, backend_specs, qasm_circuit, operator_string)

        file_name = tmpdir.join('test_workflow.yaml')

        with open(file_name, 'w') as file:
            d = yaml.dump(workflow, file)

        # 1. Submit a workflow
        response = qe_submit(file_name)
        assert 'Successfully submitted workflow to quantum engine!\n' in response
