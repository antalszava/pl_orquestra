"""
Base device class for PennyLane-Orquestra.
"""
import abc
import json
import re
import appdirs

import numpy as np

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State, Tensor
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires
from pennylane.utils import decompose_hamiltonian

from . import __version__
from .utils import _terms_to_qubit_operator_string
from .gen_workflow import expval_template
from .cli_actions import qe_submit, loop_until_finished, write_workflow_file


class OrquestraDevice(QubitDevice, abc.ABC):
    """Orquestra device

    Keyword Args:
        keep_workflow_files=False (bool): Whether or not the workflow files
            generated during the circuit execution should be kept or deleted.
            These files are placed into a user specific data folder specified
            by the output of ``appdirs.user_data_dir("pennylane-orquestra",
            "Xanadu")``.
    
    """

    name = "Orquestra device"
    short_name = "orquestra.base"
    pennylane_requires = ">=0.11.0"
    version = __version__
    author = "Antal Szava"
    # _capabilities = {"model": "qubit", "tensor_observables": True, "inverse_operations": True}

    operations = {
        "BasisState",
        "CNOT",
        "CRX",
        "CRY",
        "CRZ",
        "CRot",
        "CSWAP",
        "CY",
        "CZ",
        "DiagonalQubitUnitary",
        "Hadamard",
        "MultiRZ",
        "PauliX",
        "PauliY",
        "PauliZ",
        "PhaseShift",
        "QubitStateVector",
        "QubitUnitary",
        "RX",
        "RY",
        "RZ",
        "Rot",
        "S",
        "SWAP",
        "SX",
        "T",
        "Toffoli",
    }

    observables = {"PauliX", "PauliY", "PauliZ", "Identity", "Hadamard", "Hermitian"}

    def __init__(self, wires, shots=1000, analytic=True, **kwargs):
        super().__init__(wires=wires, shots=shots, analytic=analytic)

        # TODO: allow noise_model and device_connectivity options

        self.backend_device = kwargs.get('backend_device', None)
        self._latest_id = None
        self._keep_workflow_files = kwargs.get("keep_workflow_files", False)
        # self._pre_rotated_state = self._state

    def apply(self, operations, **kwargs):
        pass

    def create_backend_specs(self, **run_kwargs):
        """Create the backend specifications based on the device options.

        Returns:
            str: the backend specifications represented as a string
        """
        # TODO: what can be run_kwargs? (any?)
        # TODO: do we want to cache this?
        backend_specs = {}
        backend_specs["module_name"] = self.qe_module_name
        backend_specs["function_name"] = self.qe_function_name

        if self.backend_device is not None:
            # Only backends that have multiple backend_device need to specify one
            # E.g., qe-qiskit
            backend_specs["device_name"] = self.backend_device

        if not self.analytic:
            backend_specs["n_samples"] = self.shots

        return json.dumps(backend_specs)

    def execute(self, circuit, **kwargs):

        # Input checks
        not_all_expval = any(obs.return_type is not Expectation for obs in circuit.observables)
        if not_all_expval:
            raise NotImplementedError(f"The {self.short_name} device only supports returning expectation values.")

        self.check_validity(circuit.operations, circuit.observables)

        self._circuit_hash = circuit.hash

        # 1. Create the backend specs based on Device options and run_kwargs
        backend_specs = self.create_backend_specs(**kwargs)

        # 2. Create qasm strings from the circuits
        qasm_circuit = self.serialize_circuit(circuit)

        # 3. Create the qubit operators
        ops = [self.serialize_operator(obs) for obs in circuit.observables]
        ops_json = json.dumps(ops)

        # 4. Create the workflow file
        workflow = expval_template(
            self.qe_component,
            backend_specs, qasm_circuit, ops_json, **kwargs
        )
        filename = 'expval.yaml'
        filepath = write_workflow_file(filename, workflow)

        # 5. Submit the workflow
        workflow_id = qe_submit(filepath, keep_file=self._keep_workflow_files)
        self._latest_id = workflow_id

        # 6. Loop until finished
        data = loop_until_finished(workflow_id)

        # Assume that there's only one step
        list_of_result_dicts = [v for k,v in data.items()][0]['expval']['list']

        # Obtain the value for each operator
        results = [res_dict['list'] for res_dict in list_of_result_dicts]

        if len(results) > 1:
            res = np.array(results)
        else:
            res = results[0]

        return res

    def batch_execute(self, circuits, **kwargs):
        # TODO: do we pass the batch_size here or to the device?
        batch_size = kwargs.get("batch_size", 10)

        idx = 0

        results = []

        # Iterating through the circuits with batches
        while idx < len(circuits): 
            end_idx = idx + batch_size
            batch = circuits[idx:end_idx]
            res = self._batch_execute(batch, kwargs)
            results.append(res)
            idx += batch_size

        return np.array(results)

    def _batch_execute(self, circuits, **run_kwargs):
        """

        Args:
            circuits (list): a list of ciruits represented as ``CircuitGraph``
                objects

        """

    @property
    def latest_id(self):
        """Returns the latest workflow ID that has been executed.

        Returns:
            str: the ID of the latest workflow that has been submitted
        """
        return self._latest_id

    @property
    def needs_rotations(self):
        """Determines whether the specified backend is a remote hardware device.

        When using a remote hardware backend the following are applicable:
        1. circuits need to include rotations (for observables other than PauliZ)
        2. the ``IsingOperator`` representation of OpenFermion needs to be used
        to serialize an ``Observable``

        Returns:
            bool: whether or not the backend specified needs rotations
        """
        return "backend" in self.qe_module_name

    def serialize_circuit(self, circuit):
        """Serializes the circuit before submission according to the backend
        specified.

        The circuit is represented as an OpenQASM 2.0 program. Measurement
        instructions are removed from the program as the operator is passed
        separately.

        Args:
            circuit (~.CircuitGraph): circuit to serialize

        Returns:
            str: OpenQASM 2.0 representation of the circuit without any
            measurement instructions
        """
        qasm_str = circuit.to_openqasm(rotations=self.needs_rotations)

        qasm_without_measurements = re.sub("measure.*?;\n", "", qasm_str)
        return qasm_without_measurements

    def serialize_operator(self, observable):
        """
        Serialize the observable specified for the circuit as an OpenFermion
        operator.

        Args:
            observable (~.Observable): the observable to get the operator
                representation for

        Returns:
            str: string representation of terms making up the observable
        """
        if self.needs_rotations:
            obs_wires = observable.wires
            wires = self.wires.index(obs_wires)
            op_str = self.pauliz_operator_string(wires)
        else:
            op_str = self.qubit_operator_string(observable)

        return op_str

    @staticmethod
    def pauliz_operator_string(wires):
        """Creates an OpenFermion operator string based on the related wires
        that can be passed when creating an ``openfermion.IsingOperator``.

        This method is used if rotations are needed for the backend specified.
        In such a case a string that represents measuring PauliZ on each of the
        affected wires is used.

        **Example**

        >>> dev = QeQiskitDevice(wires=2)
        >>> wires = [0, 1, 2]
        >>> op_str = dev.pauliz_operator_string(wires)
        >>> print(op_str)
        [Z0 Z1 Z2]
        >>> print(openfermion.IsingOperator(op_str))
        1.0 [Z0 Z1 Z2]

        Args:
            wires (Wires): the wires the observable of the quantum function
                acts on

        Returns:
            str: the ``openfermion.IsingOperator`` string representation
        """
        op_wires_but_last = [f"Z{w} " for w in wires[:-1]]
        op_last_wire = f"Z{wires[-1]}"
        op_str = "".join(["[", *op_wires_but_last, op_last_wire, "]"])
        return op_str

    def qubit_operator_string(self, observable):
        """Creates an OpenFermion operator string from an observable that can
        be passed when creating an ``openfermion.QubitOperator``.

        This method decomposes an observable into a sum of Pauli terms and
        identities, if needed.

        **Example**

        >>> dev = QeQiskitDevice(wires=2)
        >>> obs = qml.PauliZ(0)
        >>> op_str = dev.qubit_operator_string(obs)
        >>> print(op_str)
        1 [Z0]
        >>> obs = qml.Hadamard(0)
        >>> op_str = dev.qubit_operator_string(obs)
        >>> print(op_str)
        0.7071067811865475 [X0] + 0.7071067811865475 [Z0]

        Args:
            observable (pennylane.operation.Observable): the observable to serialize

        Returns:
            str: the ``openfermion.QubitOperator`` string representation
        """
        accepted_obs = {"PauliX", "PauliY", "PauliZ", "Identity"}

        if isinstance(observable, Tensor):
            need_decomposition = any(o.name not in accepted_obs for o in observable.obs)
        else:
            need_decomposition = observable.name not in accepted_obs

        if need_decomposition:
            coeffs, obs_list = decompose_hamiltonian(observable.matrix)

            for idx in range(len(obs_list)):
                obs = obs_list[idx]

                if not isinstance(obs, Tensor):
                    # Convert terms to Tensor such that _terms_to_qubit_operator
                    # can be used
                    obs_list[idx] = Tensor(obs)

        else:
            if not isinstance(observable, Tensor):
                # If decomposition is not needed and is not a Tensor, we need
                # to convert the single observable
                observable = Tensor(observable)

            coeffs = [1]
            obs_list = [observable]

        return _terms_to_qubit_operator_string(coeffs, obs_list)

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
