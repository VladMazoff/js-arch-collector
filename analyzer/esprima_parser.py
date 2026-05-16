"""ESPrima-based JavaScript AST parser and extractor."""
import esprima
from pathlib import Path
from typing import Dict, List, Any, Optional
from utils.ast_helpers import find_nodes, get_node_loc, get_identifier_name


def _get_attr(obj, attr, default=None):
    """Safely get attribute from esprima object or dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _to_dict_safe(obj):
    """Convert esprima object to dict if needed."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    # Try to get __dict__ or convert
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    return obj


class JsEsprimaParser:
    """Parse JS files and extract structural information."""

    def __init__(self):
        self.ast = None
        self.source = None
        self.source_lines = []

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        self.source = file_path.read_text(encoding="utf-8")
        self.source_lines = self.source.split("\n")
        self.ast = esprima.parseScript(self.source, loc=True, range=True, tolerant=True)
        return self.extract_all(str(file_path))

    def parse_string(self, code: str, filename: str = "<inline>") -> Dict[str, Any]:
        self.source = code
        self.source_lines = self.source.split("\n")
        self.ast = esprima.parseScript(code, loc=True, range=True, tolerant=True)
        return self.extract_all(filename)

    def extract_all(self, filename: str) -> Dict[str, Any]:
        return {
            "file": filename,
            "source": self.source,
            "globals": self._extract_globals(),
            "functions": self._extract_functions(),
            "imports": self._extract_imports(),
            "assignments": self._extract_assignments(),
            "entry_points": self._find_entry_points(),
            "classes": self._extract_classes(),
            "iife_count": self._count_iife(),
        }

    def _extract_globals(self) -> List[Dict]:
        globals_list = []
        body = self.ast.body if hasattr(self.ast, "body") else []

        for node in body:
            if _get_attr(node, "type") == "VariableDeclaration":
                declarations = _get_attr(node, "declarations", [])
                for decl in declarations:
                    name = get_identifier_name(_get_attr(decl, "id"))
                    if name:
                        init = _get_attr(decl, "init")
                        init_type = _get_attr(init, "type") if init else None
                        globals_list.append({
                            "name": name,
                            "kind": _get_attr(node, "kind"),
                            "init_type": init_type,
                            "loc": get_node_loc(_to_dict_safe(decl)),
                        })
        return globals_list

    def _extract_functions(self) -> List[Dict]:
        functions = []
        func_nodes = find_nodes(self.ast.__dict__, "FunctionDeclaration")
        func_nodes += find_nodes(self.ast.__dict__, "FunctionExpression")
        func_nodes += find_nodes(self.ast.__dict__, "ArrowFunctionExpression")

        for node in func_nodes:
            node_dict = _to_dict_safe(node)
            node_type = node_dict.get("type")
            name = None

            if node_type == "FunctionDeclaration":
                nid = node_dict.get("id")
                name = _get_attr(nid, "name") if nid else None
            elif node_type == "FunctionExpression":
                nid = node_dict.get("id")
                name = _get_attr(nid, "name") if nid else None
                if not name:
                    name = self._get_assigned_name(node)
            elif node_type == "ArrowFunctionExpression":
                name = self._get_assigned_name(node)

            params = []
            for p in node_dict.get("params", []):
                pname = get_identifier_name(p)
                if pname:
                    params.append(pname)

            functions.append({
                "name": name or "<anonymous>",
                "type": node_type,
                "params": params,
                "loc": get_node_loc(node_dict),
                "async": node_dict.get("async", False),
                "generator": node_dict.get("generator", False),
            })
        return functions

    def _get_assigned_name(self, node) -> Optional[str]:
        """Find the variable name a function expression/arrow is assigned to."""
        assignments = find_nodes(self.ast.__dict__, "VariableDeclarator")
        for decl in assignments:
            decl_dict = _to_dict_safe(decl)
            if decl_dict.get("init") is node:
                return get_identifier_name(decl_dict.get("id"))
        assigns = find_nodes(self.ast.__dict__, "AssignmentExpression")
        for a in assigns:
            a_dict = _to_dict_safe(a)
            if a_dict.get("right") is node:
                return get_identifier_name(a_dict.get("left"))
        return None

    def _extract_imports(self) -> List[Dict]:
        imports = []
        for node in self.ast.body:
            node_type = _get_attr(node, "type")
            if node_type == "ImportDeclaration":
                source = _get_attr(node, "source")
                specifiers = _get_attr(node, "specifiers", [])
                imports.append({
                    "type": "ES6",
                    "source": _get_attr(source, "value"),
                    "specifiers": [_get_attr(s, "local", {}).get("name") if hasattr(_get_attr(s, "local"), "name") else _get_attr(_get_attr(s, "local", {}), "name") for s in specifiers],
                    "loc": get_node_loc(_to_dict_safe(node)),
                })
            elif node_type == "ExpressionStatement":
                expr = _get_attr(node, "expression")
                if _get_attr(expr, "type") == "CallExpression":
                    callee = _get_attr(expr, "callee")
                    if _get_attr(callee, "type") == "Identifier" and _get_attr(callee, "name") == "require":
                        args = _get_attr(expr, "arguments", [])
                        if args and _get_attr(args[0], "type") == "Literal":
                            imports.append({
                                "type": "CommonJS",
                                "source": _get_attr(args[0], "value"),
                                "specifiers": [],
                                "loc": get_node_loc(_to_dict_safe(node)),
                            })
        return imports

    def _extract_assignments(self) -> List[Dict]:
        assignments = []
        assign_nodes = find_nodes(self.ast.__dict__, "AssignmentExpression")
        for node in assign_nodes:
            node_dict = _to_dict_safe(node)
            left_name = get_identifier_name(node_dict.get("left"))
            right = node_dict.get("right")
            right_type = _get_attr(right, "type") if right else None
            assignments.append({
                "target": left_name,
                "operator": node_dict.get("operator"),
                "right_type": right_type,
                "loc": get_node_loc(node_dict),
            })
        return assignments

    def _find_entry_points(self) -> List[Dict]:
        entries = []
        for node in self.ast.body:
            if _get_attr(node, "type") == "ExpressionStatement":
                expr = _get_attr(node, "expression")
                expr_type = _get_attr(expr, "type")
                if expr_type == "CallExpression":
                    callee = _get_attr(expr, "callee")
                    callee_type = _get_attr(callee, "type")
                    # IIFE
                    if callee_type in ("FunctionExpression", "ArrowFunctionExpression"):
                        cid = _get_attr(callee, "id")
                        name = _get_attr(cid, "name") if cid else "<IIFE>"
                        entries.append({
                            "type": "IIFE",
                            "name": name,
                            "loc": get_node_loc(_to_dict_safe(node)),
                        })
                    # window.addEventListener / document.addEventListener
                    elif callee_type == "MemberExpression":
                        obj_name = get_identifier_name(_get_attr(callee, "object"))
                        prop_name = get_identifier_name(_get_attr(callee, "property"))
                        if obj_name in ("window", "document", "globalThis") and prop_name == "addEventListener":
                            args = _get_attr(expr, "arguments", [])
                            event_name = _get_attr(args[0], "value") if args and _get_attr(args[0], "type") == "Literal" else "unknown"
                            entries.append({
                                "type": "event_listener",
                                "target": obj_name,
                                "event": event_name,
                                "loc": get_node_loc(_to_dict_safe(node)),
                            })
                # Direct call to init() or main() at top level
                elif expr_type == "CallExpression":
                    callee = _get_attr(expr, "callee")
                    if _get_attr(callee, "type") == "Identifier":
                        entries.append({
                            "type": "direct_call",
                            "name": _get_attr(callee, "name"),
                            "loc": get_node_loc(_to_dict_safe(node)),
                        })
        return entries

    def _extract_classes(self) -> List[Dict]:
        classes = []
        class_nodes = find_nodes(self.ast.__dict__, "ClassDeclaration")
        for node in class_nodes:
            node_dict = _to_dict_safe(node)
            nid = node_dict.get("id")
            name = _get_attr(nid, "name") if nid else "<anonymous>"
            methods = []
            body = _get_attr(_get_attr(node, "body", {}), "body", [])
            for m in body:
                m_dict = _to_dict_safe(m)
                if m_dict.get("type") == "MethodDefinition":
                    mkey = m_dict.get("key")
                    mname = _get_attr(mkey, "name") if mkey else None
                    methods.append({
                        "name": mname,
                        "kind": m_dict.get("kind", "method"),
                        "static": m_dict.get("static", False),
                    })
            classes.append({
                "name": name,
                "methods": methods,
                "loc": get_node_loc(node_dict),
            })
        return classes

    def _count_iife(self) -> int:
        count = 0
        for node in self.ast.body:
            if _get_attr(node, "type") == "ExpressionStatement":
                expr = _get_attr(node, "expression")
                if _get_attr(expr, "type") == "CallExpression":
                    callee = _get_attr(expr, "callee")
                    if _get_attr(callee, "type") in ("FunctionExpression", "ArrowFunctionExpression"):
                        count += 1
        return count
