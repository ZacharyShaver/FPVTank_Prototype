"""Checks call record() with the numbers the regression table compares (head-v2/checks/regression.py)."""
import json, os
import config

PATH = os.path.join(config.OUT, 'regression.json')

def record(key, value):
    d = {}
    if os.path.exists(PATH):
        with open(PATH) as f:
            d = json.load(f)
    d[key] = value
    os.makedirs(config.OUT, exist_ok=True)
    with open(PATH, 'w') as f:
        json.dump(d, f, indent=1, sort_keys=True)
