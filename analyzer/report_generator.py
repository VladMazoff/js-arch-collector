"""Generate JSON and Markdown reports."""
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box


class ReportGenerator:
    """Generates structured reports from analysis data."""

    def __init__(self):
        self.console = Console()

    def generate(self, module_info: Dict, state: List[Dict], function_groups: Dict,
                 entry_points: List[Dict], filename: str,
                 call_graph: Dict = None, html_info: List = None,
                 functions_raw: List = None, mode: str = "normal",
                 data_flow: Dict = None) -> Dict[str, Any]:
        """Generate a complete report structure."""
        call_graph = call_graph or {}
        html_info = html_info or []
        functions_raw = functions_raw or []

        issues = self._build_issues(module_info, state, call_graph, functions_raw, entry_points)
        call_graph_md = self._build_call_graph_md(call_graph)

        report = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "filename": filename,
                "version": "1.0.0",
                "mode": mode,
            },
            "module_system": module_info,
            "key_state": state,
            "function_groups": {
                group: len(funcs) for group, funcs in function_groups.items()
            },
            "function_groups_detail": function_groups,
            "entry_points": entry_points,
            "call_graph": call_graph,
            "call_graph_markdown": call_graph_md,
            "architecture_issues": issues,
            "html_analysis": html_info,
            "data_flow": data_flow or {},
        }

        # Generate markdown based on mode
        if mode == "extended":
            report["markdown"] = self._generate_extended_md(report)
        else:
            report["markdown"] = self.generate_markdown(report)

        return report

    def _build_issues(self, module_info: Dict, state: List[Dict],
                      call_graph: Dict, functions_raw: List, entry_points: List) -> List[Dict]:
        """Detect architecture risks and anti-patterns."""
        issues = []

        for gf in call_graph.get("god_functions", []):
            issues.append({
                "severity": "high",
                "category": "complexity",
                "title": f"God Function: {gf['name']}",
                "description": f"Вызывает {gf['calls_count']} функций — слишком много ответственности.",
                "suggestion": "Разбейте на несколько функций или вынесите логику в модули.",
            })

        global_mutables = [s for s in state if s.get("is_global") and s["mutation_count"] >= 2]
        if len(global_mutables) >= 3:
            issues.append({
                "severity": "high",
                "category": "state",
                "title": "Слишком много глобального mutable state",
                "description": f"{len(global_mutables)} переменных мутируются в глобальной области.",
                "suggestion": "Вынесите state в отдельный модуль/Store (Redux/Pinia/Context).",
            })

        if module_info.get("module_system") == "Global (script tag)":
            issues.append({
                "severity": "medium",
                "category": "modules",
                "title": "Нет модульной системы",
                "description": "Код работает в глобальной области видимости.",
                "suggestion": "Перейдите на ES6 modules или CommonJS.",
            })

        for s in state:
            if "url" in s["name"].lower() or "api" in s["name"].lower() or "base" in s["name"].lower():
                issues.append({
                    "severity": "medium",
                    "category": "security",
                    "title": f"Возможный hardcoded URL: {s['name']}",
                    "description": "Проверьте, что URL не захардкожен в коде.",
                    "suggestion": "Вынесите в .env или config-файл.",
                })

        func_count = len(functions_raw)
        if func_count >= 15:
            issues.append({
                "severity": "medium",
                "category": "size",
                "title": f"Большой файл: {func_count} функций",
                "description": "Файл слишком большой для единственного модуля.",
                "suggestion": "Разделите на логические модули (UI, Map, API, Utils).",
            })

        if not entry_points:
            issues.append({
                "severity": "low",
                "category": "lifecycle",
                "title": "Не найдены точки входа",
                "description": "Не обнаружены init(), DOMContentLoaded, window.onload и т.д.",
                "suggestion": "Проверьте порядок загрузки скриптов.",
            })

        return issues

    def _build_call_graph_md(self, call_graph: Dict) -> str:
        """Build Mermaid-style call graph for markdown."""
        edges = call_graph.get("edges", [])
        if not edges:
            return "*Граф вызовов пуст — не удалось определить связи.*"

        lines = ["```mermaid", "graph TD"]
        seen = set()
        for edge in edges[:30]:
            src = edge["from"]
            dst = edge["to"]
            key = f"{src}-->{dst}"
            if key not in seen:
                lines.append(f"    {src}[{src}] --> {dst}[{dst}]")
                seen.add(key)
        lines.append("```")
        return "\n".join(lines)

    def _generate_extended_md(self, report: Dict) -> str:
        """Extended mode for LLM architect — detailed refactoring plan."""
        meta = report.get("meta", {})
        module = report.get("module_system", {})
        state = report.get("key_state", [])
        groups = report.get("function_groups_detail", {})
        entries = report.get("entry_points", [])
        call_graph = report.get("call_graph", {})
        issues = report.get("architecture_issues", [])
        data_flow = report.get("data_flow", {})

        lines = []
        lines.append("# JS Architecture Analysis — Extended Report")
        lines.append(f"**Файл:** `{meta.get('filename', 'N/A')}`")
        lines.append(f"**Дата анализа:** {meta.get('generated_at', 'N/A')}")
        lines.append(f"**Функций:** {sum(len(v) for v in groups.values())} | **Глобальных переменных:** {len([s for s in state if s.get('is_global')])}")
        lines.append("")

        # 1. Module System
        lines.append("## 1. Module System & Environment")
        lines.append(f"- **Current module system:** {module.get('module_system', 'N/A')}")
        lines.append(f"- **ES6 imports/exports:** {'Присутствуют' if module.get('has_es6') else 'Отсутствуют'}")
        lines.append(f"- **CommonJS:** {'Да' if module.get('has_commonjs') else 'Нет'}")
        global_objs = module.get("global_objects", [])
        if global_objs:
            lines.append(f"- **Global exposure:** {', '.join([g['name'] for g in global_objs[:3]])}")
        lines.append(f"- **Bundler:** {', '.join(module.get('bundler', {}).get('detected', ['Не обнаружен']))}")
        lines.append("")

        # 2. Mutable State with Data Flow
        lines.append("## 2. Mutable Global State & Data Flow")

        # Detailed state table with readers/writers
        lines.append("### State Details (Readers / Writers / Groups)")
        lines.append("| Переменная | Тип | Мутаций | Readers | Writers | Groups | Risk |")
        lines.append("|------------|-----|---------|---------|---------|--------|------|")
        df_details = data_flow.get("state_details", []) if data_flow else []
        for sd in df_details:
            readers = ", ".join(sd["readers"][:3]) + ("..." if len(sd["readers"]) > 3 else "")
            writers = ", ".join(sd["writers"][:3]) + ("..." if len(sd["writers"]) > 3 else "")
            groups_involved = ", ".join(sd["groups_involved"])
            lines.append(f"| `{sd['name']}` | {sd['type']} | {sd['mutations']} | {readers} | {writers} | {groups_involved} | {sd['risk_score']}/10 |")
        lines.append("")

        # Cross-group shared state
        cross_group = data_flow.get("cross_group_state", []) if data_flow else []
        if cross_group:
            lines.append("### ⚠️ Cross-Group Shared State")
            lines.append("| Переменная | Groups | Risk |")
            lines.append("|------------|--------|------|")
            for cg in cross_group:
                lines.append(f"| `{cg['variable']}` | {', '.join(cg['groups'])} | {cg['risk']} |")
            lines.append("")

        lines.append(f"**Shared mutable state:** {len(state)}")
        lines.append("")

        # Variable-Function Access Matrix
        matrix = data_flow.get("variable_function_matrix", {}) if data_flow else {}
        if matrix:
            lines.append("### State Access Matrix")
            all_funcs = sorted(list(next(iter(matrix.values())).keys())) if matrix else []
            all_vars = sorted(list(matrix.keys()))

            # Header
            header = "Variable \\ Function | " + " | ".join(all_funcs[:8]) + (" | ..." if len(all_funcs) > 8 else "")
            lines.append(header)
            lines.append("-" * len(header))

            # Rows
            for var in all_vars[:10]:  # limit rows
                row_vals = []
                for func in all_funcs[:8]:
                    val = matrix.get(var, {}).get(func, "")
                    row_vals.append(val if val else "·")
                lines.append(f"`{var}` | " + " | ".join(row_vals) + (" | ..." if len(all_funcs) > 8 else ""))
            lines.append("")

        # 3. Function Clusters
        lines.append("## 3. Function Clusters & Responsibilities")
        for group, funcs in groups.items():
            if funcs:
                lines.append(f"**{group}** ({len(funcs)})")
                names = [f"`{f['name']}`" for f in funcs]
                lines.append(f"- {', '.join(names[:8])}{' ...' if len(names) > 8 else ''}")
                lines.append("")

        # 4. Call Graph
        lines.append("## 4. Call Graph & Data Flow")
        cg_md = report.get("call_graph_markdown", "")
        lines.append(cg_md)
        lines.append("")

        # 5. Entry Points
        lines.append("## 5. Entry Points & Public API")
        for ep in entries:
            loc = ep.get("loc", {})
            line = f" (L{loc['start']['line']})" if loc and loc.get("start") else ""
            lines.append(f"- `{ep.get('name', ep.get('event', 'N/A'))}`{line}")
        lines.append("")

        # 6. Issues
        lines.append("## 6. Detected Issues & Anti-patterns")
        high = [i for i in issues if i["severity"] == "high"]
        med = [i for i in issues if i["severity"] == "medium"]
        low = [i for i in issues if i["severity"] == "low"]
        if high:
            lines.append("**High Risk:**")
            for i in high:
                lines.append(f"- {i['title']}: {i['description']}")
            lines.append("")
        if med:
            lines.append("**Medium Risk:**")
            for i in med:
                lines.append(f"- {i['title']}: {i['description']}")
            lines.append("")
        lines.append("")

        # 7. Refactoring Recommendations
        lines.append("## 7. Refactoring Recommendations")
        lines.append("### Предлагаемое разбиение на модули:")
        module_suggestions = {
            "state.js": ["selectedRoofs", "currentFilters", "userFavorites", "renderedCount"],
            "map.js": ["initMap", "applyLoc", "renderRoofsOnMap", "onChunk"],
            "api.js": ["scheduleLoad", "fetch"],
            "filters.js": ["clientFilter", "applyFilters", "resetFilters"],
            "ui/events.js": ["bindEvents", "toggleFavorite", "updateUI"],
            "core.js": ["init", "debouncedSearch"],
        }
        for mod_name, items in module_suggestions.items():
            lines.append(f"1. **{mod_name}** — {', '.join([f'`{i}`' for i in items[:4]])}")
        lines.append("")
        lines.append("**Сложность миграции:** Средняя")
        lines.append("")

        return "\n".join(lines)

    def generate_markdown(self, report: Dict) -> str:
        """Normal mode — compact overview."""
        meta = report.get("meta", {})
        module = report.get("module_system", {})
        state = report.get("key_state", [])
        groups = report.get("function_groups", {})
        groups_detail = report.get("function_groups_detail", {})
        entries = report.get("entry_points", [])
        call_graph = report.get("call_graph", {})
        issues = report.get("architecture_issues", [])
        html_info = report.get("html_analysis", [])

        lines = []
        lines.append("# JS Architecture Analysis")
        lines.append(f"**Файл:** `{meta.get('filename', 'N/A')}`")
        lines.append(f"**Анализ:** {meta.get('generated_at', 'N/A')}")
        total_funcs = sum(len(v) for v in groups_detail.values())
        total_globals = len([s for s in state if s.get("is_global")])
        lines.append(f"**Функций:** {total_funcs} | **Глобальных переменных:** {total_globals}")
        lines.append("")

        # Module System
        lines.append("## Module System")
        lines.append(f"- **Тип:** {module.get('module_system', 'N/A')}")
        lines.append(f"- **ES6 imports:** {'Да' if module.get('has_es6') else 'Нет'}")
        lines.append(f"- **CommonJS:** {'Да' if module.get('has_commonjs') else 'Нет'}")
        global_objs = module.get("global_objects", [])
        if global_objs:
            lines.append(f"- **Глобальные точки входа:** {', '.join([g['name'] for g in global_objs[:3]])}")
        lines.append("")

        # Mutable State
        lines.append("## Mutable Global State")
        lines.append("| Переменная | Тип | Мутаций | Риск |")
        lines.append("|------------|-----|---------|------|")
        for s in state:
            risk = "High" if s["mutation_count"] >= 3 else ("Medium" if s["mutation_count"] >= 2 else "Low")
            global_tag = " 🌍" if s.get("is_global") else ""
            lines.append(f"| `{s['name']}`{global_tag} | {s.get('inferred_type', '?')} | {s['mutation_count']} | {risk} |")
        lines.append(f"**Всего mutable state:** {len(state)}")
        lines.append("")

        # Function Groups
        lines.append("## Function Groups")
        if isinstance(groups, dict):
            for group, count in sorted(groups.items(), key=lambda x: -x[1]):
                lines.append(f"- **{group}** — {count} функций")
        else:
            lines.append(f"- **Error:** groups is {type(groups)}")
        lines.append("")

        # Entry Points
        lines.append("## Entry Points")
        for ep in entries:
            loc = ep.get("loc", {})
            line = f" (L{loc['start']['line']})" if loc and loc.get("start") else ""
            lines.append(f"- `{ep.get('name', ep.get('event', 'N/A'))}`{line}")
        lines.append("")

        # Call Graph
        lines.append("## Call Graph")
        cg_md = report.get("call_graph_markdown", "")
        lines.append(cg_md)
        lines.append("")

        # Issues
        if issues:
            high = sum(1 for i in issues if i["severity"] == "high")
            med = sum(1 for i in issues if i["severity"] == "medium")
            low = sum(1 for i in issues if i["severity"] == "low")
            lines.append(f"🔴 **High:** {high} | 🟡 **Medium:** {med} | 🟢 **Low:** {low}")
            lines.append("")
            lines.append("**Ключевые проблемы:**")
            for issue in issues[:5]:
                lines.append(f"- {issue['title']}: {issue['description']}")
            lines.append("")

        # HTML Analysis
        if html_info:
            lines.append("## HTML Analysis")
            for hi in html_info:
                lines.append(f"### {hi.get('file', 'N/A')}")
                lines.append(f"- Scripts found: {hi.get('script_count', 0)}")
                for script in hi.get("scripts", []):
                    if script.get("src"):
                        lines.append(f"  - External: `{script['src']}`")
                    elif script.get("inline"):
                        preview = script["inline"][:60].replace("\n", " ")
                        lines.append(f"  - Inline: `{preview}...`")
                lines.append("")

        return "\n".join(lines)

    def print_summary(self, report: Dict):
        """Print a rich console summary."""
        meta = report.get("meta", {})
        module = report.get("module_system", {})
        state = report.get("key_state", [])
        groups = report.get("function_groups", {})
        # DEBUG: check groups type
        if not isinstance(groups, dict):
            self.console.print(f"[red]DEBUG: groups is {type(groups)}: {repr(groups)[:100]}[/red]")
            groups = {}
        call_graph = report.get("call_graph", {})
        issues = report.get("architecture_issues", [])
        data_flow = report.get("data_flow", {})
        mode = meta.get("mode", "normal")

        title = "JS Architecture Analysis" if mode == "normal" else "JS Architecture Analysis — EXTENDED"
        self.console.print(Panel.fit(
            f"[bold cyan]{title}[/bold cyan]\n"
            f"[dim]{meta.get('filename', 'N/A')} — {meta.get('generated_at', 'N/A')} — mode: {mode}[/dim]",
            box=box.DOUBLE
        ))

        mod_table = Table(title="Module System", box=box.SIMPLE_HEAD)
        mod_table.add_column("Property", style="cyan")
        mod_table.add_column("Value", style="green")
        mod_table.add_row("System", module.get("module_system", "N/A"))
        mod_table.add_row("Bundler", ", ".join(module.get("bundler", {}).get("detected", ["none"])))
        mod_table.add_row("ES6 imports", str(module.get("has_es6", False)))
        mod_table.add_row("CommonJS", str(module.get("has_commonjs", False)))
        self.console.print(mod_table)

        state_table = Table(title=f"Top Mutable State ({len(state)})", box=box.SIMPLE_HEAD)
        state_table.add_column("Variable", style="yellow")
        state_table.add_column("Type", style="blue")
        state_table.add_column("Mutations", style="red")
        state_table.add_column("Global", style="magenta")
        for s in state[:10]:
            state_table.add_row(
                s["name"],
                s.get("inferred_type", "?"),
                str(s["mutation_count"]),
                "✓" if s.get("is_global") else ""
            )
        self.console.print(state_table)

        # EXTENDED: Data Flow details
        if mode == "extended":
            df_details = data_flow.get("state_details", [])
            if df_details:
                df_table = Table(title="Data Flow — State Details", box=box.SIMPLE_HEAD)
                df_table.add_column("Variable", style="yellow")
                df_table.add_column("Readers", style="cyan")
                df_table.add_column("Writers", style="red")
                df_table.add_column("Groups", style="magenta")
                df_table.add_column("Risk", style="bold red")
                for sd in df_details[:8]:
                    readers = ", ".join(sd["readers"][:2]) + ("..." if len(sd["readers"]) > 2 else "")
                    writers = ", ".join(sd["writers"][:2]) + ("..." if len(sd["writers"]) > 2 else "")
                    groups = ", ".join(sd["groups_involved"][:2])
                    df_table.add_row(sd["name"], readers, writers, groups, f"{sd['risk_score']}/10")
                self.console.print(df_table)

            cross = data_flow.get("cross_group_state", [])
            if cross:
                self.console.print(f"[bold yellow]⚠️ {len(cross)} cross-group shared variables[/bold yellow]")

        groups_table = Table(title="Function Groups", box=box.SIMPLE_HEAD)
        groups_table.add_column("Group", style="cyan")
        groups_table.add_column("Count", style="green")
        if isinstance(groups, dict):
            if groups:
                for group, count in sorted(groups.items(), key=lambda x: -x[1]):
                    groups_table.add_row(str(group), str(count))
            else:
                groups_table.add_row("[empty]", "0")
        else:
            groups_table.add_row("[error]", f"type={type(groups)} val={repr(groups)[:80]}")
        self.console.print(groups_table)

        # Call Graph in console
        edges = call_graph.get("edges", [])
        if edges:
            cg_table = Table(title="Call Graph (top 10)", box=box.SIMPLE_HEAD)
            cg_table.add_column("Caller", style="cyan")
            cg_table.add_column("→", style="dim")
            cg_table.add_column("Callee", style="green")
            seen = set()
            for edge in edges[:10]:
                key = f"{edge['from']}->{edge['to']}"
                if key not in seen:
                    cg_table.add_row(edge["from"], "→", edge["to"])
                    seen.add(key)
            self.console.print(cg_table)
        else:
            self.console.print("[dim]Call Graph: no edges found[/dim]")

        # Issues
        if issues:
            high = sum(1 for i in issues if i["severity"] == "high")
            med = sum(1 for i in issues if i["severity"] == "medium")
            low = sum(1 for i in issues if i["severity"] == "low")
            self.console.print(f"[bold red]🔴 {high} high[/bold red] | [bold yellow]🟡 {med} medium[/bold yellow] | [bold green]🟢 {low} low[/bold green] issues")

        god_funcs = call_graph.get("god_functions", [])
        if god_funcs:
            self.console.print(f"[bold red]⚠️ {len(god_funcs)} god function(s)[/bold red]")

    def save(self, report: Dict, output_dir: Path):
        """Save JSON and Markdown reports."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = report["meta"]["filename"].replace(".", "_")
        mode = report["meta"].get("mode", "normal")
        suffix = f"_{mode}" if mode != "normal" else ""

        # JSON
        json_path = output_dir / f"{base_name}{suffix}_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        # Markdown
        md_path = output_dir / f"{base_name}{suffix}_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.get("markdown", ""))

        self.console.print(f"[green]Reports saved:[/green]")
        self.console.print(f"  JSON: {json_path}")
        self.console.print(f"  MD:   {md_path}")
