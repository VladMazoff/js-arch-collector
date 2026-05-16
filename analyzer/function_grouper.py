"""Group functions by semantic prefixes and patterns."""
from typing import Dict, List
from collections import defaultdict
from config import CONFIG


class FunctionGrouper:
    """Clusters functions into semantic groups."""

    def __init__(self):
        # Более гибкие правила
        self.group_rules = {
            "UI/Events": [
                "bind", "toggle", "reset", "favorite", "render", "update", "show", 
                "hide", "open", "close", "callback", "handle", "click"
            ],
            "Map/Geo": [
                "map", "loc", "chunk", "geo", "layer", "marker", "filter", "apply", "clientfilter"
            ],
            "Data/API": [
                "load", "schedule", "fetch", "recalc", "export", "process", "api", "save"
            ],
            "Init/Boot": [
                "init", "boot", "setup", "start", "main", "module", "iife"
            ],
            "Utils": [
                "debounce", "throttle", "getstate", "format", "parse", "validate", "helper"
            ],
        }



    def group_functions(self, functions: List[Dict], config=None) -> Dict[str, List[Dict]]:
        groups = defaultdict(list)

        for func in functions:
            name_lower = func.get("name", "").lower()
            if not name_lower:
                groups["Others"].append(func)
                continue

            if "getstate" in name_lower or "get_state" in name_lower:
                groups["Utils"].append(func)
                continue

            assigned = False

            # 1. Проверка по правилам групп (contains, а не только startswith)
            for group_name, keywords in self.group_rules.items():
                if any(kw in name_lower for kw in keywords):
                    groups[group_name].append(func)
                    assigned = True
                    break

            # 2. Специальные кейсы
            if not assigned:
                if "filter" in name_lower:
                    groups["Map/Geo"].append(func)
                elif any(x in name_lower for x in ["on", "handler", "event"]):
                    groups["UI/Events"].append(func)
                elif name_lower.startswith("get") or name_lower.startswith("set"):
                    groups["Utils"].append(func)   # или Data, по вкусу
                else:
                    groups["Others"].append(func)

        # Сортируем группы по размеру (самые большие сверху)
        sorted_groups = dict(sorted(groups.items(), key=lambda x: len(x[1]), reverse=True))
        
        return sorted_groups