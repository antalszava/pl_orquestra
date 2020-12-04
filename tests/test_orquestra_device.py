import pytest
import subprocess
import os
import uuid
import time
import numpy as np

import pennylane as qml
import pennylane.tape
import pennylane_orquestra
from pennylane_orquestra import OrquestraDevice, QeQiskitDevice, QeIBMQDevice
from conftest import test_batch_res0, test_batch_res1, test_batch_res2, test_batch_result

qiskit_analytic_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "statevector_simulator"}'
qiskit_sampler_specs = '{"module_name": "qeqiskit.simulator", "function_name": "QiskitSimulator", "device_name": "statevector_simulator", "n_samples": 1000}'


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

    def test_ibmq_analytic_warning(self):
        """Test that a warning is raised when using the IBMQDevice in analytic
        mode and that we'll switch to sampling mode."""
        with pytest.warns(Warning, match="device cannot be used in analytic mode. Results are based on sampling."):
            dev = qml.device('orquestra.ibmq', wires=2, analytic=True, ibmqx_token="Some token")

        assert not dev.analytic

    def test_ibmq_no_token_error(self):
        """Test that an error is raised when using the IBMQDevice without any
        tokens specified."""
        with pytest.raises(ValueError, match="Please pass a valid IBMQX token"):
            dev = qml.device('orquestra.ibmq', wires=2, analytic=False)

    @pytest.mark.parametrize("keep", [True, False])
    def test_keep_workflow_file(self, keep, tmpdir, monkeypatch):
        """Test the option for keeping/deleting the workflow file."""

        file_name = 'test_workflow.yaml'
        dev = qml.device('orquestra.forest', wires=3, keep_workflow_files=keep)
        mock_res_dict = {'First': {'expval': {'list': [{'list': 123456789}]}}}
        test_uuid = "1234"

        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}.yaml"))
        assert not dev.filenames
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    mock_res_dict)

            # Disable random uuid generation
            m.setattr(uuid, "uuid4", lambda *args: test_uuid)

            @qml.qnode(dev)
            def circuit():
                qml.PauliX(0)
                return qml.expval(qml.PauliZ(0))

            assert circuit() == 123456789
            file_kept = os.path.exists(tmpdir.join(f"expval-{test_uuid}.yaml"))
            assert file_kept if keep else not file_kept
            assert dev.filenames == ([f"expval-{test_uuid}.yaml"] if keep else [])

    @pytest.mark.parametrize("timeout", [1,2.5])
    def test_timeout(self, timeout, tmpdir, monkeypatch):
        """Test the option for keeping/deleting the workflow file."""

        file_name = 'test_workflow.yaml'
        dev = qml.device('orquestra.forest', wires=3, timeout=timeout)
        mock_res_dict = {'First': {'expval': {'list': [{'list': 123456789}]}}}

        test_uuid = "1234"
        assert dev._timeout == timeout
        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}.yaml"))
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)
            m.setattr(pennylane_orquestra.cli_actions, "get_workflow_results", lambda *args: "Test res")

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())

            # Disable random uuid generation
            m.setattr(uuid, "uuid4", lambda *args: test_uuid)

            @qml.qnode(dev)
            def circuit():
                qml.PauliX(0)
                return qml.expval(qml.PauliZ(0))

            start = time.time()
            with pytest.raises(TimeoutError, match="The workflow results for workflow"):
                circuit()
            end =  time.time()
            assert end-start >= timeout

    @pytest.mark.parametrize("dev", ['orquestra.forest', 'orquestra.qiskit', 'orquestra.qulacs'])
    def test_identity_single(self, dev):
        """Test computing the expectation value of the identity for a single return value."""
        dev = qml.device(dev, wires=1)

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.Identity(0))

        assert circuit() == 1

    @pytest.mark.parametrize("dev", ['orquestra.forest', 'orquestra.qiskit', 'orquestra.qulacs'])
    def test_identity_multiple(self, dev):
        """Test computing the expectation value of the identity for multiple return values."""
        dev = qml.device(dev, wires=2)

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.Identity(0)), qml.expval(qml.Identity(1))

        assert np.allclose(circuit(), np.ones(2))

    @pytest.mark.parametrize("dev", ['orquestra.forest', 'orquestra.qiskit', 'orquestra.qulacs'])
    def test_identity_single(self, dev):
        """Test computing the expectation value of the identity for a single return value."""
        dev = qml.device(dev, wires=1)

        @qml.qnode(dev)
        def circuit():
            qml.PauliX(0)
            return qml.expval(qml.Identity(0))

        assert circuit() == 1

    @pytest.mark.parametrize("dev", ['orquestra.forest', 'orquestra.qiskit', 'orquestra.qulacs'])
    def test_identity_multiple(self, dev, tmpdir, monkeypatch):
        """Test computing the expectation value of the identity for multiple
        return values."""
        qml.enable_tape()

        dev = qml.device(dev, wires=2, keep_workflow_files=True)

        with qml.tape.QuantumTape() as tape1:
            qml.RX(0.133, wires=0)
            qml.expval(qml.Identity(wires=[0]))

        with qml.tape.QuantumTape() as tape2:
            qml.RX(0.432, wires=0)
            qml.expval(qml.Identity(wires=[0]))
            qml.expval(qml.Identity(wires=[1]))

        circuits = [tape1, tape2]

        test_uuid = "1234"
        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    None)

            # Disable random uuid generation
            m.setattr(uuid, "uuid4", lambda *args: test_uuid)

            res = dev.batch_execute(circuits)

            # No workflow files were created because we only computed with
            # identities
            assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}.yaml"))
            assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}.yaml"))

            expected = [
                    np.ones(1),
                    np.ones(2),
                    ]

            for r, e in zip(res, expected):
                assert np.allclose(r, e)

            qml.disable_tape()
class TestCreateBackendSpecs:
    """Test the create_backend_specs function"""

    def test_backend_specs_analytic(self):
        """Test that the backend specs are created well for an analytic device"""
        dev = qml.device("orquestra.qiskit", backend_device="statevector_simulator", wires=1, analytic=True)
        assert dev.backend_specs == qiskit_analytic_specs

    @pytest.mark.parametrize("backend", [QeQiskitDevice])
    def test_backend_specs_sampling(self, backend):
        """Test that the backend specs are created well for a sampling device"""
        dev = qml.device("orquestra.qiskit", backend_device="statevector_simulator", wires=1,  shots=1000, analytic=False)
        assert dev.backend_specs == qiskit_sampler_specs

class TestSerializeCircuit:
    """Test the serialize_circuit function"""

    def test_serialize_circuit_rotations(self):
        """Test that a circuit that is serialized correctly with rotations for
        a remote hardware backend"""
        dev = QeQiskitDevice(wires=1, shots=1000, backend_device='qasm_simulator', analytic=False)

        def circuit():
            qml.Hadamard(wires=[0])
            return qml.expval(qml.Hadamard(0))

        qnode = qml.QNode(circuit, dev)
        qnode._construct([], {})

        qasm = dev.serialize_circuit(qnode.circuit)
        expected = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\ncreg c[1];\nh q[0];\nry(-0.7853981633974483) q[0];\n'
        assert qasm == expected

    def test_serialize_circuit_no_rotations(self):
        """Test that a circuit that is serialized correctly without rotations for
        a simulator backend"""
        dev = QeQiskitDevice(wires=1, shots=1000, backend_device="statevector_simulator", analytic=True)

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
]

obs_serialize_custom_labels = [
    # Custom wires
    (qml.PauliZ(wires=['a']), '1 [Z0]'),
    (qml.PauliX(wires=['c']), '1 [X2]'),
    (qml.Hermitian(mx, wires=['a', 'b']) @ qml.Identity(wires=['c']), "2.5 [] + -0.5 [Z1] + -1.0 [Z0]"),
]

serialize_needs_rot = [
        (qml.PauliZ(0) @ qml.PauliZ(2), '[Z0 Z2]'),
        (qml.PauliZ(2), '[Z2]'),
        (qml.PauliZ(0) @ qml.PauliZ(1) @ qml.PauliZ(2), '[Z0 Z1 Z2]'),

        # Rotations need to be included
        (qml.PauliY(2), '[Z2]'),
        (qml.PauliX(0) @ qml.PauliY(2), '[Z0 Z2]'),
        (qml.PauliY(0) @ qml.PauliX(1) @ qml.PauliY(2), '[Z0 Z1 Z2]')
]

class TestSerializeOperator:
    """Test the serialize_operator function"""

    @pytest.mark.parametrize("wires, expected", [([2], '[Z2]'), ([0, 2], '[Z0 Z2]'), ([0, 1, 2], '[Z0 Z1 Z2]')])
    def test_pauliz_operator_string(self, wires, expected):
        """Test that an operator is serialized correctly on a device with
        consecutive integer wires."""
        dev = QeQiskitDevice(wires=3, shots=1000, backend_device='qasm_simulator', analytic=False)
        op_str = dev.pauliz_operator_string(wires)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", obs_serialize)
    def test_qubit_operator_consec_int_wires(self, obs, expected):
        """Test that an operator is serialized correctly on a device with
        consecutive integer wires."""
        dev = QeQiskitDevice(wires=3, shots=1000, backend_device='qasm_simulator', analytic=False)
        op_str = dev.qubit_operator_string(obs)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", obs_serialize_custom_labels)
    def test_qubit_operator_custom_labels(self, obs, expected):
        """Test that an operator is serialized correctly on a device with
        custom wire labels."""
        dev = QeQiskitDevice(wires=['a','b','c'], shots=1000, backend_device='qasm_simulator', analytic=False)
        op_str = dev.qubit_operator_string(obs)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", serialize_needs_rot)
    def test_serialize_operator_needs_rotation(self, obs, expected):
        """Test that a device that needs to include rotations serializes the
        operators correctly."""
        dev = QeQiskitDevice(wires=3, shots=1000, backend_device='qasm_simulator', analytic=False)
        op_str = dev.serialize_operator(obs)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", obs_serialize)
    def test_serialize_operator_no_rot(self, obs, expected):
        """Test that a device that does not need to include rotations
        serializes the operators with consecutive integer wires correctly."""
        dev = QeQiskitDevice(wires=3, backend_device='statevector_simulator', analytic=True)
        op_str = dev.serialize_operator(obs)
        assert op_str == expected

    @pytest.mark.parametrize("obs, expected", obs_serialize_custom_labels)
    def test_serialize_operator_no_rot_custom_labels(self, obs, expected):
        """Test that a device that does not need to include rotations
        serializes the operators with custom labels correctly."""
        dev = QeQiskitDevice(wires=['a','b','c'], backend_device='statevector_simulator', analytic=True)
        op_str = dev.serialize_operator(obs)
        assert op_str == expected

    def test_operator_with_invalid_wire(self, monkeypatch):
        """Test that a device with custom wire labels raises an error when an
        invalid wire is used in the operator definition.
        
        This test is meant to check that the internal wire mappings do not
        introduce false positive behaviour when using custom wire labels.
        """
        dev = QeQiskitDevice(wires=['a','b','c'], shots=1000, backend_device='qasm_simulator', analytic=False)

        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    test_batch_result)

            @qml.qnode(dev)
            def circuit():
                return qml.expval(qml.PauliZ(0))

            with pytest.raises(qml.qnodes.base.QuantumFunctionError, match="Operation PauliZ applied to invalid wire"):
                circuit()

class TestBatchExecute:
    """Test the integration of the device with PennyLane."""

    @pytest.mark.parametrize("keep", [True, False])
    def test_batch_exec(self, keep, tmpdir, monkeypatch):
        """Test that the batch_execute method returns the desired result and
        that the result preserves the order in which circuits were
        submitted."""
        qml.enable_tape()

        dev = qml.device('orquestra.forest', wires=3, keep_workflow_files=keep)

        with qml.tape.QuantumTape() as tape1:
            qml.RX(0.133, wires=1)
            qml.CNOT(wires=[0, 1])
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape2:
            qml.RX(0.432, wires=0)
            qml.RY(0.543, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape3:
            qml.RX(0.432, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        circuits = [tape1, tape2, tape3]

        test_uuid = "1234"
        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}-0.yaml"))

        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    test_batch_result)

            # Disable random uuid generation
            m.setattr(uuid, "uuid4", lambda *args: test_uuid)

            res = dev.batch_execute(circuits)

            # Correct order of results is expected
            assert np.allclose(res[0], test_batch_res0)
            assert np.allclose(res[1], test_batch_res1)
            assert np.allclose(res[2], test_batch_res2)
            file_kept = os.path.exists(tmpdir.join(f"expval-{test_uuid}-0.yaml"))

            assert file_kept if keep else not file_kept

        qml.disable_tape()

    @pytest.mark.parametrize("keep", [True, False])
    @pytest.mark.parametrize("dev_name", ['orquestra.forest', 'orquestra.qiskit', 'orquestra.qulacs'])
    def test_batch_exec_multiple_workflow(self, keep, dev_name, tmpdir, monkeypatch):
        """Test that the batch_execute method returns the desired result and
        that the result preserves the order in which circuits were submitted
        when batches are created in multiple workflows ."""

        qml.enable_tape()

        with qml.tape.QuantumTape() as tape1:
            qml.RX(0.133, wires=0)
            qml.CNOT(wires=[0, 1])
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape2:
            qml.RX(0.432, wires=0)
            qml.RY(0.543, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        with qml.tape.QuantumTape() as tape3:
            qml.RX(0.432, wires=0)
            qml.expval(qml.PauliZ(wires=[0]))

        circuits = [tape1, tape2, tape3]

        # Setting batch size: allow only a single circuit for each workflow
        dev = qml.device(dev_name, wires=3, batch_size=1, keep_workflow_files=keep)

        # Check that no workflow files were created before
        test_uuid = "1234"
        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}-0.yaml"))
        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}-1.yaml"))
        assert not os.path.exists(tmpdir.join(f"expval-{test_uuid}-2.yaml"))

        with monkeypatch.context() as m:
            m.setattr(pennylane_orquestra.cli_actions, "user_data_dir", lambda *args: tmpdir)

            # Disable submitting to the Orquestra platform by mocking Popen
            m.setattr(subprocess, "Popen", lambda *args, **kwargs: MockPopen())
            m.setattr(pennylane_orquestra.orquestra_device,
                    "loop_until_finished", lambda *args, **kwargs:
                    test_batch_result)

            # Disable random uuid generation
            m.setattr(uuid, "uuid4", lambda *args: test_uuid)

            res = dev.batch_execute(circuits)

            # Correct order of results is expected
            assert np.allclose(res[0], test_batch_res0)
            assert np.allclose(res[1], test_batch_res1)
            assert np.allclose(res[2], test_batch_res2)
            file0_kept = os.path.exists(tmpdir.join(f"expval-{test_uuid}-0.yaml"))
            file1_kept = os.path.exists(tmpdir.join(f"expval-{test_uuid}-1.yaml"))
            file2_kept = os.path.exists(tmpdir.join(f"expval-{test_uuid}-2.yaml"))

        # Check that workflow files were either all kept or all deleted
        files_kept = file0_kept and file1_kept and file2_kept
        assert files_kept and file0_kept if keep else not files_kept

        qml.disable_tape()
