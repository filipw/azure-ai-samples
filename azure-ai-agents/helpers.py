import json

def print_json(json_obj):
    """Pretty print JSON data"""
    if isinstance(json_obj, str):
        try:
            json_obj = json.loads(json_obj)
        except:
            pass
    print(json.dumps(json_obj, indent=2))