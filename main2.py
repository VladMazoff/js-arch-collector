"""Entry point for JS Architecture Collector — DEBUG / TEST version"""
import argparse
import io
import sys
from pathlib import Path
from rich.console import Console

from config import CONFIG
from utils.file_utils import collect_js_files
from analyzer.esprima_parser import JsEsprimaParser
from analyzer.call_graph import CallGraphBuilder
from analyzer.state_detector import StateDetector
from analyzer.function_grouper import FunctionGrouper
from analyzer.module_detector import ModuleDetector
from analyzer.report_generator import ReportGenerator
from analyzer.data_flow import DataFlowAnalyzer

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

console = Console()


def analyze_single_file(file_path: Path, debug_call_graph: bool = True) -> dict:
    """Упрощённый анализ одного файла с дебаг-выводом"""
    console.print(f"[cyan]Анализируем файл:[/] {file_path.name}")

    parser = JsEsprimaParser()
    data = parser.parse_file(file_path)

    # DEBUG: вывод сырых данных
    console.print(f"[dim]  Functions found: {len(data.get('functions', []))}[/]")
    console.print(f"[dim]  Globals found: {len(data.get('globals', []))}[/]")
    console.print(f"[dim]  Assignments found: {len(data.get('assignments', []))}[/]")
    console.print(f"[dim]  Entry points: {len(data.get('entry_points', []))}[/]")
    console.print(f"[dim]  IIFE count: {data.get('iife_count', 0)}[/]")

    for ep in data.get("entry_points", []):
        console.print(f"[dim]    → {ep}[/]")

    # DEBUG: raw assignments
    console.print("[dim]  Raw assignments:[/]")
    for a in data.get("assignments", [])[:10]:
        console.print(f"[dim]    → target={a.get('target')}, op={a.get('operator')}, type={a.get('type', a.get('right_type'))}[/]")

    # Call Graph with DEBUG
    console.print("[cyan]  Building Call Graph...[/]")
    cg_builder = CallGraphBuilder()
    call_graph = cg_builder.build_from_ast(parser.ast, data["functions"], debug=debug_call_graph)
    console.print(f"[dim]  Call Graph edges: {call_graph.get('total_calls', 0)}[/]")
    if call_graph.get("edges"):
        for edge in call_graph["edges"][:5]:
            console.print(f"[dim]    → {edge['from']} -> {edge['to']}[/]")

    # State
    state_detector = StateDetector()
    mutable_state = state_detector.find_mutable_state(data)
    console.print(f"[dim]  Mutable state items: {len(mutable_state)}[/]")
    for s in mutable_state[:5]:
        console.print(f"[dim]    → {s['name']}: {s['mutation_count']} mutations[/]")

    # Groups
    grouper = FunctionGrouper()
    groups = grouper.group_functions(data["functions"])
    console.print(f"[dim]  Function groups: {list(groups.keys())}[/]")

    # Module info
    module_detector = ModuleDetector()
    module_info = module_detector.analyze(data, file_path)
    console.print(f"[dim]  Module system: {module_info.get('module_system', '?')}[/]")
    console.print(f"[dim]  CommonJS: {module_info.get('has_commonjs', '?')}[/]")
    console.print(f"[dim]  ES6: {module_info.get('has_es6', '?')}[/]")
    console.print(f"[dim]  IIFE: {module_info.get('has_iife', '?')}[/]")

    # Report
    report_gen = ReportGenerator()
    report = report_gen.generate(
        module_info=module_info,
        state=mutable_state,
        function_groups=groups,
        entry_points=data.get("entry_points", []),
        filename=file_path.name,
        functions_raw=data["functions"],
        call_graph=call_graph,  # ← добавлено
    )

    return report


def main():
    parser = argparse.ArgumentParser(description="JS Architecture Collector DEBUG")
    parser.add_argument("--file", type=str, help="Путь к одному JS-файлу")
    parser.add_argument("--dir", type=str, help="Папка с JS-файлами")
    parser.add_argument("--output", type=str, default=None, help="Папка для сохранения отчётов")
    parser.add_argument("--debug-cg", action="store_true", help="Debug call graph building")
    args = parser.parse_args()

    if not args.file and not args.dir:
        console.print("[red]Ошибка: укажите --file или --dir[/red]")
        parser.print_help()
        return

    output_dir = Path(args.output) if args.output else CONFIG["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        path = Path(args.file)
        if not path.exists():
            console.print(f"[red]Файл не найден: {path}[/]")
            return
        report = analyze_single_file(path, debug_call_graph=args.debug_cg)
    else:
        path = Path(args.dir)
        if not path.exists() or not path.is_dir():
            console.print(f"[red]Папка не найдена: {path}[/]")
            return
        js_files = collect_js_files(path)
        console.print(f"[cyan]Найдено {len(js_files)} JS-файлов[/]")
        if js_files:
            report = analyze_single_file(js_files[0], debug_call_graph=args.debug_cg)
        else:
            return

    console.print("\n" + "="*60)
    console.print(report.get("markdown", "[no markdown]"))
    console.print("="*60)

    report_gen = ReportGenerator()
    report_gen.save(report, output_dir)
    console.print(f"[green]✅ Отчёт сохранён в {output_dir}[/]")


if __name__ == "__main__":
    main()
