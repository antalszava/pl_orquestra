import pytest
import subprocess
import os
import numpy as np

import pennylane as qml
import pennylane.tape
import pennylane_orquestra
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice
from conftest import test_batch_res0, test_batch_res1, test_batch_res2, test_batch_dict

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "statevector_simulator"}'
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
        """Test the option for keeping/deleting the workflow file."""

        file_name = 'test_workflow.yaml'
        dev = qml.device('orquestra.forest', wires=3, keep_workflow_files=keep)
        mock_res_dict = {'First': {'expval': {'list': [{'list': 123456789}]}}}

        assert not os.path.exists(tmpdir.join("expval.yaml"))
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Mocking Popen disables submitting to the Orquestra platform
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
        dev = backend(wires=1, shots=1000, backend_device='statevector_simulator', analytic=True)
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
    def test_qubit_operator_string_needs_decompose(self, obs, expected):
        dev = QeIBMQDevice(wires=1, shots=1000, analytic=False)
        op_str = dev.qubit_operator_string(obs)
        assert op_str == expected

    @pytest.mark.parametrize("wires", [[0], list(range(4)), ['a'], ['a','b']])
    def test_serialize_operator(self, wires):
        """Test that a circuit that is serialized correctly without rotations for
        a simulator backend"""
        pass

class TestBatchExecute:
    """Test the integration of the device with PennyLane."""

    @pytest.mark.parametrize("keep", [True, False])
    def test_batch_exec(self, keep, tmpdir, monkeypatch):
        """Test that the batch_execute method returns the desired result and
        that the result preserves the order in which circuits were
        submitted."""

        qml.enable_tape()

        with qml.tape.QuantumTape() as tape1:
            qml.RX(0.133, wires='a')
            qml.CNOT(wires=[0, 'a'])
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape2:
            qml.RX(0.432, wires=0)
            qml.RY(0.543, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape3:
            qml.RX(0.432, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        circuits = [tape1, tape2, tape3]

        dev = qml.device('orquestra.forest', wires=3, keep_workflow_files=keep)

        assert not os.path.exists(tmpdir.join("expval.yaml"))

        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Mocking Popen disables submitting to the Orquestra platform
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    test_batch_dict)

            res = dev.batch_execute(circuits)

            # We expect that the results are in the correct order
            assert np.allclose(res[0], test_batch_res0)
            assert np.allclose(res[1], test_batch_res1)
            assert np.allclose(res[2], test_batch_res2)
            file_kept = os.path.exists(tmpdir.join("expval-0.yaml"))

        assert file_kept if keep else not file_kept
        qml.disable_tape()

    @pytest.mark.parametrize("keep", [True, False])
    def test_batch_exec_multiple_workflow(self, keep, tmpdir, monkeypatch):
        """Test that the batch_execute method returns the desired result and
        that the result preserves the order in which circuits were submitted
        when batches are created in multiple workflows ."""

        qml.enable_tape()

        with qml.tape.QuantumTape() as tape1:
            qml.RX(0.133, wires='a')
            qml.CNOT(wires=[0, 'a'])
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape2:
            qml.RX(0.432, wires=0)
            qml.RY(0.543, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape3:
            qml.RX(0.432, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        circuits = [tape1, tape2, tape3]

        # Only allow a single circuit for each workflow
        dev = qml.device('orquestra.forest', wires=3, batch_size=1, keep_workflow_files=keep)

        # Check that no workflow files were created before
        assert not os.path.exists(tmpdir.join("expval-0.yaml"))
        assert not os.path.exists(tmpdir.join("expval-1.yaml"))
        assert not os.path.exists(tmpdir.join("expval-2.yaml"))

        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Mocking Popen disables submitting to the Orquestra platform
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    test_batch_dict)

            res = dev.batch_execute(circuits)

            # We expect that the results are in the correct order
            assert np.allclose(res[0], test_batch_res0)
            assert np.allclose(res[1], test_batch_res1)
            assert np.allclose(res[2], test_batch_res2)
            file0_kept = os.path.exists(tmpdir.join("expval-0.yaml"))
            file1_kept = os.path.exists(tmpdir.join("expval-1.yaml"))
            file2_kept = os.path.exists(tmpdir.join("expval-2.yaml"))

        # Check that workflow files were either all kept or all deleted
        files_kept = file0_kept and file1_kept and file2_kept
        assert files_kept and file0_kept if keep else not files_kept
        qml.disable_tape()
