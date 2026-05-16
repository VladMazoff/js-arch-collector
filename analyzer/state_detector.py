"""Detect mutable state variables — improved for architecture analysis."""
from typing import Dict, List, Any
from collections import Counter, defaultdict
from config import CONFIG
from utils.ast_helpers import _get_attr, get_identifier_name


class StateDetector:
    """Finds the most mutated variables (potential state)."""

    def find_mutable_state(self, ast_data: Dict[str, Any]) -> List[Dict]:
        assignments = ast_data.get("assignments", [])
        globals_list = ast_data.get("globals", [])

        mutation_counter = Counter()
        mutation_details = defaultdict(lambda: {
            "locations": [],
            "operators": [],
            "methods": [],
            "update_types": [],
            "is_global": False,
        })

        global_names = {g["name"] for g in globals_list}

        for assign in assignments:
            target = assign.get("target")
            if not target or not isinstance(target, str):
                continue

            mutation_counter[target] += 1
            details = mutation_details[target]

            details["locations"].append(assign.get("loc"))
            
            # Оператор или метод
            op = assign.get("operator")
            method = assign.get("method")
            if op:
                details["operators"].append(op)
            if method:
                details["methods"].append(method)

            # Тип обновления
            assign_type = assign.get("type", "assignment")
            if assign_type == "mutation":
                details["update_types"].append(f"mutation.{method}")
            elif op and op != "=":
                details["update_types"].append(f"compound.{op}")
            else:
                details["update_types"].append("reassignment")

            # Глобальность
            if (target in global_names or 
                target.startswith(("window.", "globalThis.")) or 
                "." in target):
                details["is_global"] = True

        # Формируем результат
        results = []
        for var_name, count in mutation_counter.most_common(CONFIG.get("top_state_limit", 15)):
            details = mutation_details[var_name]
            inferred_type = self._infer_type(var_name, globals_list, details)

            results.append({
                "name": var_name,
                "mutation_count": count,
                "inferred_type": inferred_type,
                "is_global": details["is_global"],
                "update_types": list(set(details["update_types"]))[:4],   # лимит
                "methods": list(set(details["methods"]))[:4],
                "sample_locations": details["locations"][:2],
            })

        return results

    def _infer_type(self, var_name: str, globals_list: List[Dict], details: Dict) -> str:
        """Улучшенная типизация переменной"""
        name_lower = var_name.lower()

        # 1. Прямое объявление в глобальной области
        for g in globals_list:
            if g.get("name") == var_name:
                init = g.get("init_type")
                if init == "ArrayExpression":
                    return "array"
                if init == "ObjectExpression":
                    return "object"
                if init == "Literal":
                    return "primitive"
                if init in ("NewExpression", "CallExpression"):
                    return "instance"

        # 2. По методам мутации
        methods = details.get("methods", [])
        if any(m in ["push", "pop", "shift", "unshift", "splice", "sort"] for m in methods):
            return "array"
        if any(m in ["assign"] for m in methods):
            return "object"

        # 3. По имени переменной (эвристика)
        if any(x in name_lower for x in ["roofs", "items", "list", "array", "favorites"]):
            return "array"
        if any(x in name_lower for x in ["filter", "config", "state", "data", "filters"]):
            return "object"
        if any(x in name_lower for x in ["count", "index", "length", "total"]):
            return "primitive (counter)"

        # 4. По типам обновлений
        update_types = details.get("update_types", [])
        if any("compound" in ut for ut in update_types):
            return "primitive (number)"

        return "object" if "." in var_name else "mixed"