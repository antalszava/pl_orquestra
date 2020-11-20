import setuptools
import os

with open("README.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="pennylane-orquestra",
    version="0.0.1",
    author="Antal Szava",
    author_email="antalszava@gmail.com",
    description="Integrations for deploying on Orquestra",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/antalszava/pl_orquestra",
    packages=[
        "pl_component",
        "pennylane_orquestra",
    ],
    package_dir={
        "pl_component": "src/python",
        "pennylane_orquestra": "",
        },
    entry_points= {
        "pennylane.plugins": ["orquestra.qiskit = pennylane_orquestra:QeQiskitDevice",
                              "orquestra.qiskit.ibmq = pennylane_orquestra:QeIBMQDevice",
            ]
    },
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),
    install_requires=[
    ],
)
