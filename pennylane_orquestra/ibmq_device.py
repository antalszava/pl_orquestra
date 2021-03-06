"""
The IBMQ device class for PennyLane-Orquestra.
"""
import warnings
import os

from pennylane_orquestra.orquestra_device import OrquestraDevice


class QeIBMQDevice(OrquestraDevice):
    """The Orquestra IBMQ device."""

    short_name = "orquestra.ibmq"

    qe_component = "qe-qiskit"
    qe_module_name = "qeqiskit.backend"
    qe_function_name = "QiskitBackend"

    def __init__(self, wires, shots=1024, backend="ibmq_qasm_simulator", **kwargs):

        self._token = os.getenv("IBMQX_TOKEN") or kwargs.get("ibmqx_token", None)

        if self._token is None:
            raise ValueError(
                "Please pass a valid IBMQX token to the device using the 'ibmqx_token' argument."
            )

        if "analytic" in kwargs and kwargs["analytic"]:
            # Raise a warning if the analytic attribute was set to True
            warnings.warn(
                "The {self.short_name} device cannot be used in "
                "analytic mode. Results are based on sampling."
            )

        kwargs["analytic"] = False
        super().__init__(wires, backend=backend, shots=shots, **kwargs)

    def create_backend_specs(self):
        backend_dict = super().create_backend_specs()

        # Plug in the IBMQ token
        backend_dict["api_token"] = self._token
        return backend_dict
