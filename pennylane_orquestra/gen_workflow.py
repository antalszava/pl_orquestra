forest_import = {'name': 'qe-forest',
   'type': 'git',
   'parameters': {'repository': 'git@github.com:zapatacomputing/qe-forest.git',
    'branch': 'dev'}
  }


qiskit_import = {'name': 'qe-qiskit',
   'type': 'git',
   'parameters': {'repository': 'git@github.com:zapatacomputing/qe-qiskit.git',
    'branch': 'dev'}
  }

qhipster_import = {'name': 'qe-qhipster',
   'type': 'git',
   'parameters': {'repository': 'git@github.com:zapatacomputing/qe-qhipster.git',
    'branch': 'dev'}
  }

qulacs_import = {'name': 'qe-qulacs',
   'type': 'git',
   'parameters': {'repository': 'git@github.com:zapatacomputing/qe-qulacs.git',
    'branch': 'dev'}
  }

backend_import_db = {
        'qe-forest': forest_import,
        'qe-qhipster': qhipster_import,
        'qe-qiskit': qiskit_import,
        'qe-qulacs': qulacs_import
        }

def expval_template(component, backend_specs, circuit, operators, **kwargs):
    """Workflow template for computing the expectation value of operators
    given a quantum circuit and a device backend.

    Args:
        component (str): the name of the Orquestra component to use
        backend_specs (str): the Orquestra backend specifications as a json
            string
        circuit (str): the circuit is represented as an OpenQASM 2.0
            program
        operators (list): the list of string for operators in an
            ``openfermion.QubitOperator`` or ``openfermion.IsingOperator``
            representation
    
    Keyword arguments:
        noise_model=None (str): the noise model to use
        device_connectivity=None (str): the device connectivity of the remote
            device
        resources=None (str): the machine resources to use for executing the
            workflow

    Returns:
        dict: the dictionary that contains the workflow template to be
        submitted to Orquestra
    """
    noise_model = kwargs.get('noise_model', None)
    device_connectivity = kwargs.get('device_connectivity', None)

    backend_import = backend_import_db.get(component, None)
    if backend_import is None:
        raise ValueError("The specified backend component is not supported.")
    
    expval_template = {'apiVersion': 'io.orquestra.workflow/1.0.0',
     'name': 'expval',
     'imports': [{'name': 'pl_orquestra',
       'type': 'git',
       'parameters': {'repository': 'git@github.com:antalszava/pl_orquestra.git',
        'branch': 'master'}},
      {'name': 'z-quantum-core',
       'type': 'git',
       'parameters': {'repository': 'git@github.com:zapatacomputing/z-quantum-core.git',
        'branch': 'dev'}},
      {'name': 'qe-openfermion',
       'type': 'git',
       'parameters': {'repository': 'git@github.com:zapatacomputing/qe-openfermion.git',
        'branch': 'dev'}},
        # Will insert: main backend import
            ],
     'steps': [{'name': 'run-circuit-and-get-expval',
       'config': {'runtime': {'language': 'python3',
         'imports': ['pl_orquestra',
          'z-quantum-core',
          'qe-openfermion',
            # Will insert: step backend component import
            ],
         'parameters': {'file': 'pl_orquestra/steps/expval.py',
          'function': 'run_circuit_and_get_expval'}}
        },
        # Will insert: inputs
       'outputs': [{'name': 'expval',
         'type': 'expval',
         'path': '/app/expval.json'}]}],
     'types': ['circuit', 'expval', 'noise-model', 'device-connectivity']}
    
    # TODO: update indexing when having multiple steps
    
    # Insert the backend component to the main imports
    expval_template['imports'].append(backend_import)

    resources = kwargs.get('resources', None)
    if resources is not None:
        # Insert the backend component to the import list of the step
        expval_template['steps'][0]['config']['resources'] = resources

    # Insert the backend component to the import list of the step
    expval_template['steps'][0]['config']['runtime']['imports'].append(component)

    # Insert step inputs
    expval_template['steps'][0]['inputs'] = []
    expval_template['steps'][0]['inputs'].append({'backend_specs': backend_specs, 'type': 'string'})

    if noise_model is not None:
        expval_template['steps'][0]['inputs'].append({'noise_model': noise_model, 'type': 'noise-model'})

    if device_connectivity is not None:
        expval_template['steps'][0]['inputs'].append({'device_connectivity': device_connectivity, 'type': 'device-connectivity'})

    expval_template['steps'][0]['inputs'].append({'operators': operators, 'type': 'string'})
    expval_template['steps'][0]['inputs'].append({'circuit': circuit, 'type': 'string'})
    
    return expval_template
