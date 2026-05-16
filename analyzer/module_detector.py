"""Detect module system and bundler traces."""
from pathlib import Path
from typing import Dict, List, Any


class ModuleDetector:
    """Analyzes module system used in the JS file."""

    def analyze(self, ast_data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Detect module system, bundler traces, and global patterns."""
        imports = ast_data.get("imports", [])
        globals_list = ast_data.get("globals", [])
        assignments = ast_data.get("assignments", [])
        functions = ast_data.get("functions", [])
        source = ast_data.get("source", "")

        module_system = self._detect_module_system(imports, ast_data, source)
        bundler = self._detect_bundler(assignments, ast_data, source)
        global_objects = self._find_global_objects(globals_list, assignments)

        has_commonjs = any(i["type"] == "CommonJS" for i in imports) or "module.exports" in source or "require(" in source
        has_es6 = any(i["type"] == "ES6" for i in imports)
        has_iife = ast_data.get("iife_count", 0) > 0

        return {
            "file": str(file_path),
            "module_system": module_system,
            "bundler": bundler,
            "global_objects": global_objects,
            "import_count": len(imports),
            "export_count": self._count_exports(ast_data, source),
            "has_commonjs": has_commonjs,
            "has_es6": has_es6,
            "has_iife": has_iife,
        }

    def _detect_module_system(self, imports: List[Dict], ast_data: Dict, source: str) -> str:
        has_commonjs = any(i["type"] == "CommonJS" for i in imports) or "module.exports" in source or "require(" in source
        has_es6 = any(i["type"] == "ES6" for i in imports)
        has_iife = ast_data.get("iife_count", 0) > 0

        if "typeof define" in source and "define.amd" in source:
            return "AMD/UMD"
        if has_commonjs and has_iife:
            return "UMD"
        if has_commonjs:
            return "CommonJS"
        if has_es6:
            return "ES6 Modules"
        if has_iife:
            return "IIFE"
        return "Global (script tag)"

    def _detect_bundler(self, assignments: List[Dict], ast_data: Dict, source: str) -> Dict[str, Any]:
        traces = {}
        if "import.meta" in source:
            traces["vite"] = True
        if "__webpack" in source:
            traces["webpack"] = True
        if "__rollup" in source or "rollup" in source.lower():
            traces["rollup"] = True
        if "parcelRequire" in source:
            traces["parcel"] = True
        if "browserify" in source.lower():
            traces["browserify"] = True

        detected = [k for k, v in traces.items() if v]
        return {"detected": detected, "traces": traces}

    def _find_global_objects(self, globals_list: List[Dict], assignments: List[Dict]) -> List[Dict]:
        globals_found = []
        for assign in assignments:
            target = assign.get("target", "")
            if target and (target.startswith("window.") or target.startswith("globalThis.") or target.startswith("self.")):
                globals_found.append({"name": target, "loc": assign.get("loc")})
        return globals_found

    def _count_exports(self, ast_data: Dict, source: str) -> int:
        count = 0
        if "module.exports" in source:
            count += source.count("module.exports")
        if "exports." in source:
            count += source.count("exports.")
        if "export default" in source:
            count += 1
        if "export " in source:
            count += source.count("export ")
        return count
