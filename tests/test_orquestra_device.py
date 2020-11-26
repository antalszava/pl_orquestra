import pytest
import subprocess
import os
import numpy as np

import pennylane as qml
import pennylane_orquestra
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator"}'
qiskit_sampler_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "qasm_simulator", "n_samples": 1000}'


class MockPopen:
    """A mock class that allows to mock the self.stdout.readlines() call."""
    def __init__(self):
        class MockStdOut: 
            def readlines(*args):
                return 'Successfully submitted workflow to quantum engine!\n'
    
        self.stdout = MockStdOut()


class TestBaseDevice:
    """Test the Orquestra base device"""

    def test_error_if_not_expval(self):
        """Test that an error is raised if not an expectation value is computed"""
        dev = qml.device('orquestra.qiskit', wires=2)

        @qml.qnode(dev)
        def circuit():
            return qml.var(qml.PauliZ(0))

        with pytest.raises(NotImplementedError):
            circuit()

    def test_qasm_simulator_analytic_warning(self):
        """Test that a warning is raised when using the QeQiskitDevice with the
        qasm_simulator backend in analytic mode and that we'll switch to
        sampling mode."""

        with pytest.warns(Warning, match="The qasm_simulator backend device cannot be used in "
                    "analytic mode. Results are based on sampling."):
            dev = qml.device('orquestra.qiskit', backend_device='qasm_simulator', wires=2, analytic=True)

        assert not dev.analytic

    @pytest.mark.parametrize("keep", [True, False])
    def test_keep_workflow_file(self, keep, tmpdir, monkeypatch):

        file_name = 'test_workflow.yaml'
        dev = qml.device('orquestra.forest', wires=3, keep_workflow_files=keep)
        mock_res_dict = {'First': {'expval': {'value': 123456789}}}

        assert not os.path.exists(tmpdir.join("expval.yaml"))
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    mock_res_dict)

            @qml.qnode(dev)
            def circuit():
                qml.PauliX(0)
                return qml.expval(qml.PauliZ(0))

            assert circuit() == 123456789
            file_kept = os.path.exists(tmpdir.join("expval.yaml"))
            assert file_kept if keep else not file_kept

class TestCreateBackendSpecs:
    """Test the create_backend_specs function"""

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_create_backend_specs_analytic(self, backend):
        """Test that the backend specs are created well for an analytic device"""
        dev = backend(wires=1, shots=1000, analytic=True)
        assert dev.create_backend_specs() == qiskit_analytic_specs

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_create_backend_specs_sampling(self, backend):
        """Test that the backend specs are created well for a sampling device"""
        dev = backend(wires=1, shots=1000, analytic=False)
        assert dev.create_backend_specs() == qiskit_sampler_specs

class TestSerializeCircuit:
    """Test the serialize_circuit function"""

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

mx = np.diag(np.array([1,2,3,4]))

obs_serialize= [
    # Don't decomposition
    (qml.Identity(wires=[0]), '1 []'),
    (qml.PauliX(wires=[0]), '1 [X0]'),
    (qml.PauliY(wires=[0]), '1 [Y0]'),
    (qml.PauliZ(wires=[0]), '1 [Z0]'),

    # Need decomposition
    (qml.Hadamard(wires=[0]), '0.7071067811865475 [X0] + 0.7071067811865475 [Z0]'),
    (qml.Hermitian(mx, wires=[0, 1]), "2.5 [] + -0.5 [Z1] + -1.0 [Z0]"),
    (qml.Identity(wires=[0]) @ qml.Identity(wires=[1]), '1 []'),
    (qml.PauliX(wires=[0]) @ qml.Identity(wires=[1]), '1 [X0]'),
    (qml.PauliY(wires=[0]) @ qml.Identity(wires=[1]), '1 [Y0]'),
    (qml.PauliZ(wires=[0]) @ qml.Identity(wires=[1]), '1 [Z0]'),
    (qml.Hermitian(mx, wires=[0, 1]) @ qml.Identity(wires=[2]), "2.5 [] + -0.5 [Z1] + -1.0 [Z0]"),

    # Custom wires
    (qml.PauliZ(wires=['w']), '1 [Z0]'),
    (qml.Hermitian(mx, wires=['a', 'b']) @ qml.Identity(wires=['c']), "2.5 [] + -0.5 [Z1] + -1.0 [Z0]"),
]


class TestSerializeOperator:
    """Test the serialize_operator function"""

    @pytest.mark.parametrize("wires, expected", [([2], '[Z2]'), ([0, 2], '[Z0 Z2]'), ([0, 1, 2], '[Z0 Z1 Z2]')])
    def test_pauliz_operator_string(self, wires, expected):
        dev = QeIBMQDevice(wires=1, shots=1000, analytic=False)
        op_str = dev.pauliz_operator_string(wires)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", obs_serialize)
    def test_qubitoperator_string_needs_decompose(self, obs, expected):
        dev = QeIBMQDevice(wires=1, shots=1000, analytic=False)
        op_str = dev.qubitoperator_string(obs)
        assert op_str == expected

    @pytest.mark.parametrize("wires", [[0], list(range(4)), ['a'], ['a','b']])
    def test_serialize_operator(self, wires):
        """Test that a circuit that is serialized correctly without rotations for
        a simulator backend"""
        pass
