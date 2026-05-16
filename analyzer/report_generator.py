"""Generates rich Markdown report for architecture analysis."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class ReportGenerator:
    def generate(self, 
                 module_info: Dict,
                 state: List[Dict],
                 function_groups: Dict[str, List],
                 entry_points: List,
                 filename: str,
                 functions_raw: List[Dict] = None) -> Dict:   # добавили
        
        report = {
            "metadata": {
                "file": filename,
                "generated_at": datetime.now().isoformat(),
                "total_functions": sum(len(funcs) for funcs in function_groups.values()),
                "total_mutable_vars": len(state)
            },
            "markdown": self._generate_markdown(
                module_info, state, function_groups, entry_points, filename, functions_raw
            )
        }
        return report

    def _generate_markdown(self, module_info, state, function_groups, entry_points, filename, functions_raw=None) -> str:
        md = []
        md.append(f"# JS Architecture Analysis: `{filename}`\n")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        # ==================== MODULE SYSTEM ====================
        md.append("## Module System\n")
        md.append(f"- **Type**: {module_info.get('system', 'Unknown')}")
        md.append(f"- **Bundler**: {module_info.get('bundler', '—')}")
        md.append(f"- **ES6 Imports**: {'Yes' if module_info.get('es6') else 'No'}")
        md.append(f"- **CommonJS/UMD**: {'Yes' if module_info.get('commonjs') else 'No'}")
        md.append("")

        # ==================== GLOBAL STATE ====================
        md.append("## Global State & Data Structures\n")
        md.append("| Variable | Type | Mutations | Global | Description |")
        md.append("|----------|------|-----------|--------|-------------|")
        for item in state[:12]:
            global_mark = "✅" if item.get("is_global") else ""
            desc = self._generate_var_description(item)
            md.append(f"| `{item['name']}` | {item['inferred_type']} | **{item['mutation_count']}** | {global_mark} | {desc} |")
        md.append("")

        # ==================== FUNCTION GROUPS ====================
        md.append("## Function Groups\n")
        for group_name, funcs in function_groups.items():
            if not funcs:
                continue
            md.append(f"### {group_name} ({len(funcs)} functions)\n")
            
            for f in funcs[:10]:   # лимит
                name = f.get("name", "<anonymous>")
                params = f.get("params", [])
                param_str = f"({', '.join(params)})" if params else "()"
                async_mark = "async " if f.get("async") else ""
                
                md.append(f"- `{async_mark}{name}{param_str}`")
            if len(funcs) > 10:
                md.append(f"- ... +{len(funcs)-10} more")
            md.append("")

        # ==================== ENTRY POINTS ====================
        if entry_points:
            md.append("## Entry Points & Lifecycle\n")
            for ep in entry_points[:8]:
                ep_type = ep.get("type", "")
                name = ep.get("name") or ep.get("event") or "—"
                md.append(f"- `{ep_type}` → `{name}`")
            md.append("")

        md.append("---\n")
        md.append("**Готов для рефакторинга:** Разделение на модули + облачная архитектура (secrets, auth layer, API client и т.д.).")

        return "\n".join(md)

    def _generate_var_description(self, item: Dict) -> str:
        """Генерирует короткое описание структуры данных"""
        name = item["name"].lower()
        t = item["inferred_type"]
        
        if "roof" in name or "item" in name or "list" in name:
            return "массив объектов"
        if "filter" in name:
            return "фильтры поиска"
        if "favorite" in name:
            return "избранное пользователя"
        if "map" in name or "instance" in t:
            return "экземпляр карты"
        if "count" in name:
            return "счётчик"
        if t == "object":
            return "конфигурация / состояние"
        return ""
    
    def save(self, report: Dict, output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(report["metadata"]["file"]).stem
        
        md_path = output_dir / f"{base_name}_analysis.md"
        md_path.write_text(report["markdown"], encoding="utf-8")
        
        print(f"✅ Отчёт сохранён → {md_path}")