"""
The OrquestraQiskitdevice class for PennyLane-Orquestra.
"""
import numpy as np
import os

from pennylane import QubitDevice, DeviceError
from pennylane.operation import Sample, Variance, Expectation, Probability, State
from pennylane.ops import QubitStateVector, BasisState, QubitUnitary, CRZ, PhaseShift
from pennylane.wires import Wires


from .qiskit_device import QeQiskitDevice
from . import __version__



class QeIBMQDevice(QeQiskitDevice):
    """The Orquestra IBMQ device."""
    short_name = "orquestra.ibmq"

    qe_component = "qe-qiskit"
    qe_module_name = "qeqiskit.backend"
    qe_function_name = "QiskitBackend"

    def __init__(self, wires, shots=1024, backend_device="ibmq_qasm_simulator", **kwargs):

        token = os.getenv("IBMQX_TOKEN") or kwargs.get("ibmqx_token", None)
        url = os.getenv("IBMQX_URL") or kwargs.get("ibmqx_url", None)

        if token is not None:
            # token was provided by the user, so attempt to enable an
            # IBM Q account manually
            ibmq_kwargs = {"url": url} if url is not None else {}
            IBMQ.enable_account(token, **ibmq_kwargs)

        super().__init__(wires, backend_device=backend_device, shots=shots, **kwargs)
