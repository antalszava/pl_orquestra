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
    classifiers=(
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        "qiskit==0.18.3",
        "qiskit-ibmq-provider==0.6.1",
        "pyquil==2.17.0",
        "numpy>=1.18.1",
        #"z-quantum-core",
        #"qe-openfermion",
    ],
)
