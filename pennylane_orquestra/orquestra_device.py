"""
Base device class for PennyLane-Orquestra.
"""
import abc
import json
import re

import numpy as np

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires

from . import __version__


class OrquestraDevice(QubitDevice, abc.ABC):
    """Orquestra device"""

    name = "Orquestra device"
    short_name = "orquestra.base"
    pennylane_requires = ">=0.11.0"
    version = __version__
    author = "Antal Szava"
    # _capabilities = {"model": "qubit", "tensor_observables": True, "inverse_operations": True}

    operations = {'BasisState',
     'CNOT',
     'CRX',
     'CRY',
     'CRZ',
     'CRot',
     'CSWAP',
     'CY',
     'CZ',
     'DiagonalQubitUnitary',
     'Hadamard',
     'MultiRZ',
     'PauliX',
     'PauliY',
     'PauliZ',
     'PhaseShift',
     'QubitStateVector',
     'QubitUnitary',
     'RX',
     'RY',
     'RZ',
     'Rot',
     'S',
     'SWAP',
     'SX',
     'T',
     'Toffoli'}

    observables = {"PauliX", "PauliY", "PauliZ", "Identity", "Hadamard", "Hermitian"}

    def __init__(self, wires, backend_device, shots=1000, analytic=True, **kwargs):
        super().__init__(wires=wires, shots=shots, analytic=analytic)

        self.backend_device = backend_device
        # self._pre_rotated_state = self._state

    def apply(self, operations, **kwargs):
        pass

    def create_backend_specs(self, **run_kwargs):

        # TODO: do we want to cache this?
        backend_specs = {}
        backend_specs["module_name"] = self.qe_module_name
        backend_specs["function_name"] = self.qe_function_name
        backend_specs["device_name"] = self.backend_device

        if not self.analytic:
            backend_specs["n_samples"] = self.shots

        return json.dumps(backend_specs)

    def execute(self, circuit, **kwargs):

        not_all_expval = any(obs.return_type is not Expectation for obs in circuit.observables)
        if not_all_expval:
            raise NotImplementedError('OrquestraDevice only supports returning expectation values.')

        self.check_validity(circuit.operations, circuit.observables)

        self._circuit_hash = circuit.hash

        # 1. Create the backend specs based on Device options and run_kwargs
        backend_specs = self.create_backend_specs(**run_kwargs)

        # TODO:
        # 2-3. Create qasm strings from the circuits & create the qubit operator
        qasm_circuit = self.serialize_circuit(circuit)
        qubit_operator = self.serialize_operator(circuit, **kwargs)

        # 4. Create the parallel workflow file
        workflow_file = create_parallel_workflow_file(backend_specs, qasm_circuits, qubit_operator, **run_kwargs)

        # 5. Submit the workflow
        workflow_id = qe_submit(workflow_file)

        # 6. Loop until finished
        data = loop_until_finished(workflow_id)
        return data

    def serialize_circuit(self, circuit):
        """Serializes the circuit before submission according to the backend
        specified.

        The circuit is represented as an OpenQASM 2.0 program.
        Measurement instructions are removed from the program as the backend is
        instructed to measure all qubits by default by Orquestra.

        Args:
            circuit (~.CircuitGraph): circuit to serialize
        """
        # Remote hardware backends need rotations to be applied
        needs_rotation = "backend" in self.qe_module_name
        qasm_str = circuit.to_openqasm(rotations=needs_rotation)

        qasm_without_measurements = re.sub('measure.*?;\n', '', qasm_str)

        return qasm_without_measurements

    # TODO: finalize
    def get_qubit_operator_repr(self):
        from pennylane.utils import decompose_hamiltonian
        # 1. decompose
        decomp = decompose_hamiltonian(qml.Hadamard(wires=[0]).matrix)

        observables = decomp[1]
        for idx in range(len(observables)):
            obs = observables[idx]
            if not isinstance(obs, qml.operation.Tensor):
                decomp[1][idx] = qml.operation.Tensor(obs)

        _terms_to_qubit_operator(decomp[0], decomp[1])
    '''
    def apply_operations(self, operations):
        """Apply the circuit operations to the state.

        This method serves as an auxiliary method to :meth:`~.OrquestraDevice.apply`.

        Args:
            operations (List[pennylane.Operation]): operations to be applied
        """

        for i, op in enumerate(operations):
            if i > 0 and isinstance(op, (QubitStateVector, BasisState)):
                raise DeviceError(
                    "Operation {} cannot be used after other Operations have already been applied "
                    "on a {} device.".format(op.name, self.short_name)
                )

            if isinstance(op, QubitStateVector):
                self._apply_qubit_state_vector(op)
            elif isinstance(op, BasisState):
                self._apply_basis_state(op)
            elif isinstance(op, QubitUnitary):
                self._apply_qubit_unitary(op)
            elif isinstance(op, (CRZ, PhaseShift)):
                self._apply_matrix(op)
            else:
                self._apply_gate(op)

    def _apply_qubit_state_vector(self, op):
        """Initialize state with a state vector"""
        wires = op.wires
        input_state = op.parameters[0]

        if len(input_state) != 2 ** len(wires):
            raise ValueError("State vector must be of length 2**wires.")
        if input_state.ndim != 1 or len(input_state) != 2 ** len(wires):
            raise ValueError("State vector must be of length 2**wires.")
        if not np.isclose(np.linalg.norm(input_state, 2), 1.0, atol=tolerance):
            raise ValueError("Sum of amplitudes-squared does not equal one.")

        input_state = _reverse_state(input_state)

        # call orquestra' state initialization
        self._state.load(input_state)

    def _apply_basis_state(self, op):
        """Initialize a basis state"""
        wires = op.wires
        par = op.parameters

        # translate from PennyLane to Orquestra wire order
        bits = par[0][::-1]
        n_basis_state = len(bits)

        if not set(bits).issubset({0, 1}):
            raise ValueError("BasisState parameter must consist of 0 or 1 integers.")
        if n_basis_state != len(wires):
            raise ValueError("BasisState parameter and wires must be of equal length.")

        basis_state = 0
        for bit in bits:
            basis_state = (basis_state << 1) | bit

        # call orquestra' basis state initialization
        self._state.set_computational_basis(basis_state)

    def _apply_qubit_unitary(self, op):
        """Apply unitary to state"""
        # translate op wire labels to consecutive wire labels used by the device
        device_wires = self.map_wires(op.wires)
        par = op.parameters

        if len(par[0]) != 2 ** len(device_wires):
            raise ValueError("Unitary matrix must be of shape (2**wires, 2**wires).")

        if op.inverse:
            par[0] = par[0].conj().T

        # reverse wires (could also change par[0])
        reverse_wire_labels = device_wires.tolist()[::-1]
        unitary_gate = gate.DenseMatrix(reverse_wire_labels, par[0])
        self._circuit.add_gate(unitary_gate)
        unitary_gate.update_quantum_state(self._state)

    def _apply_matrix(self, op):
        """Apply predefined gate-matrix to state (must follow orquestra convention)"""
        # translate op wire labels to consecutive wire labels used by the device
        device_wires = self.map_wires(op.wires)
        par = op.parameters

        mapped_operation = self._operation_map[op.name]
        if op.inverse:
            mapped_operation = self._get_inverse_operation(mapped_operation, device_wires, par)

        if callable(mapped_operation):
            gate_matrix = mapped_operation(*par)
        else:
            gate_matrix = mapped_operation

        # gate_matrix is already in correct order => no wire-reversal needed
        dense_gate = gate.DenseMatrix(device_wires.labels, gate_matrix)
        self._circuit.add_gate(dense_gate)
        gate.DenseMatrix(device_wires.labels, gate_matrix).update_quantum_state(self._state)

    def _apply_gate(self, op):
        """Apply native orquestra gate"""

        # translate op wire labels to consecutive wire labels used by the device
        device_wires = self.map_wires(op.wires)
        par = op.parameters

        mapped_operation = self._operation_map[op.name]
        if op.inverse:
            mapped_operation = self._get_inverse_operation(mapped_operation, device_wires, par)

        # Negating the parameters such that it adheres to orquestra
        par = np.negative(par)

        # mapped_operation is already in correct order => no wire-reversal needed
        self._circuit.add_gate(mapped_operation(*device_wires.labels, *par))
        mapped_operation(*device_wires.labels, *par).update_quantum_state(self._state)

    @staticmethod
    def _get_inverse_operation(mapped_operation, device_wires, par):
        """Return the inverse of an operation"""

        if mapped_operation is None:
            return mapped_operation

        # if an inverse variant of the operation exists
        try:
            inverse_operation = getattr(gate, mapped_operation.get_name() + "dag")
        except AttributeError:
            # if the operation is hard-coded
            try:
                if callable(mapped_operation):
                    inverse_operation = np.conj(mapped_operation(*par)).T
                else:
                    inverse_operation = np.conj(mapped_operation).T
            # if mapped_operation is a orquestra.gate and np.conj is applied on it
            except TypeError:
                # else, redefine the operation as the inverse matrix
                def inverse_operation(*p):
                    # embed the gate in a unitary matrix with shape (2**wires, 2**wires)
                    g = mapped_operation(*p).get_matrix()
                    mat = reduce(np.kron, [np.eye(2)] * len(device_wires)).astype(complex)
                    mat[-len(g) :, -len(g) :] = g

                    # mat follows PL convention => reverse wire-order
                    reverse_wire_labels = device_wires.tolist()[::-1]
                    gate_mat = gate.DenseMatrix(reverse_wire_labels, np.conj(mat).T)
                    return gate_mat

        return inverse_operation

    def analytic_probability(self, wires=None):
        """Return the (marginal) analytic probability of each computational basis state."""
        if self._state is None:
            return None

        all_probs = self._abs(self.state) ** 2
        prob = self.marginal_prob(all_probs, wires)
        return prob

    @property
    def state(self):
        # returns the state after all operations are applied
        return _reverse_state(self._pre_rotated_state.get_vector())

    def reset(self):
        self._state.set_zero_state()
        self._pre_rotated_state = self._state
        self._circuit = QuantumCircuit(self.num_wires)
    '''
