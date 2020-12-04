"""
The Qulacs device class for PennyLane-Orquestra.
"""
import numpy as np

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires

from .orquestra_device import OrquestraDevice
from . import __version__


class QeQulacsDevice(OrquestraDevice):
    """Orquestra device"""

    short_name = "orquestra.qulacs"

    qe_component = "qe-qulacs"
    qe_module_name = "qequlacs.simulator"
    qe_function_name = "QulacsSimulator"

    def __init__(self, wires, shots=1024, **kwargs):
        super().__init__(wires, shots=shots, **kwargs)
