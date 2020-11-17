import json
from zquantum.core.utils import create_object, save_value_estimate, ValueEstimate
from openfermion import QubitOperator, SymbolicOperator, IsingOperator
from zquantum.core.circuit import Circuit

from qiskit import QuantumCircuit
import numpy as np

def run_circuit_and_get_expval(
    backend_specs: dict,
    circuit: str,
    target_operator,
    noise_model: str = "None",
    device_connectivity: str = "None"
    ):
    backend_specs = json.loads(backend_specs)
    if noise_model != "None":
        backend_specs["noise_model"] = load_noise_model(noise_model)
    if device_connectivity != "None":
        backend_specs["device_connectivity"] = load_circuit_connectivity(
            device_connectivity
        )

    backend = create_object(backend_specs)

    # 1. Parse circuit
    qc = QuantumCircuit.from_qasm_str(circuit)
    circuit = Circuit(qc)

    if backend.n_samples is None:
        # Need to create operator for Simulator
        op = QubitOperator(target_operator)
    else:
        op = IsingOperator(target_operator)

    # 2. Expval
    expectation_values = backend.get_expectation_values(
        circuit,
        op
        #     epsilon=epsilon,
        #     delta=delta,
        )
    val = ValueEstimate(np.sum(expectation_values.values))
    save_value_estimate(val, "expval.json")
