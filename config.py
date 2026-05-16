from pathlib import Path

BASE_DIR = Path(__file__).parent

CONFIG = {
    "min_function_length": 3,
    "top_state_limit": 15,                   
    "state_mutation_threshold": 2,            # можно использовать позже    
    "group_prefixes": {
        "UI/Events": ["bind", "handle", "click", "open", "close", "render", "toggle", "initSlider", "updateUI", "show", "hide"],
        "Map/Geo": ["map", "geo", "layer", "marker", "chunk", "loc", "filter", "flyTo", "zoom", "pan"],
        "Data/API": ["fetch", "load", "api", "schedule", "recalc", "export", "process", "get", "post", "save", "send"],
        "Init/Boot": ["init", "boot", "setup", "start", "main", "run", "launch", "prepare"],
        "Utils": ["utils", "helper", "format", "validate", "debounce", "throttle", "parse", "stringify", "clone", "merge"],
        "Auth/Security": ["auth", "login", "logout", "token", "encrypt", "decrypt", "hash", "verify", "secure", "check"],
    },
    "output_dir": BASE_DIR / "output",
    "exclude_dirs": ["node_modules", "dist", "build", ".git", "vendor", "__pycache__", ".venv"],
    "exclude_files": ["*.min.js", "*.bundle.js", "*.map"],
    "top_state_limit": 15,
    "top_callers_limit": 10,
}
