"""Data Flow Analysis — who reads/writes state, cross-group dependencies."""
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
from utils.ast_helpers import find_nodes, _get_attr, get_identifier_name, _to_dict_safe


class DataFlowAnalyzer:
    """Analyzes variable usage across functions: readers, writers, risk score."""

    def analyze(self, ast_data: Dict, functions: List[Dict]) -> Dict[str, Any]:
        """
        Returns:
            {
                "state_details": [{
                    "name": str,
                    "type": str,
                    "mutations": int,
                    "readers": [func_names],
                    "writers": [func_names],
                    "groups_involved": [group_names],
                    "risk_score": int (0-10),
                    "access_matrix": {func: "R"/"W"/"R/W"/""}
                }],
                "cross_group_state": [{
                    "variable": str,
                    "groups": [group_names],
                    "risk": "high"/"medium"
                }],
                "variable_function_matrix": {var: {func: "R"/"W"/"R/W"/""}}
            }
        """
        source = ast_data.get("source", "")
        assignments = ast_data.get("assignments", [])
        globals_list = ast_data.get("globals", [])

        # Build function name -> group mapping
        func_to_group = {}
        for func in functions:
            group = func.get("_group", "Others")
            func_to_group[func["name"]] = group

        # Extract all variable references from source (heuristic)
        # For each function, find which variables it reads/writes
        func_access = self._analyze_function_access(source, functions, assignments)

        state_details = []
        cross_group = []

        # Get top mutable state variables
        state_vars = self._get_state_vars(assignments, globals_list)

        for var_name in state_vars:
            readers = set()
            writers = set()
            access_matrix = {}

            for func_name, access in func_access.items():
                if func_name in ("[inline]", "<anonymous>", "<global>", ""):
                    continue
                if var_name in access.get("reads", set()):
                    readers.add(func_name)
                if var_name in access.get("writes", set()):
                    writers.add(func_name)

                # Build access string
                has_read = var_name in access.get("reads", set())
                has_write = var_name in access.get("writes", set())
                if has_read and has_write:
                    access_matrix[func_name] = "R/W"
                elif has_read:
                    access_matrix[func_name] = "R"
                elif has_write:
                    access_matrix[func_name] = "W"
                else:
                    access_matrix[func_name] = ""

            groups = set()
            for func in list(readers) + list(writers):
                g = func_to_group.get(func, "Others")
                groups.add(g)

            # Risk score heuristic
            risk = self._calc_risk(
                mutation_count=len([a for a in assignments if a.get("target") == var_name]),
                reader_count=len(readers),
                writer_count=len(writers),
                group_count=len(groups),
                is_global=var_name in {g["name"] for g in globals_list}
            )

            state_details.append({
                "name": var_name,
                "type": self._infer_type(var_name, globals_list, assignments),
                "mutations": len([a for a in assignments if a.get("target") == var_name]),
                "readers": sorted(list(readers)),
                "writers": sorted(list(writers)),
                "groups_involved": sorted(list(groups)),
                "risk_score": risk,
                "access_matrix": access_matrix,
            })

            # Cross-group shared state
            if len(groups) >= 2:
                cross_group.append({
                    "variable": var_name,
                    "groups": sorted(list(groups)),
                    "risk": "high" if len(groups) >= 3 else "medium",
                })

        # Build full variable-function matrix
        all_vars = [s["name"] for s in state_details]
        all_funcs = [f["name"] for f in functions if f["name"] != "<anonymous>"]
        matrix = {}
        for var in all_vars:
            matrix[var] = {}
            for func in all_funcs:
                # Find access from state_details
                sd = next((s for s in state_details if s["name"] == var), None)
                matrix[var][func] = sd["access_matrix"].get(func, "") if sd else ""

        return {
            "state_details": state_details,
            "cross_group_state": cross_group,
            "variable_function_matrix": matrix,
        }

    def _analyze_function_access(self, source: str, functions: List[Dict], 
                                  assignments: List[Dict]) -> Dict[str, Dict[str, Set]]:
        """For each function, determine which variables it reads and writes."""
        func_access = defaultdict(lambda: {"reads": set(), "writes": set()})

        # Build function name map: resolve <anonymous> to assigned names
        import re
        func_name_map = {}
        print(f"[DATA_FLOW] Resolving {len(functions)} functions...")
        for idx, func in enumerate(functions):
            name = func.get("name", "<anonymous>")
            original_name = name
            if name == "<anonymous>":
                loc = func.get("loc")
                if loc and loc.get("start"):
                    line_idx = loc["start"]["line"] - 1
                    lines = source.split("\n")
                    if 0 <= line_idx < len(lines):
                        # Check current line and up to 2 previous lines
                        for offset in range(0, 3):
                            check_idx = line_idx - offset
                            if check_idx >= 0 and check_idx < len(lines):
                                line = lines[check_idx]
                                # Match: const name = (, let name = (, var name = (, name = (
                                m = re.search(r'(?:const|let|var)\s+(\w+)\s*[=:]', line)
                                if m:
                                    name = m.group(1)
                                    break
                                # Match: name = function or name = (
                                m = re.search(r'(\w+)\s*=\s*(?:function|\()', line)
                                if m:
                                    name = m.group(1)
                                    break
            if original_name == "<anonymous>" and name != "<anonymous>":
                print(f"[DATA_FLOW] Resolved anonymous -> {name} (line {func.get('loc', {}).get('start', {}).get('line', '?')})")
            func_name_map[idx] = name
        print(f"[DATA_FLOW] Function map: {func_name_map}")

        # Simple heuristic: parse source line by line
        lines = source.split("\n")

        # Build function line ranges with resolved names
        func_ranges = []
        for idx, func in enumerate(functions):
            loc = func.get("loc")
            if loc and loc.get("start") and loc.get("end"):
                func_ranges.append({
                    "name": func_name_map.get(idx, func["name"]),
                    "start": loc["start"]["line"],
                    "end": loc["end"]["line"],
                })

        # For each assignment, find which function contains it
        for assign in assignments:
            target = assign.get("target")
            if not target:
                continue
            loc = assign.get("loc")
            if not loc or not loc.get("start"):
                continue
            line = loc["start"]["line"]

            # Find enclosing function
            for fr in func_ranges:
                if fr["start"] <= line <= fr["end"]:
                    func_access[fr["name"]]["writes"].add(target)
                    break
            else:
                # Global scope write
                func_access["<global>"]["writes"].add(target)

        # For reads: scan each function body for variable references
        # Heuristic: look for variable names in function body lines
        global_vars = set()
        for assign in assignments:
            t = assign.get("target")
            if t:
                global_vars.add(t)

        for fr in func_ranges:
            func_lines = lines[fr["start"]-1:fr["end"]]
            func_body = "\n".join(func_lines)
            for var in global_vars:
                # Check if variable is read (not just written)
                if var in func_body:
                    # Check if it's only on the left side of assignment
                    # Simple heuristic: if it appears in the function, consider it a read
                    # unless we already marked it as write
                    if var not in func_access[fr["name"]]["writes"]:
                        func_access[fr["name"]]["reads"].add(var)

        return dict(func_access)

    def _get_state_vars(self, assignments: List[Dict], globals_list: List[Dict]) -> List[str]:
        """Get unique state variable names from assignments."""
        vars_seen = set()
        for a in assignments:
            t = a.get("target")
            if t:
                vars_seen.add(t)
        # Also include globals
        for g in globals_list:
            vars_seen.add(g["name"])
        return sorted(list(vars_seen))

    def _infer_type(self, var_name: str, globals_list: List[Dict], 
                    assignments: List[Dict]) -> str:
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
        for a in assignments:
            if a.get("target") == var_name:
                rt = a.get("right_type")
                if rt == "ArrayExpression":
                    return "array"
                elif rt == "ObjectExpression":
                    return "object"
                elif rt == "Literal":
                    return "primitive"
        return "unknown"

    def _calc_risk(self, mutation_count: int, reader_count: int, writer_count: int,
                   group_count: int, is_global: bool) -> int:
        """Calculate risk score 0-10."""
        score = 0
        if is_global:
            score += 2
        score += min(mutation_count, 3)  # 0-3
        score += min(reader_count, 2)    # 0-2
        score += min(writer_count, 2)    # 0-2
        if group_count >= 3:
            score += 2
        elif group_count >= 2:
            score += 1
        return min(score, 10)
