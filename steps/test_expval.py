import pytest
import expval

import qeforest
import json
import os

class TestExpvalExact:
    def test_run_circuit_and_get_expval(self, monkeypatch, tmpdir):
        local_list = []

        backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator"}'

        only_measure_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
        target_op = "[Z0]"

        lst = []

        monkeypatch.setattr(expval, "load_circuit", lambda circuit: circuit)
        monkeypatch.setattr(expval, "save_value_estimate", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, only_measure_qasm, target_op)
        assert lst[0] == 1

    def test_run_circuit_and_get_expval_hadamard(self, monkeypatch, tmpdir):
        local_list = []

        backend_specs = '{"module_name": "qeforest.simulator", "function_name": "ForestSimulator", "device_name": "wavefunction-simulator"}'

        hadamard_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nh q[0];\n'
        target_op = "[Z0]"

        lst = []

        monkeypatch.setattr(expval, "load_circuit", lambda circuit: circuit)
        monkeypatch.setattr(expval, "save_value_estimate", lambda val, name: lst.append(val))

        expval.run_circuit_and_get_expval(backend_specs, hadamard_qasm, target_op)
        assert lst[0] == 0.0
