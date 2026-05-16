"""Detect mutable state variables."""
from typing import Dict, List, Any
from collections import Counter
from config import CONFIG
from utils.ast_helpers import _to_dict_safe, _get_attr


class StateDetector:
    """Finds the most mutated variables (potential state)."""

    def find_mutable_state(self, ast_data: Dict[str, Any]) -> List[Dict]:
        """Returns top-N most mutated objects/variables."""
        assignments = ast_data.get("assignments", [])
        globals_list = ast_data.get("globals", [])

        mutation_counter = Counter()
        mutation_details = {}

        for assign in assignments:
            target = assign.get("target")
            if not target:
                continue
            mutation_counter[target] += 1
            if target not in mutation_details:
                mutation_details[target] = {
                    "locations": [],
                    "operators": [],
                    "right_types": [],
                }
            mutation_details[target]["locations"].append(assign.get("loc"))
            mutation_details[target]["operators"].append(assign.get("operator"))
            mutation_details[target]["right_types"].append(assign.get("right_type"))

        global_names = {g["name"] for g in globals_list}

        results = []
        for var_name, count in mutation_counter.most_common(CONFIG["top_state_limit"]):
            details = mutation_details[var_name]
            is_global = var_name in global_names
            inferred_type = self._infer_type(details["right_types"], globals_list, var_name)

            results.append({
                "name": var_name,
                "mutation_count": count,
                "is_global": is_global,
                "inferred_type": inferred_type,
                "operators": list(set(details["operators"])),
                "locations": details["locations"][:3],
            })

        return results

    def _infer_type(self, right_types: List[str], globals_list: List[Dict], var_name: str) -> str:
        for g in globals_list:
            if g["name"] == var_name:
                init = g.get("init_type")
                if init == "ArrayExpression":
                    return "array"
                elif init == "ObjectExpression":
                    return "object"
                elif init == "Literal":
                    return "primitive"
                elif init == "CallExpression":
                    return "instance"

        type_hints = {
            "ArrayExpression": "array",
            "ObjectExpression": "object",
            "Literal": "primitive",
            "CallExpression": "instance",
            "NewExpression": "instance",
            "BinaryExpression": "primitive",
            "UnaryExpression": "primitive",
            "UpdateExpression": "primitive",
            "SpreadElement": "array",
        }
        for rt in right_types:
            if rt in type_hints:
                return type_hints[rt]
        return "unknown"
