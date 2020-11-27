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

def step_dictionary(name_suffix):
    name = 'run-circuit-and-get-expval-' + name_suffix
    step_dict = {'name': name,
           'config': {'runtime': {'language': 'python3',
             'imports': ['pl_orquestra',
              'z-quantum-core',
              'qe-openfermion',
                # Place to insert: step backend component import
                ],
             'parameters': {'file': 'pl_orquestra/steps/expval.py',
              'function': 'run_circuit_and_get_expval'}}
            },
            # Place to insert: inputs
           'outputs': [{'name': 'expval',
             'type': 'expval',
             'path': '/app/expval.json'}]}

    return step_dict

def expval_template(component, backend_specs, circuits, operators, **kwargs):
    """Workflow template for computing the expectation value of operators
    given a quantum circuit and a device backend.

    Args:
        component (str): the name of the Orquestra component to use
        backend_specs (str): the Orquestra backend specifications as a json
            string
        circuits (list): list of circuits where each circuit is represented as
            an OpenQASM 2.0 program
        operators (list): a nested list of operators, each operator is a string
            in an ``openfermion.QubitOperator`` or ``openfermion.IsingOperator``
            representation
    
    Keyword arguments:
        noise_model='None' (str): the noise model to use
        device_connectivity='None' (str): the device connectivity of the remote
            device
        resources=None (str): the machine resources to use for executing the
            workflow

    Returns:
        dict: the dictionary that contains the workflow template to be
        submitted to Orquestra
    """
    # By default Orquestra takes 'None' (needs to be a string)
    noise_model = 'None' if 'noise_model' not in kwargs else kwargs['noise_model']
    device_connectivity = 'None' if 'device_connectivity' not in kwargs else kwargs['device_connectivity']

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
        # Place to insert: main backend import
            ],
     'steps': [],
     'types': ['circuit', 'expval', 'noise-model', 'device-connectivity']}
    
    # Insert the backend component to the main imports
    expval_template['imports'].append(backend_import)

    resources = kwargs.get('resources', None)

    for idx, (circ, ops) in enumerate(zip(circuits, operators)):
        new_step = step_dictionary(str(idx))
        expval_template['steps'].append(new_step)

        if resources is not None:
            # Insert the backend component to the import list of the step
            expval_template['steps'][idx]['config']['resources'] = resources

        # Insert the backend component to the import list of the step
        expval_template['steps'][idx]['config']['runtime']['imports'].append(component)

        # Insert step inputs
        expval_template['steps'][idx]['inputs'] = []
        expval_template['steps'][idx]['inputs'].append({'backend_specs': backend_specs, 'type': 'string'})

        expval_template['steps'][idx]['inputs'].append({'noise_model': noise_model, 'type': 'noise-model'})
        expval_template['steps'][idx]['inputs'].append({'device_connectivity': device_connectivity, 'type': 'device-connectivity'})
        expval_template['steps'][idx]['inputs'].append({'operators': ops, 'type': 'string'})
        expval_template['steps'][idx]['inputs'].append({'circuit': circ, 'type': 'string'})

    return expval_template
