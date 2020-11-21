import pytest

import pennylane as qml
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice

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

    @pytest.mark.parametrize("backend", [QeIBMQDevice])
    def test_serialize_circuit_rotations(self, backend):
        """Test that a circuit that is serialized correctly with rotations for
        a remote hardware backend"""
        dev = backend(wires=1, shots=1000, analytic=False)

        def circuit():
            qml.Hadamard(wires=[0])
            return qml.expval(qml.Hadamard(0))

        qnode = qml.QNode(circuit, dev)
        qnode._construct([], {})

        qasm = dev.serialize_circuit(qnode.circuit)
        expected = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nh q[0];\nry(-0.7853981633974483) q[0];\n'
        assert qasm == expected

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_serialize_circuit_no_rotations(self, backend):
        """Test that a circuit that is serialized correctly without rotations for
        a simulator backend"""
        dev = backend(wires=1, shots=1000, analytic=False)

        def circuit():
            qml.Hadamard(wires=[0])
            return qml.expval(qml.Hadamard(0))

        qnode = qml.QNode(circuit, dev)
        qnode._construct([], {})

        qasm = dev.serialize_circuit(qnode.circuit)
        expected = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nh q[0];\n'
        assert qasm == expected
