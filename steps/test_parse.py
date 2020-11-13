import pytest
import parse

openqasm_str = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nry(0.4) q[0];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];\n'

serialized_circuit = {"schema": "zapata-v1-circuit", "name": "circuit0", "gates": [{"name": "Ry", "qubits": [{"index": 0, "info": {"label": "qiskit", "qreg": "QuantumRegister(2, 'q')", "num": 0}}], "info": {"label": "qiskit"}, "params": [0.4]}, {"name": "MEASURE", "qubits": [{"index": 0, "info": {"label": "qiskit", "qreg": "QuantumRegister(2, 'q')", "num": 0}}], "info": {"label": "qiskit"}, "params": []}, {"name": "MEASURE", "qubits": [{"index": 1, "info": {"label": "qiskit", "qreg": "QuantumRegister(2, 'q')", "num": 1}}], "info": {"label": "qiskit"}, "params": []}], "qubits": [{"index": 0, "info": {"label": "qiskit", "qreg": "QuantumRegister(2, 'q')", "num": 0}}, {"index": 1, "info": {"label": "qiskit", "qreg": "QuantumRegister(2, 'q')", "num": 1}}], "info": {"label": "qiskit"}}

class TestPLAnsatz:
    def test_parse(self, monkeypatch):
        local_list = []
        monkeypatch.setattr(parse, "save_circuit", lambda circuit, file_name: local_list.append(circuit))
        parse.create_circuit_from_qasm(openqasm_str)
        assert local_list[0].to_dict(serialize_gate_params=True) == serialized_circuit

    def test_execute_qiskit(self, monkeypatch):
        local_list = []
        only_measure_qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\nmeasure q[0] -> c[0];\nmeasure q[1] -> c[1];\n'
        monkeypatch.setattr(parse, "save_json", lambda counts, file_name: local_list.append(counts))

        parse.execute_qiskit(only_measure_qasm)
        assert local_list[0] == {'00': 1024}
