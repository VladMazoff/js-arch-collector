"""Group functions by semantic prefixes and patterns."""
from typing import Dict, List, Any
from collections import defaultdict
from config import CONFIG


class FunctionGrouper:
    """Clusters functions into semantic groups."""

    # Keywords that indicate side effects / non-pure functions
    SIDE_EFFECT_KEYWORDS = {
        "init", "bind", "handle", "render", "load", "fetch", "schedule",
        "apply", "toggle", "reset", "open", "close", "update", "show", "hide",
        "create", "destroy", "remove", "add", "set", "get", "on", "emit",
        "start", "boot", "setup", "run", "launch", "prepare", "main",
        "draw", "plot", "display", "refresh", "reload", "save", "delete",
        "insert", "append", "prepend", "attach", "detach", "mount", "unmount",
        "send", "post", "put", "patch", "delete", "upload", "download",
        "connect", "disconnect", "subscribe", "unsubscribe", "register", "unregister",
        "enable", "disable", "activate", "deactivate", "lock", "unlock",
        "expand", "collapse", "scroll", "resize", "drag", "drop", "sort",
        "filter", "search", "find", "match", "replace", "split", "join",
        "animate", "transition", "fade", "slide", "zoom", "pan", "rotate",
        "fly", "move", "center", "fit", "focus", "blur", "select", "deselect",
        "check", "uncheck", "validate", "submit", "cancel", "abort", "retry",
        "pause", "resume", "stop", "play", "record", "capture", "release",
    }

    def group_functions(self, functions: List[Dict], config: Dict = None) -> Dict[str, List[Dict]]:
        if config is None:
            config = CONFIG

        groups = defaultdict(list)
        prefixes = config.get("group_prefixes", {})

        for func in functions:
            name = func.get("name", "")
            assigned = False

            # First: explicit prefix matching
            for group_name, group_prefixes in prefixes.items():
                for prefix in group_prefixes:
                    if name.lower().startswith(prefix.lower()):
                        groups[group_name].append(func)
                        assigned = True
                        break
                if assigned:
                    break

            if not assigned:
                # Second: check if function has side effects by name
                base_name = name.lower().replace("_", "").replace("-", "")
                has_side_effects = any(kw in base_name for kw in self.SIDE_EFFECT_KEYWORDS)

                if has_side_effects:
                    # Try to categorize by side effect type
                    if any(kw in base_name for kw in ["init", "boot", "setup", "start", "run", "launch", "prepare", "main"]):
                        groups["Init/Boot"].append(func)
                    elif any(kw in base_name for kw in ["bind", "handle", "click", "toggle", "render", "update", "show", "hide", "open", "close", "reset"]):
                        groups["UI/Events"].append(func)
                    elif any(kw in base_name for kw in ["fetch", "load", "api", "schedule", "recalc", "export", "process", "get", "post", "save", "send", "download", "upload"]):
                        groups["Data/API"].append(func)
                    elif any(kw in base_name for kw in ["map", "geo", "layer", "marker", "chunk", "loc", "filter", "flyto", "zoom", "pan", "center", "fit"]):
                        groups["Map/Geo"].append(func)
                    elif any(kw in base_name for kw in ["auth", "login", "logout", "token", "encrypt", "decrypt", "hash", "verify", "secure", "check"]):
                        groups["Auth/Security"].append(func)
                    else:
                        groups["Others"].append(func)
                else:
                    # Likely pure / utility
                    if any(kw in base_name for kw in ["format", "parse", "validate", "clone", "merge", "debounce", "throttle", "stringify", "helper", "util"]):
                        groups["Utils"].append(func)
                    else:
                        groups["Others"].append(func)

        return dict(groups)
