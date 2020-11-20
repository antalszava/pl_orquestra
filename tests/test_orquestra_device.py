import pytest

import pennylane as qml
from pennylane_orquestra import OrquestraDevice

class TestDevice:

    def test_error_if_not_expval(self):
        dev = qml.device('orquestra.device', wires=2)

        @qml.qnode(dev)
        def circuit():
            return qml.var(qml.PauliZ(0))

        with pytest.raises(NotImplementedError):
            circuit()
