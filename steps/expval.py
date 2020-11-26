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
    operators,
    noise_model: str = "None",
    device_connectivity: str = "None",
):
    """Takes a circuit to obtain the expectation value of an operator on a
    given backend.

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

    ops = []
    for op in operators:
        if sampling_mode:
            ops.append(IsingOperator(op))
        else:
            # Need to create operator for Simulator
            ops.append(QubitOperator(op))

    # 2. Expval
    results = []
    if sampling_mode:
        # TODO: how do we allow sampling?
        measurements = backend.run_circuit_and_measure(circuit)
        # TODO: define return_type
        # if return_type is not Samples:
        # Expval, need to post-process samples
        for op in ops:

            # Note: each expval runs the circuit every time
            #    measurements = self.run_circuit_and_measure(circuit)
            #    expectation_values = measurements.get_expectation_values(operator)
            # TODO: could we use a joint interface that runs the circuit ones and can ko
            # TODO: kwargs?:
            #     epsilon=epsilon,
            #     delta=delta,
            expectation_values = measurements.get_expectation_values(op)
            expectation_values = expectation_values_to_real(expectation_values)

            # TODO: is this needed?:
            val = ValueEstimate(np.sum(expectation_values.values))
            results.append(val)
    else:
        # Exact version
        # TODO
        pass
    # save_value_estimate(results, "expval.json")
    save_list(results, "expval.json")
