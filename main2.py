"""Entry point for JS Architecture Collector (v0.1)"""
import argparse
from pathlib import Path
from rich.console import Console
from datetime import datetime

from config import CONFIG
from utils.file_utils import collect_js_files  # создадим позже, если нужно
from analyzer.esprima_parser import JsEsprimaParser
from analyzer.state_detector import StateDetector
from analyzer.function_grouper import FunctionGrouper
from analyzer.module_detector import ModuleDetector
from analyzer.report_generator import ReportGenerator
import io
import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')




console = Console()


def analyze_single_file(file_path: Path) -> dict:
    """Анализ одного JS-файла"""
    console.print(f"[cyan]Анализируем файл:[/] {file_path.name}")

    parser = JsEsprimaParser()
    data = parser.parse_file(file_path)

    # State
    state_detector = StateDetector()
    mutable_state = state_detector.find_mutable_state(data)

    # Groups
    grouper = FunctionGrouper()
    groups = grouper.group_functions(data["functions"])

    # Module info
    module_detector = ModuleDetector()
    module_info = module_detector.analyze(data, file_path)

    # Report
    report_gen = ReportGenerator()
    report = report_gen.generate(
        module_info=module_info,
        state=mutable_state,
        function_groups=groups,
        entry_points=data.get("entry_points", []),
        filename=file_path.name,
        functions_raw=data["functions"]        # ← добавь

    )

    return report


def analyze_directory(dir_path: Path) -> dict:
    """Анализ всей папки (агрегация)"""
    js_files = collect_js_files(dir_path)
    if not js_files:
        console.print(f"[red]Не найдено .js файлов в {dir_path}[/]")
        return {}

    console.print(f"[cyan]Найдено {len(js_files)} JS-файлов[/]")

    all_functions = []
    all_globals = []
    all_assignments = []

    for js_file in js_files:
        console.print(f"  [dim]→ {js_file.name}[/]")
        parser = JsEsprimaParser()
        data = parser.parse_file(js_file)

        all_functions.extend([{**f, "file": js_file.name} for f in data.get("functions", [])])
        all_globals.extend([{**g, "file": js_file.name} for g in data.get("globals", [])])
        all_assignments.extend([{**a, "file": js_file.name} for a in data.get("assignments", [])])

    # Агрегированный анализ
    aggregated = {
        "functions": all_functions,
        "globals": all_globals,
        "assignments": all_assignments,
    }

    state_detector = StateDetector()
    mutable_state = state_detector.find_mutable_state(aggregated)

    grouper = FunctionGrouper()
    groups = grouper.group_functions(all_functions)

    module_detector = ModuleDetector()
    # Берём информацию из первого файла как доминирующую
    module_info = module_detector.analyze(parser.parse_file(js_files[0]), js_files[0]) if js_files else {}

    report_gen = ReportGenerator()
    report = report_gen.generate(
        module_info=module_info,
        state=mutable_state,
        function_groups=groups,
        entry_points=[],
        filename=f"{dir_path.name} (directory)",
        functions_raw=data["functions"]        # ← добавь

    )

    return report


def main():
    parser = argparse.ArgumentParser(description="JS Architecture Collector для LLM")
    parser.add_argument("--file", type=str, help="Путь к одному JS-файлу")
    parser.add_argument("--dir", type=str, help="Папка с JS-файлами")
    parser.add_argument("--output", type=str, default=None, help="Папка для сохранения отчётов")

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
        report = analyze_single_file(path)

    else:
        path = Path(args.dir)
        if not path.exists() or not path.is_dir():
            console.print(f"[red]Папка не найдена: {path}[/]")
            return
        report = analyze_directory(path)

    # Вывод и сохранение
    report_gen = ReportGenerator()
    console.print("\n" + "="*60)
    console.print(report["markdown"])   # или report_gen.print_summary(report)
    console.print("="*60)

    report_gen.save(report, output_dir)
    console.print(f"[green]✅ Анализ завершён! Отчёт сохранён в {output_dir}[/]")


if __name__ == "__main__":
    main()