"""Build call graph: who calls whom."""
from typing import Dict, List, Any, Optional
from utils.ast_helpers import find_nodes, get_identifier_name, _to_dict_safe, _get_attr
import networkx as nx


class CallGraphBuilder:
    """Builds a call graph from AST data."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.function_map = {}

    def build(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        self.graph = nx.DiGraph()
        self.function_map = {}

        functions = ast_data.get("functions", [])
        for func in functions:
            name = func.get("name", "<anonymous>")
            if name != "<anonymous>":
                self.function_map[name] = func
                self.graph.add_node(name, **func)

        return {
            "nodes": list(self.graph.nodes()),
            "edges": [],
            "god_functions": [],
            "orphan_functions": [],
        }

    def build_from_ast(self, ast_obj: Any, functions: List[Dict]) -> Dict[str, Any]:
        """Build call graph using the raw AST object."""
        self.graph = nx.DiGraph()
        self.function_map = {}

        for func in functions:
            name = func.get("name", "<anonymous>")
            if name != "<anonymous>":
                self.function_map[name] = func
                self.graph.add_node(name, **func)

        call_exprs = find_nodes(ast_obj.__dict__, "CallExpression")
        edges = []

        for call in call_exprs:
            call_dict = _to_dict_safe(call)
            callee = call_dict.get("callee")
            caller = self._find_enclosing_function(call, functions)
            callee_name = self._resolve_callee_name(callee)

            if caller and callee_name and caller != callee_name:
                if callee_name in self.function_map:
                    self.graph.add_edge(caller, callee_name)
                    edges.append({"from": caller, "to": callee_name})

        god_functions = []
        for node in self.graph.nodes():
            out_degree = self.graph.out_degree(node)
            if out_degree >= 8:
                god_functions.append({
                    "name": node,
                    "calls_count": out_degree,
                    "calls": list(self.graph.successors(node)),
                })

        orphan_functions = [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]

        return {
            "nodes": list(self.graph.nodes(data=True)),
            "edges": edges,
            "god_functions": god_functions,
            "orphan_functions": orphan_functions,
            "total_calls": len(edges),
        }

    def _find_enclosing_function(self, node, functions: List[Dict]) -> Optional[str]:
        """Find which function contains this call expression."""
        node_dict = _to_dict_safe(node)
        node_loc = node_dict.get("loc")
        if not node_loc:
            return None
        loc_dict = _to_dict_safe(node_loc)
        start = _to_dict_safe(loc_dict.get("start"))
        node_start = _get_attr(start, "line", 0)

        best_match = None
        for func in functions:
            floc = func.get("loc")
            if floc:
                f_start = floc.get("start", {}).get("line", 0)
                f_end = floc.get("end", {}).get("line", 999999)
                if f_start <= node_start <= f_end:
                    best_match = func.get("name", "<anonymous>")
        return best_match

    def _resolve_callee_name(self, callee: Any) -> Optional[str]:
        """Resolve callee to a function name."""
        callee_dict = _to_dict_safe(callee)
        if not callee_dict:
            return None
        if callee_dict.get("type") == "Identifier":
            return callee_dict.get("name")
        elif callee_dict.get("type") == "MemberExpression":
            obj = get_identifier_name(callee_dict.get("object"))
            prop = get_identifier_name(callee_dict.get("property"))
            if obj and prop:
                return f"{obj}.{prop}"
            return prop
        return None
