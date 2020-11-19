import sys
import subprocess
import time
import os

def qe_get(workflow_id, option='workflow'):
    """Function for getting a information via a CLI call.
    
    This function is mostly used for retrieving workflow related information.

    Args:
        workflow_id (str): the workflow id for which information will be
            retrieved

    Kwargs:
        option (str): The option specified for the ``qe get`` CLI call.
            Examples include ``workflow`` and ``workflowresult``.

    Returns:
        str: response message of the CLI call
    """
    process = subprocess.Popen(['qe', 'get', option, str(args)], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    return process.stdout.readlines()  

def qe_submit(file_name):
    """Function for submitting a workflow via a CLI call.
    
    Args:
        file_name (str): the name of the workflow file

    Returns:
        str: response message of the CLI call
    """
    process = subprocess.Popen(['qe', 'submit', 'workflow', str(file_name)], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    return process.stdout.readlines()    

def workflow_details(workflow_id):
    """Function for getting workflow details via a CLI call.

    Args:
        workflow_id (str): the workflow id for which information will be
            retrieved

    Kwargs:
        option (str): The option specified for the ``qe get`` CLI call.
            Examples include ``workflow`` and ``workflowresult``.

    Returns:
        str: response message of the CLI call
    """
    return qe_get(args, option='workflow')

def get_workflow_results(workflow_id):
    """Function for getting workflow results via a CLI call.

    Args:
        workflow_id (str): the workflow id for which information will be
            retrieved

    Kwargs:
        option (str): The option specified for the ``qe get`` CLI call.
            Examples include ``workflow`` and ``workflowresult``.

    Returns:
        str: response message of the CLI call
    """
    return qe_get(args, option='workflowresult')

def get_step_ids(res, workflow_id):
    step_ids = []

    for i in res[::-1]:
        
        # This is the line for columns --- end the reverse looping here
        if 'STEP' in i:
            break

        # Get the step IDs; using the fact that there's a
        # subscript '-' character when the step id is defined
        if workflow_id + '-' in i:
            step_id = [s for s in i.split() if workflow_id in s][0]
            step_ids.append(step_id)
            
    return step_ids
