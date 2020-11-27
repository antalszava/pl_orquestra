An approach for integration with Orquestra

**Installation**

Installing [PennyLane](https://github.com/PennyLaneAI/pennylane) and the [qe-cli](https://github.com/zapatacomputing/qe-cli) are required.

The package can be installed using `pip` and running `pip install -e .` from
the `pl_orquestra` folder.

**Supported Orquestra backends**

The following Orquestra backends are supported at the moment:

* `QiskitSimulator`
* `ForestSimulator`
* `QulacsSimulator`
* `IBMQBackend` (still under development)

The `backend_device` option can be passed as a keyword argument to the
`qml.device` PennyLane function (see example).

**Examples**

*Using `QulacsSimulator`*

```python
import pennylane as qml

dev = qml.device('orquestra.qulacs', wires=3, analytic=True, keep_workflow_files=True)

@qml.qnode(dev)
def circuit():
    qml.PauliX(0)
    return qml.expval(qml.PauliZ(0))

circuit()
```

*Using `QiskitSimulator` with the `statevector_simulator`*

```python
import pennylane as qml

dev = qml.device('orquestra.qulacs', wires=3, analytic=True, keep_workflow_files=True)

@qml.qnode(dev)
def circuit():
    qml.PauliX(0)
    return qml.expval(qml.PauliZ(0)), qml.expval(qml.PauliZ(1))

circuit()
```
