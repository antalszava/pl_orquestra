# pylint: disable=protected-access, consider-using-enumerate
"""
Base device class for PennyLane-Orquestra.
"""
import abc
import json
import uuid
import re

from pennylane import QubitDevice
from pennylane.operation import Expectation, Tensor
from pennylane.ops import Identity
from pennylane.wires import Wires
from pennylane.utils import decompose_hamiltonian

from pennylane_orquestra._version import __version__
from pennylane_orquestra.utils import _terms_to_qubit_operator_string
from pennylane_orquestra.gen_workflow import gen_expval_workflow
from pennylane_orquestra.cli_actions import qe_submit, loop_until_finished, write_workflow_file


class OrquestraDevice(QubitDevice, abc.ABC):
    """The Orquestra base device.

    Provides the ``~.execute`` and ``~.batch_execute`` methods which allows
    remote device executions by generating, submitting Orquestra workflows and
    processing their results.

    The ``~.batch_execute`` method can be utilized to send workflows that
    contain several circuits which are computed in parallel on a remote device.

    The workflow files generated are placed into a user specific data folder
    specified by the output of ``appdirs.user_data_dir("pennylane-orquestra",
    "Xanadu")``. By default, such files are removed (see
    ``keep_files`` keyword argument). After each device execution,
    filenames for the generated workflows are stored in the ``filenames``
    attribute.

    Computing the expectation value of the identity operator does not involve a
    workflow submission (hence no files are created).

    Args:
        wires (int, Iterable[Number, str]]): Number of subsystems represented
            by the device, or iterable that contains unique labels for the
            subsystems as numbers (i.e., ``[-1, 0, 2]``) or strings (``['ancilla',
            'q1', 'q2']``). Default 1 if not specified.
        shots (int): number of circuit evaluations/random samples used to estimate
            expectation values of observables
        analytic (bool): If ``True``, the device calculates probability,
            expectation values, and variances analytically. If ``False``, a finite
            number of samples set by the argument ``shots`` are used to estimate
            these quantities.

    Keyword Args:
        backend=None (str): the Orquestra backend device to use for the
            specific Orquestra backend, if applicable
        batch_size=10 (int): the size of each circuit batch when using the
            ``~.batch_execute`` method to send multiple workflows
        keep_files=False (bool): Whether or not the workflow files
            generated during the circuit execution should be kept or deleted.
        resources (dict): the resources to be specified for each workflow step
        timeout=300 (int): seconds to wait until raising a TimeoutError
    """

    name = "Orquestra device"
    short_name = "orquestra.base"
    pennylane_requires = ">=0.11.0"
    version = __version__
    author = "Antal Szava"

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
        "Hadamard",
        "MultiRZ",
        "PauliX",
        "PauliY",
        "PauliZ",
        "PhaseShift",
        "QubitStateVector",
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

    observables = {"PauliX", "PauliY", "PauliZ", "Identity", "Hadamard"}

    def __init__(self, wires, shots=1000, analytic=True, **kwargs):
        super().__init__(wires=wires, shots=shots, analytic=analytic)

        self.backend = kwargs.get("backend", None)
        self._batch_size = kwargs.get("batch_size", 10)
        self._keep_files = kwargs.get("keep_files", False)
        self._resources = kwargs.get("resources", None)
        self._timeout = kwargs.get("timeout", 300)
        self._latest_id = None
        self._filenames = []
        self._backend_specs = None

    def apply(self, operations, **kwargs):
        pass

    @classmethod
    def capabilities(cls):
        capabilities = super().capabilities().copy()
        capabilities.update(
            model="qubit",
            supports_inverse_operations=False,
            supports_analytic_computation=True,
            returns_probs=False,
        )
        return capabilities

    @property
    def backend_specs(self):
        """The backend specifications defined for the device.

        Returns:
            str: the backend specifications represented as a string
        """
        if self._backend_specs is None:
            backend_specs_dict = self.create_backend_specs()
            self._backend_specs = json.dumps(backend_specs_dict)

        return self._backend_specs

    def create_backend_specs(self):
        """Create the backend specifications based on the device options.

        Returns:
            dict: the backend specifications represented as a dictionary
        """
        backend_specs = {}
        backend_specs["module_name"] = self.qe_module_name
        backend_specs["function_name"] = self.qe_function_name

        if self.backend is not None:
            # Only backends that have multiple backend need to specify one
            # E.g., qe-qiskit
            backend_specs["device_name"] = self.backend

        if not self.analytic:
            backend_specs["n_samples"] = self.shots

        return backend_specs

    def execute(self, circuit, **kwargs):

        # Input checks
        not_all_expval = any(obs.return_type is not Expectation for obs in circuit.observables)
        if not_all_expval:
            raise NotImplementedError(
                f"The {self.short_name} device only supports returning expectation values."
            )

        self.check_validity(circuit.operations, circuit.observables)

        # 1. Create qasm strings from the circuits
        try:
            qasm_circuit = self.serialize_circuit(circuit)
        except AttributeError:
            # QuantumTape case: need to extract the CircuitGraph
            qasm_circuit = self.serialize_circuit(circuit.graph)

        # 2. Create the qubit operators
        ops, identity_indices = self.process_observables(circuit.observables)

        if not ops:
            # All the observables were identity, no workflow submission needed
            return self._asarray([1] * len(identity_indices))

        ops_json = json.dumps(ops)

        # Single step: need to nest the operators into a list
        ops = [ops_json]
        qasm_circuit = [qasm_circuit]

        # 4-5. Create the backend specs & workflow file
        workflow = gen_expval_workflow(
            self.qe_component,
            self.backend_specs,
            qasm_circuit,
            ops,
            resources=self._resources,
            **kwargs,
        )
        file_id = str(uuid.uuid4())
        filename = f"expval-{file_id}.yaml"
        filepath = write_workflow_file(filename, workflow)

        # 6. Submit the workflow
        workflow_id = qe_submit(filepath, keep_file=self._keep_files)

        if self._keep_files:
            self._filenames.append(filename)

        self._latest_id = workflow_id

        # 7. Loop until finished
        data = loop_until_finished(workflow_id, timeout=self._timeout)

        # Assume that there's only one step
        results = [v for k, v in data.items()][0]["expval"]["list"]

        # Insert the theoretical value for the expectation value of the
        # identity operator
        for idx in identity_indices:
            results.insert(idx, 1)

        res = self._asarray(results)

        return res

    @staticmethod
    def insert_identity_res_batch(results, empty_obs_list, identity_indices):
        """An auxiliary function for inserting values which were not computed
        using workflows into batch results.

        Computations involving the identity observable are given by theoretical
        values rather than as part of a workflow. Therefore, such values need
        to be inserted into the results later.

        Args:
            results (list): workflow results of the batched execution
            empty_obs_list (list): list of indices where every observable was
                identity
            identity_indices (dict): maps the index of a sublist to the
                the list of indices where the observable was an identity

        Returns:
            list: list of results
        """
        # Insert the lists needed for only identity results
        for idx in empty_obs_list:
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

    @property
    def filenames(self):
        """Returns the names of the workflow files created during device
        executions.

        Returns:
            list: the workflow filenames
        """
        return self._filenames

    @property
    @abc.abstractmethod
    def qe_module_name(self):
        """Device specific Orquestra module name used in the backend
        specification."""

    @property
    @abc.abstractmethod
    def qe_function_name(self):
        """Device specific Orquestra function name used in the backend
        specification."""

    @property
    @abc.abstractmethod
    def qe_component(self):
        """Device specific Orquestra component name used in the backend
        specification."""

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

        qasm_without_measurements = re.sub("measure.*?;\n?\s*", "", qasm_str)
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

            original_observable = observable

            # Decompose the matrix of the observable
            # This removes information about the wire labels used and
            # consecutive integer wires are used
            coeffs, obs_list = decompose_hamiltonian(original_observable.matrix)

            for idx in range(len(obs_list)):
                obs = obs_list[idx]

                if not isinstance(obs, Tensor):
                    # Convert terms to Tensor such that _terms_to_qubit_operator
                    # can be used
                    obs_list[idx] = Tensor(obs)

                # Need to use the custom wire labels of the original observable
                original_wires = original_observable.wires.tolist()
                for o, mapped_w in zip(obs_list[idx].obs, original_wires):
                    o._wires = Wires(mapped_w)

        else:
            if not isinstance(observable, Tensor):
                # If decomposition is not needed and is not a Tensor, we need
                # to convert the single observable
                observable = Tensor(observable)

            coeffs = [1]
            obs_list = [observable]

        # Use consecutive integers as default wire_map
        wire_map = {v: idx for idx, v in enumerate(self.wires)}
        return _terms_to_qubit_operator_string(coeffs, obs_list, wires=wire_map)

    def batch_execute(self, circuits, **kwargs):
        results = []
        idx = 0
        file_prefix = f"{str(uuid.uuid4())}"

        # Iterating through the circuits based on the allowed number of
        # circuits per workflow
        while idx < len(circuits):
            end_idx = idx + self._batch_size
            batch = circuits[idx:end_idx]
            file_id = f"{file_prefix}-{str(idx)}"

            res = self._batch_execute(batch, file_id, **kwargs)

            results.extend(res)
            idx += self._batch_size

        return results

    def _batch_execute(self, circuits, file_id, **kwargs):
        """Creates a multi-step workflow for executing a batch of circuits.

        Args:
            circuits (list[QuantumTape]): circuits to execute on the device
            file_id (str): the file id to be used for naming the workflow file

        Returns:
            list[array[float]]: list of measured value(s) for the batch
        """
        for circuit in circuits:
            # Input checks
            not_all_expval = any(obs.return_type is not Expectation for obs in circuit.observables)
            if not_all_expval:
                raise NotImplementedError(
                    f"The {self.short_name} device only supports returning expectation values."
                )

            self.check_validity(circuit.operations, circuit.observables)

        # 1. Create qasm strings from the circuits
        # Extract the CircuitGraph object from QuantumTape
        circuits = [circ.graph for circ in circuits]
        qasm_circuits = [self.serialize_circuit(circuit) for circuit in circuits]

        # 2. Create the qubit operators of observables for each circuit
        ops = []
        identity_indices = {}
        empty_obs_list = []

        for idx, circuit in enumerate(circuits):
            processed_observables, current_id_indices = self.process_observables(
                circuit.observables
            )
            ops.append(processed_observables)
            if not processed_observables:
                # Keep track of empty observable lists
                empty_obs_list.append(idx)

            identity_indices[idx] = current_id_indices

        if not all(ops):
            # There were batches which had only identity observables

            if not any(ops):
                # All the batches only had identity observables, no workflow submission needed
                return [self._asarray([1] * len(circuit.observables)) for circuit in circuits]

            # Remove the empty lists so that those are not submitted
            ops = [o for o in ops if o]

        # Multiple steps: need to create json strings as elements of the list
        ops = [json.dumps(o) for o in ops]

        # 3-4. Create the backend specs & workflow file
        workflow = gen_expval_workflow(
            self.qe_component,
            self.backend_specs,
            qasm_circuits,
            ops,
            resources=self._resources,
            **kwargs,
        )

        filename = f"expval-{file_id}.yaml"
        filepath = write_workflow_file(filename, workflow)

        # 5. Submit the workflow
        workflow_id = qe_submit(filepath, keep_file=self._keep_files)
        self._latest_id = workflow_id

        if self._keep_files:
            self._filenames.append(filename)

        # 6. Loop until finished
        data = loop_until_finished(workflow_id, timeout=self._timeout)

        # Due to parallel execution, results might have been written in any order
        # Sort the results by the step name
        get_step_name = lambda entry: entry[1]["stepName"]
        data = dict(sorted(data.items(), key=get_step_name))

        # There are multiple steps
        # Obtain the results for each step
        result_dicts = [v for k, v in data.items()]
        results = [dct["expval"]["list"] for dct in result_dicts]

        results = self.insert_identity_res_batch(results, empty_obs_list, identity_indices)
        results = [self._asarray(res) for res in results]

        return results
