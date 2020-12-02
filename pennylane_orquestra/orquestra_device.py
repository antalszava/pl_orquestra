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
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift, Identity
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
            "Xanadu")``. Computing the expectation value of the identity
            observable does not involve a workflow submission (hence no files
            are created).
        timeout=300 (int): seconds to wait until raising a TimeoutError
    """

    name = "Orquestra device"
    short_name = "orquestra.base"
    pennylane_requires = ">=0.11.0"
    version = __version__
    author = "Antal Szava"
    _capabilities = {"model": "qubit", "tensor_observables": True, "inverse_operations": True}

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
        self._keep_workflow_files = kwargs.get("keep_workflow_files", False)
        self._timeout = kwargs.get("timeout", 300)
        self._batch_size = kwargs.get("batch_size", 10)
        self._latest_id = None
        self._backend_specs = None
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
        try:
            qasm_circuit = self.serialize_circuit(circuit)
        except AttributeError:
            # QuantumTape case: need to extract the CircuitGraph
            qasm_circuit = self.serialize_circuit(circuit.graph)

        # 3. Create the qubit operators
        ops, identity_indices = self.process_observables(circuit.observables)

        if not ops:
            # All the observables were identity, no workflow submission needed
            return self._asarray([1] * len(identity_indices))

        ops_json = json.dumps(ops)

        # Single step: need to nest the operators into a list
        ops = [ops_json]
        qasm_circuit = [qasm_circuit]

        # 4. Create the workflow file
        workflow = expval_template(
            self.qe_component,
            backend_specs, qasm_circuit, ops, **kwargs
        )
        filename = 'expval.yaml'
        filepath = write_workflow_file(filename, workflow)

        # 5. Submit the workflow
        workflow_id = qe_submit(filepath, keep_file=self._keep_workflow_files)
        self._latest_id = workflow_id

        # 6. Loop until finished
        data = loop_until_finished(workflow_id, timeout=self._timeout)

        # Assume that there's only one step
        list_of_result_dicts = [v for k,v in data.items()][0]['expval']['list']

        # Obtain the value for each operator
        results = [res_dict['list'] for res_dict in list_of_result_dicts]

        # Insert the theoretical value for the expectation value of the
        # identity operator
        for idx in identity_indices:
            results.insert(idx, 1)

        res = self._asarray(results)

        return res

    def batch_execute(self, circuits, **kwargs):
        # TODO: do we pass the batch_size here or to the device?


        # 1. Create the backend specs based on Device options and run_kwargs
        self._backend_specs = self.create_backend_specs(**kwargs)

        idx = 0

        results = []

        # Iterating through the circuits based on the allowed number of
        # circuits per workflow
        while idx < len(circuits): 
            end_idx = idx + self._batch_size
            batch = circuits[idx:end_idx]
            res = self._batch_execute(batch, idx, **kwargs)
            results.extend(res)
            idx += self._batch_size

        return results

    def _batch_execute(self, circuits, batch_idx, **kwargs):
        """Creates a multi-step workflow for executing a batch of circuits.

        Args:
            circuits (list[QuantumTape]): circuits to execute on the device
            batch_idx (int): the index of the batch used to name the workflow

        Returns:
            list[array[float]]: list of measured value(s) for the batch
        """
        for circuit in circuits:
            obs = circuit.observables

            # Input checks
            not_all_expval = any(obs.return_type is not Expectation for obs in circuit.observables)
            if not_all_expval:
                raise NotImplementedError(f"The {self.short_name} device only supports returning expectation values.")

            self.check_validity(circuit.operations, circuit.observables)

            # TODO: process hashes as a batch
            self._circuit_hash = circuit.hash

        # 2. Create qasm strings from the circuits
        # Extract the CircuitGraph object from QuantumTape
        circuits = [circ.graph for circ in circuits]
        qasm_circuits = [self.serialize_circuit(circuit) for circuit in circuits]

        # 3. Create the qubit operators of observables for each circuit
        ops = []
        identity_indices = {}
        empty_ops_list = []

        for idx, circuit in enumerate(circuits):
            this_ops, this_indices = self.process_observables(circuit.observables)
            ops.append(this_ops)
            if not ops:
                # Keep track of empty operation lists
                empty_ops_list.append(idx)

            identity_indices[idx] = this_indices

        if not all(ops):
            # There were batches which had only identity observables

            if not any(ops):
                # All the batches only had identity observables, no workflow submission needed
                return [self._asarray([1] * len(circuit.observables)) for circuit in circuits]

            # Remove the empty lists so that those are not submitted
            ops = [o for o in ops if o]
            print(ops)

        # Multiple steps: need to create json strings as elements of the list
        ops = [json.dumps(o) for o in ops]

        # 4. Create the workflow file
        workflow = expval_template(
            self.qe_component,
            self._backend_specs, qasm_circuits, ops, **kwargs
        )
        filename = f'expval-{str(batch_idx)}.yaml'
        print(filename)
        filepath = write_workflow_file(filename, workflow)

        # 5. Submit the workflow
        workflow_id = qe_submit(filepath, keep_file=self._keep_workflow_files)
        self._latest_id = workflow_id

        # 6. Loop until finished
        data = loop_until_finished(workflow_id, timeout=self._timeout)

        # Due to parallel execution, results might have been written in any order
        # Sort the results by the step name
        get_step_name = lambda entry: entry[1]['expval']['stepName']
        data = {k: v for k, v in sorted(data.items(), key=get_step_name)}

        # There are multiple steps
        result_dicts = [v for k,v in data.items()]
        list_of_result_dicts = [dct['expval']['list'] for dct in result_dicts]

        # Obtain the results for each step
        results = []
        for res_step in list_of_result_dicts:
            extracted_results = [res_dict['list'] for res_dict in res_step]
            results.append(extracted_results)

        results = self.insert_identity_res_batch(results, empty_ops_list, identity_indices)
        results = [self._asarray(res) for res in results]

        return results

    def insert_identity_res_batch(self, results, empty_ops_list, identity_indices):
        """An auxiliary function for inserting values which were not computed
        using workflows into batch results.

        Computations involving the identity observable are given by theoretical
        values rather than as part of a workflow. Therefore, such values need
        to be inserted into the results later.

        Args:
            results (list): workflow results of the batched execution
            empty_ops_list (list): list of indices where every operation was identity
            identity_indices (dict): maps the index of a sublist to the
                the list of indices where the observable was an identity

        Returns:
            list: list of results
        """
        # Insert the lists needed for only identity results
        for idx in empty_ops_list:
            results.insert(idx, [])

        # Insert further identity results
        for list_idx in identity_indices.keys():
            for iden_idx in identity_indices[list_idx]:
                results[list_idx].insert(iden_idx, 1)

        return results

    @property
    def latest_id(self):
        """Returns the latest workflow ID that has been executed.

        Returns:
            str: the ID of the latest workflow that has been submitted
        """
        return self._latest_id

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
        qasm_str = circuit.to_openqasm(rotations=not self.analytic)

        qasm_without_measurements = re.sub("measure.*?;\n", "", qasm_str)
        return qasm_without_measurements

    def process_observables(self, observables):
        """Processes the observables provided with the circuits.

        If the observable defined is the identity, then no serialization
        happens. Instead, the index of the observable is saved.
        
        Args:
            observables (list): a list of observables to process
        
        Returns:
            tuple:
                
                * the serialized non-identity operators
                * the indices of the identity operators
        """
        ops = []
        identity_indices = []
        for idx, obs in enumerate(observables):
            if not isinstance(obs, Identity):
                # Only serialize if it's not the identity
                ops.append(self.serialize_operator(obs))
            else:
                # Otherwise keep track of the indices and use the theoreticaly
                # value as a result later
                identity_indices.append(idx)

        return ops, identity_indices


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
        if not self.analytic:
            obs_wires = observable.wires
            wires = self.wires.indices(obs_wires)
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

            # Decompose the matrix of the observable
            # This removes information about the wire labels used
            coeffs, obs_list = decompose_hamiltonian(observable.matrix)

            inverted_wire_map = {idx:v for idx, v in enumerate(self.wires)}
            for idx in range(len(obs_list)):
                obs = obs_list[idx]

                if not isinstance(obs, Tensor):
                    # Convert terms to Tensor such that _terms_to_qubit_operator
                    # can be used
                    obs_list[idx] = Tensor(obs)

                # The decomposition involved using consecutive integer wires
                # Need to use the custom wire labels, use the inverted wire map
                for o in obs_list[idx].obs:
                    mapped_wires = [inverted_wire_map[wire] for wire in o.wires.tolist()]
                    o._wires = Wires(mapped_wires)

        else:
            if not isinstance(observable, Tensor):
                # If decomposition is not needed and is not a Tensor, we need
                # to convert the single observable
                observable = Tensor(observable)

            coeffs = [1]
            obs_list = [observable]

        # Use consecutive integers as default wire_map
        wire_map = {v:idx for idx, v in enumerate(self.wires)}
        return _terms_to_qubit_operator_string(coeffs, obs_list, wires=wire_map)
