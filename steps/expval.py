import json
from zquantum.core.utils import create_object, save_value_estimate, save_list, ValueEstimate
from openfermion import QubitOperator, SymbolicOperator, IsingOperator
from zquantum.core.circuit import Circuit

from zquantum.core.measurement import (
    expectation_values_to_real,
    ExpectationValues,
    Measurements,
)

from qiskit import QuantumCircuit
import numpy as np

from collections import Sequence

def run_circuit_and_get_expval(
    backend_specs: dict,
    circuit: str,
    operators: list,
    noise_model: str = "None",
    device_connectivity: str = "None",
):
    """Takes a circuit to obtain the expectation value of an operator on a
    given backend.

    All backend calls used in this function are defined as ``QuantumBackend``
    and ``QuantumSimulator`` interface standard methods implemented are defined
    in the ``z-quantum-core`` repository.

    Args:
        backend_specs (dict): the parsed Orquestra backend specifications
        circuit (str): the circuit represented as an OpenQASM 2.0 program
        operators (str): the operator in an ``openfermion.QubitOperator``
            or ``openfermion.IsingOperator`` representation

    Keyword arguments:
        noise_model="None" (str): the noise model to use
        device_connectivity="None" (str): the device connectivity of the remote
            device
    """
    backend_specs = json.loads(backend_specs)
    operators = json.loads(operators)

    if noise_model != "None":
        backend_specs["noise_model"] = load_noise_model(noise_model)
    if device_connectivity != "None":
        backend_specs["device_connectivity"] = load_circuit_connectivity(device_connectivity)

    backend = create_object(backend_specs)

    sampling_mode = backend.n_samples is not None

    # 1. Parse circuit
    qc = QuantumCircuit.from_qasm_str(circuit)
    circuit = Circuit(qc)

    if not isinstance(operators, Sequence):
        operators = [target_operator]

    # 2. Create operators
    ops = []
    for op in operators:
        if sampling_mode:
            # Operator for Backend/Simulator in sampling mode
            ops.append(IsingOperator(op))
        else:
            # Operator for Simulator exact mode
            ops.append(QubitOperator(op))

    # 3. Expval
    results = []
    if sampling_mode:
        # Sampling mode --- Simulator sampling or Backend
        measurements = backend.run_circuit_and_measure(circuit)

        # Iterating through the operators specified e.g., [IsingOperator("[Z0]
        # + [Z1]"), IsingOperator("[Z1]")] to post-process the measurements
        # outcomes
        for op in ops:
            expectation_values = measurements.get_expectation_values(op)
            expectation_values = expectation_values_to_real(expectation_values)

            # Summing the expectation values obtained for each term of the
            # operator yields the expectation value for the operator
            # E.g., <psi|Z0 + Z1|psi> = <psi|Z0|psi> + <psi|Z1|psi>
            val = np.sum(expectation_values.values)
            results.append(val)
    else:
        # Exact version --- Simulator exact
        for op in ops:
            # Note: each expval considers the circuit separately
            # As the logic is backend specific, better to use the standard
            # get_exact_expectation_values method (instead of caching the state
            # in some way)
            expectation_values = backend.get_exact_expectation_values(circuit, op)

            val = np.sum(expectation_values.values)
            results.append(val)

    save_list(results, "expval.json")
