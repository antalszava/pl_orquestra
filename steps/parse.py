from zquantum.core.interfaces.ansatz import Ansatz, ansatz_property
from zquantum.core.circuit import Circuit, Qubit, create_layer_of_gates
from zquantum.core.evolution import time_evolution
from zquantum.core.circuit._circuit import save_circuit, load_circuit
from typing import Union, Optional, List
import numpy as np
import sympy
from overrides import overrides

from qiskit import(
  QuantumCircuit,
  execute,
  Aer)

from pl_orquestra.utils import save_json


def create_circuit_from_qasm(circuit: str):
    """Creates an Orquestra core Circuit object from an OpenQASM string."""
    qc = QuantumCircuit.from_qasm_str(circuit)
    zcircuit = Circuit(qc)
    save_circuit(zcircuit, "circuit.json")

def create_circuit():
    """Creates an Orquestra core Circuit object from an OpenQASM string."""
    circuit = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nry(0.4) q[0];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];\n'
    qc = QuantumCircuit.from_qasm_str(circuit)
    zcircuit = Circuit(qc)
    save_circuit(zcircuit, "circuit.json")

def empty_func():
    pass

def execute_qiskit(circuit):
    """Executes an OpenQASM string using the QasmSimulator backend."""
    qc = QuantumCircuit.from_qasm_str(circuit)

    # Run the quantum circuit on a statevector simulator backend
    backend = Aer.get_backend('qasm_simulator')

    # Create a Quantum Program for execution
    job = execute(qc, backend)

    result = job.result()
    counts = result.get_counts()

    save_json(counts, "results.json")
