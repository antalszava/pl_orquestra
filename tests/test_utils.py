# Copyright 2018-2020 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import numpy as np

import pennylane as qml
from pennylane_orquestra import utils


class TestUtils:
    """Test the utility functions of the PennyLane-Orquestra plugin."""

    def test_terms_to_qubit_operator_no_decomp(self):
        coeffs = np.array([0.1, 0.2])
        ops = [
            qml.operation.Tensor(qml.PauliX(wires=['w0'])),
            qml.operation.Tensor(qml.PauliY(wires=['w0']), qml.PauliZ(wires=['w2']))
        ]
        op_str = utils._terms_to_qubit_operator(coeffs, ops, wires=qml.wires.Wires(['w0', 'w1', 'w2']))
        expected = '0.1 [X0] + 0.2 [Y0 Z2]'
        assert op_str == expected

    def test_error_terms_to_qubit_operator(self):
        r"""Test if the conversion complains about non-Pauli matrix
        observables"""
        with pytest.raises(
            ValueError,
            match="Expected only PennyLane observables PauliX/Y/Z or Identity, but also got {"
            "'QuadOperator'}.",
        ):
            utils._terms_to_qubit_operator(
                np.array([0.1 + 0.0j, 0.0]),
                [
                    qml.operation.Tensor(qml.PauliX(0)),
                    qml.operation.Tensor(qml.PauliZ(0), qml.QuadOperator(0.1, wires=1)),
                ],
            )
