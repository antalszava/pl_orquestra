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

get_backend_import = lambda backend_component: backend_import_db[backend_component]

def expval_template(backend_component, backend_specs, qasm_circuit, operator_string, noise_model=None, device_connectivity=None, resources=None):
    
    if noise_model is None:
        noise_model = 'None'

    if device_connectivity is None:
        device_connectivity = 'None'

    backend_import = backend_import_db[backend_component]
    
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

    if resources is not None:
        # Insert the backend component to the import list of the step
        expval_template['steps'][0]['config']['resources'] = resources

    # Insert the backend component to the import list of the step
    expval_template['steps'][0]['config']['runtime']['imports'].append(backend_component)

    # Insert step inputs
    expval_template['steps'][0]['inputs'] = []
    expval_template['steps'][0]['inputs'].append({'backend_specs': backend_specs, 'type': 'string'})
    expval_template['steps'][0]['inputs'].append({'noise_model': noise_model, 'type': 'noise-model'})
    expval_template['steps'][0]['inputs'].append({'device_connectivity': device_connectivity, 'type': 'device-connectivity'})
    expval_template['steps'][0]['inputs'].append({'target_operator': operator_string, 'type': 'string'})
    expval_template['steps'][0]['inputs'].append({'circuit': qasm_circuit, 'type': 'string'})
    
    return expval_template
