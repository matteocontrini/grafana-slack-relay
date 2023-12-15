import json


def json_serialize(obj):
    return json.dumps(obj, ensure_ascii=False)
