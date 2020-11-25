import sys
import subprocess
import time
import os
import urllib.request, json

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
    process = subprocess.Popen(['qe', 'get', option, str(workflow_id)], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    return process.stdout.readlines()  

def qe_submit(file_name):
    """Function for submitting a workflow via a CLI call.
    
    Args:
        file_name (str): the name of the workflow file

    Returns:
        str: the ID of the workflow submitted

    Raises:
        ValueError: if the submission was not successful
    """
    process = subprocess.Popen(['qe', 'submit', 'workflow', str(file_name)], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    res = process.stdout.readlines()

    success_msg = 'Successfully submitted workflow to quantum engine!\n'
    if success_msg not in res:
        raise ValueError(res)

    # Get the workflow ID after submitting a workflow
    workflow_id = res[1].split()[-1]
    return workflow_id

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
    return qe_get(workflow_id, option='workflow')

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
    return qe_get(workflow_id, option='workflowresult')

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

def loop_until_finished(workflow_id):
    res = get_workflow_results(workflow_id)

    strips = [output.strip() for output in res]
    message = strips[0]

    start = time.time()
    while "is being processed. Please check back later." not in message:
        res = get_workflow_results(workflow_id)

        strips = [output.strip() for output in res]
        message = strips[0]
        if time.time()-start > 240:
            current_status = workflow_details(workflow_id)
            raise TimeoutError(f'The workflow results for workflow {workflow_id} were not obtained after 5 minutes. {current_status}')

    if "is being processed. Please check back later." not in message:
        current_status = workflow_details(workflow_id)
        raise ValueError(f'Something went wrong with the results. {current_status}')

    if "aggregated workflow result request has failed" in message:
        raise ValueError('Something went wrong with executing your workflow.')

    results = get_workflow_results(workflow_id)

    # Try to get the results
    try:
        location = results[1].split()[1]
    except IndexError:
        print("".join(get_workflow_results(workflow_id)))

    with urllib.request.urlopen(location) as url:
        data = json.loads(url.read().decode())

    return data
