"""
The OrquestraQiskitdevice class for PennyLane-Orquestra.
"""
import numpy as np

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires

from .orquestra_device import OrquestraDevice
from . import __version__



class QeQiskitDevice(OrquestraDevice):
    """Orquestra device"""
    short_name = "orquestra.qiskit"

    qe_component = "qe-qiskit"
    qe_module_name = "qeqiskit.simulator"
    qe_function_name = "QiskitSimulator"

    def __init__(self, wires, shots=1024, backend_device="qasm_simulator", **kwargs):
        super().__init__(wires, backend_device=backend_device, shots=shots, **kwargs)
