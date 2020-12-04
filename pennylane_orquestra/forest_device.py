"""
The Forest device class for PennyLane-Orquestra.
"""
from pennylane_orquestra.orquestra_device import OrquestraDevice


class QeForestDevice(OrquestraDevice):
    """Orquestra device"""

    short_name = "orquestra.forest"

    qe_component = "qe-forest"
    qe_module_name = "qeforest.simulator"
    qe_function_name = "ForestSimulator"

    def __init__(self, wires, shots=1024, backend="wavefunction-simulator", **kwargs):
        super().__init__(wires, backend=backend, shots=shots, **kwargs)
