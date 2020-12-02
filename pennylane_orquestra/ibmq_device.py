"""
The OrquestraQiskitdevice class for PennyLane-Orquestra.
"""
import numpy as np
import warnings
import os

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires


from .orquestra_device import OrquestraDevice
from . import __version__



class QeIBMQDevice(OrquestraDevice):
    """The Orquestra IBMQ device."""
    short_name = "orquestra.ibmq"

    qe_component = "qe-qiskit"
    qe_module_name = "qeqiskit.backend"
    qe_function_name = "QiskitBackend"

    def __init__(self, wires, shots=1024, backend_device="ibmq_qasm_simulator", **kwargs):

        self._token = os.getenv("IBMQX_TOKEN") or kwargs.get("ibmqx_token", None)

        if self._token is None:
            raise ValueError("Please pass a valid IBMQX token to the device using the 'ibmqx_token' argument.")

        if "analytic" in kwargs and kwargs["analytic"]:
            # Raise a warning if the analytic attribute was set to True
            warnings.warn("The {self.short_name} device cannot be used in "
                    "analytic mode. Results are based on sampling.")

        kwargs["analytic"] = False
        super().__init__(wires, backend_device=backend_device, shots=shots, **kwargs)

    def create_backend_specs(self):
        backend_dict = super().create_backend_specs()

        # Plug in the IBMQ token
        backend_dict["api_token"] = self._token
        return backend_dict
