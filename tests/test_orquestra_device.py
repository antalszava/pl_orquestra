import pytest

import pennylane as qml
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator"}'
qiskit_sampler_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 1000}'

class TestDevice:

    def test_error_if_not_expval(self):
        dev = qml.device('orquestra.qiskit', wires=2)

        @qml.qnode(dev)
        def circuit():
            return qml.var(qml.PauliZ(0))

        with pytest.raises(NotImplementedError):
            circuit()

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_create_backend_specs_analytic(self, backend):
        dev = backend(wires=1, shots=1000, analytic=True)
        assert dev.create_backend_specs() == qiskit_analytic_specs

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_create_backend_specs(self, backend):
        dev = backend(wires=1, shots=1000, analytic=False)
        assert dev.create_backend_specs() == qiskit_sampler_specs
