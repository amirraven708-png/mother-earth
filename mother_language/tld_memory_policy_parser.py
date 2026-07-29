"""
tld_memory_policy_parser.py
تبدیل ساختار MEMORY_POLICY از TLD به دیکشنری با استفاده از Regex
(بدون وابستگی به lark)
"""

import re
from typing import Dict, Any, Optional

def parse_memory_policy(tld_text: str) -> Optional[Dict[str, Any]]:
    pattern = r'MEMORY_POLICY\s+"([^"]+)"\s*\{([^}]*)\}'
    match = re.search(pattern, tld_text, re.DOTALL)
    if not match:
        return None
    name = match.group(1).strip()
    body = match.group(2).strip()
    params = {}
    for line in body.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip()
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        elif val.replace('.', '').replace('-', '').isdigit():
            val = float(val) if '.' in val else int(val)
        params[key] = val
    return {"name": name, "params": params}

def apply_policy_to_config(policy: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    param_mapping = {
        "hot_enter": "hot_enter",
        "hot_exit": "hot_exit",
        "warm_enter": "warm_enter",
        "warm_exit": "warm_exit",
        "decay_rate": "base_decay_rate",
        "access_gain": "access_heat_gain",
        "initial_state": "initial_state",
    }
    params = policy.get("params", {})
    calibrated = {}
    for tld_key, internal_key in param_mapping.items():
        if tld_key in params:
            calibrated[internal_key] = params[tld_key]
    if "initial_state" in calibrated:
        config["initial_state"] = calibrated.pop("initial_state")
    if calibrated:
        config["calibrator_params"] = calibrated
    return config

if __name__ == "__main__":
    sample_tld = '''
    MEMORY_POLICY "event_stream" {
        hot_enter = 0.75
        hot_exit = 0.55
        warm_enter = 0.30
        warm_exit = 0.15
        decay_rate = 0.015
        access_gain = 0.25
        initial_state = "warm"
    }
    '''
    policy = parse_memory_policy(sample_tld)
    print("📋 Extracted Policy:")
    print(policy)
    config = {"initial_state": "cold", "replication_factors": {"hot": 1, "warm": 2, "cold": 3}}
    new_config = apply_policy_to_config(policy, config)
    print("\n📋 Updated Config:")
    print(new_config)
