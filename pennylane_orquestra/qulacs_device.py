"""
The Qulacs device class for PennyLane-Orquestra.
"""
from pennylane_orquestra.orquestra_device import OrquestraDevice


class QeQulacsDevice(OrquestraDevice):
    """Orquestra device"""

    short_name = "orquestra.qulacs"

    qe_component = "qe-qulacs"
    qe_module_name = "qequlacs.simulator"
    qe_function_name = "QulacsSimulator"

    def __init__(self, wires, shots=1024, **kwargs):
        super().__init__(wires, shots=shots, **kwargs)
