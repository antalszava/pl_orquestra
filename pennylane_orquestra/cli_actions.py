import sys
import subprocess
import time
import os
import yaml
from appdirs import user_data_dir
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

def qe_submit(filepath, keep_file=False):
    """Function for submitting a workflow via a CLI call.
    
    Args:
        filepath (str): the filepath for the workflow file

    Keyword Args:
        keep_file=False (bool): whether or not to keep or delete the workflow
            file after submission

    Returns:
        str: the ID of the workflow submitted

    Raises:
        ValueError: if the submission was not successful
    """
    process = subprocess.Popen(['qe', 'submit', 'workflow', str(filepath)], 
                               stdout=subprocess.PIPE,
                               universal_newlines=True)
    res = process.stdout.readlines()

    success_msg = 'Successfully submitted workflow to quantum engine!\n'
    if success_msg not in res:
        raise ValueError(res)

    if not keep_file:
        # Delete file
        os.remove(filepath)

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

def write_workflow_file(filename, workflow):
    """Write a workflow file given the name of the file.

    This function will create a YAML file with the workflow content. The file
    is placed into a user specific data folder specified by using
    ``appdirs.user_data_dir``.

    Args:
        filename (str): the name of the file to write
        workflow (dict): the workflow generated as a dictionary
    """
    # Get the directory to write the file to
    directory = user_data_dir("pennylane-orquestra", "Xanadu")

    # Create target Directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    filepath = os.path.join(directory, filename)

    with open(filepath, 'w') as file:
        # Need to keep the order of the keys so that Orquestra accepts the YAML
        # file
        d = yaml.dump(workflow, file, sort_keys=False)

    return filepath

def loop_until_finished(workflow_id, timeout=300):
    """Loops until the workflow execution has finished by querying workflow
    details using the workflow ID.

    Args:
        workflow_id (str): the ID of the workflow for which to return the
            results

    Keyword args:
        timeout (int): seconds to wait until raising a TimeoutError

    Returns:
        dict: the resulting dictionary parsed from a json file
    """
    res = get_workflow_results(workflow_id)

    strips = [output.strip() for output in res]
    message = strips[0]

    start = time.time()
    while "is being processed. Please check back later." not in message:
        res = get_workflow_results(workflow_id)

        strips = [output.strip() for output in res]
        message = strips[0]
        if time.time()-start > timeout:
            current_status = workflow_details(workflow_id)
            raise TimeoutError(f'The workflow results for workflow '
                    f'{workflow_id} were not obtained after {timeout/60} minutes. '
                    f'{current_status}')

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

    try:
        with urllib.request.urlopen(location) as url:
            data = json.loads(url.read().decode())
    except UnboundLocalError:
        # This error is raised if the workflow failed and no URL for the
        # results was obtained
        raise ValueError(f'Something went wrong with the results. {current_status}')


    return data
