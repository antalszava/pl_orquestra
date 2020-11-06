def sum_func(pos_arg, **kwargs):
    res = 0
    res += pos_arg

    terms = list(kwargs.values())

    res += sum(terms)
    result = {'res': str(res)}
    save_json(result, "result.json")
    

# The following is used from an Orquestra tutorial
"""
Copyright Zapata Computing, Inc. All rights reserved.
"""

import json
from json import JSONEncoder
import numpy as np

def save_json(result, filename) -> None:
    """
    Saves data as JSON.
    Args:
        result (ditc): of data to save.
        filenames (str): file name to save the data in
            (should have a '.json' extension).
    """
    try:
        with open(filename,'w') as f:
            result["schema"] = "orquestra-v1-data"
            f.write(json.dumps(result, indent=2, cls=NumpyArrayEncoder)) 

    except IOError:
        print(f'Error: Could not open {filename}')
