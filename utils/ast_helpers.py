"""AST traversal and helper functions."""
from typing import Any, Dict, List, Optional


def _get_attr(obj: Any, attr: str, default=None):
    """Самый надёжный getter для esprima-python нод"""
    if obj is None:
        return default

    # 1. dict
    if isinstance(obj, dict):
        return obj.get(attr, default)

    # 2. Прямой getattr
    try:
        value = getattr(obj, attr, None)
        if value is not None:
            return value
    except:
        pass

    # 3. __dict__ (самый надёжный для esprima)
    try:
        if hasattr(obj, '__dict__'):
            return obj.__dict__.get(attr, default)
    except:
        pass

    # 4. Последний fallback
    try:
        return getattr(obj, attr, default)
    except:
        return default


def _to_dict_safe(obj: Any) -> Dict:
    """Полное безопасное преобразование в dict"""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj.copy()

    d = {}
    try:
        if hasattr(obj, '__dict__'):
            d.update(obj.__dict__)
        else:
            for key in dir(obj):
                if not key.startswith('__') and not callable(getattr(obj, key, None)):
                    val = _get_attr(obj, key)
                    if val is not None:
                        d[key] = val
    except:
        pass
    return d


def get_identifier_name(node: Any) -> Optional[str]:
    """Улучшенная версия с поддержкой MemberExpression"""
    if not node:
        return None

    node_type = _get_attr(node, "type")

    if node_type == "Identifier":
        return _get_attr(node, "name")
    elif node_type == "Literal":
        return str(_get_attr(node, "value", ""))
    elif node_type == "MemberExpression":
        obj = get_identifier_name(_get_attr(node, "object"))
        prop = get_identifier_name(_get_attr(node, "property"))
        computed = _get_attr(node, "computed", False)

        if computed:
            return f"{obj}[{prop}]" if obj and prop else prop
        return f"{obj}.{prop}" if obj and prop else (obj or prop)

    return None


def get_node_loc(node: Any) -> Dict:
    loc = _get_attr(node, "loc")
    if not loc:
        return {}
    start = _get_attr(loc, "start") or {}
    end = _get_attr(loc, "end") or {}
    return {
        "start": {"line": _get_attr(start, "line"), "column": _get_attr(start, "column")},
        "end":   {"line": _get_attr(end, "line"),   "column": _get_attr(end, "column")}
    }




def find_nodes2(node: Any, node_type: str, max_depth: int = 50) -> List[Any]:
    """Надёжный рекурсивный поиск нод по типу"""
    results: List[Any] = []
    
    def traverse(current: Any, depth: int = 0):
        if depth > max_depth or not current:
            return
        
        # === dict case ===
        if isinstance(current, dict):
            if current.get("type") == node_type:
                results.append(current)
            for value in current.values():
                if isinstance(value, (dict, list)):
                    traverse(value, depth + 1)
            return

        # === esprima object case ===
        try:
            curr_type = _get_attr(current, "type")
            if curr_type == node_type:
                results.append(current)

            # Основные поля, где могут быть дети
            for field in ("body", "declarations", "expression", "callee", "arguments", 
                         "left", "right", "object", "property", "init", "params", 
                         "elements", "properties", "consequent", "alternate", "block"):
                child = _get_attr(current, field)
                if child:
                    if isinstance(child, list):
                        for item in child:
                            traverse(item, depth + 1)
                    else:
                        traverse(child, depth + 1)
        except:
            pass

    traverse(node)
    return results


def find_nodes(ast_node: Any, node_type: str, _seen=None) -> List[Any]:
    """Recursively find all nodes of a given type in the AST."""
    if _seen is None:
        _seen = set()
    results = []
    if ast_node is None:
        return results
    node_id = id(ast_node)
    if node_id in _seen:
        return results
    _seen.add(node_id)
    if isinstance(ast_node, dict):
        if ast_node.get("type") == node_type:
            results.append(ast_node)
        for key, value in ast_node.items():
            if key in ("loc", "range"):
                continue
            results.extend(find_nodes(value, node_type, _seen))
    elif hasattr(ast_node, 'type'):
        if ast_node.type == node_type:
            results.append(ast_node)
        for key in dir(ast_node):
            if key.startswith('_') or key in ('loc', 'range'):
                continue
            try:
                value = getattr(ast_node, key)
                if not callable(value):
                    results.extend(find_nodes(value, node_type, _seen))
            except (AttributeError, TypeError):
                pass
    elif isinstance(ast_node, list):
        for item in ast_node:
            results.extend(find_nodes(item, node_type, _seen))
    return results
