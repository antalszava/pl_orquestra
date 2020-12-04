"""
The OrquestraQiskitdevice class for PennyLane-Orquestra.
"""
import numpy as np
import warnings

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires

from .orquestra_device import OrquestraDevice
from . import __version__



class QeQiskitDevice(OrquestraDevice):
    """The Orquestra Qiskit device."""
    short_name = "orquestra.qiskit"

    qe_component = "qe-qiskit"
    qe_module_name = "qeqiskit.simulator"
    qe_function_name = "QiskitSimulator"

    def __init__(self, wires, shots=1024, backend="qasm_simulator", **kwargs):
        if backend =="qasm_simulator":
            if "analytic" in kwargs and kwargs["analytic"]:
                # Raise a warning if the analytic attribute was set to True
                warnings.warn("The qasm_simulator backend device cannot be used in "
                        "analytic mode. Results are based on sampling.")

            kwargs["analytic"] = False
        super().__init__(wires, backend=backend, shots=shots, **kwargs)
