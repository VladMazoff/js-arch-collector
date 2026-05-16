"""Entry point for JS Architecture Collector (v1.0)"""
import argparse
import io
import sys
from pathlib import Path
from rich.console import Console

from config import CONFIG
from utils.file_utils import collect_js_files, collect_html_files
from analyzer.esprima_parser import JsEsprimaParser
from analyzer.html_extractor import HtmlExtractor
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


def analyze_file(file_path: Path, html_files: list = None, mode: str = "normal") -> dict:
    """Analyze a single JS file."""
    parser = JsEsprimaParser()
    data = parser.parse_file(file_path)

    # Call graph
    cg_builder = CallGraphBuilder()
    call_graph = cg_builder.build_from_ast(parser.ast, data["functions"])

    # State detection
    state_detector = StateDetector()
    mutable_state = state_detector.find_mutable_state(data)

    # Function grouping
    grouper = FunctionGrouper()
    groups = grouper.group_functions(data["functions"], CONFIG)

    # Module detection
    module_detector = ModuleDetector()
    module_info = module_detector.analyze(data, file_path)

    # HTML analysis
    html_info = []
    if html_files:
        html_extractor = HtmlExtractor()
        for hf in html_files:
            html_info.append(html_extractor.extract(hf))

    # Data Flow Analysis
    data_flow_analyzer = DataFlowAnalyzer()
    data_flow = data_flow_analyzer.analyze(data, data["functions"])

    # Generate report
    report_gen = ReportGenerator()
    report = report_gen.generate(
        module_info=module_info,
        state=mutable_state,
        function_groups=groups,
        entry_points=data["entry_points"],
        call_graph=call_graph,
        filename=file_path.name,
        html_info=html_info,
        functions_raw=data["functions"],
        mode=mode,
        data_flow=data_flow,
    )

    return report


def analyze_directory(dir_path: Path, html_files: list = None, mode: str = "normal") -> dict:
    """Analyze all JS files in a directory and aggregate results."""
    js_files = collect_js_files(dir_path)
    if not js_files:
        console.print(f"[red]No .js files found in {dir_path}[/red]")
        return {}

    console.print(f"[cyan]Found {len(js_files)} JS file(s) to analyze[/cyan]")

    all_functions = []
    all_globals = []
    all_assignments = []
    all_imports = []
    all_entry_points = []
    all_module_info = []
    all_call_graphs = []

    for js_file in js_files:
        console.print(f"  [dim]→ {js_file.relative_to(dir_path)}[/dim]")
        parser = JsEsprimaParser()
        data = parser.parse_file(js_file)

        all_functions.extend([{**f, "file": js_file.name} for f in data["functions"]])
        all_globals.extend([{**g, "file": js_file.name} for g in data["globals"]])
        all_assignments.extend([{**a, "file": js_file.name} for a in data["assignments"]])
        all_imports.extend([{**i, "file": js_file.name} for i in data["imports"]])
        all_entry_points.extend([{**e, "file": js_file.name} for e in data["entry_points"]])

        cg_builder = CallGraphBuilder()
        cg = cg_builder.build_from_ast(parser.ast, data["functions"])
        all_call_graphs.append(cg)

        module_detector = ModuleDetector()
        mod_info = module_detector.analyze(data, js_file)
        all_module_info.append(mod_info)

    aggregated_data = {
        "file": str(dir_path),
        "functions": all_functions,
        "globals": all_globals,
        "assignments": all_assignments,
        "imports": all_imports,
        "entry_points": all_entry_points,
    }

    state_detector = StateDetector()
    mutable_state = state_detector.find_mutable_state(aggregated_data)

    grouper = FunctionGrouper()
    groups = grouper.group_functions(all_functions, CONFIG)

    merged_cg = {
        "nodes": [],
        "edges": [],
        "god_functions": [],
        "orphan_functions": [],
        "total_calls": 0,
    }
    for cg in all_call_graphs:
        merged_cg["nodes"].extend(cg.get("nodes", []))
        merged_cg["edges"].extend(cg.get("edges", []))
        merged_cg["god_functions"].extend(cg.get("god_functions", []))
        merged_cg["total_calls"] += cg.get("total_calls", 0)

    all_orphans = set()
    for cg in all_call_graphs:
        all_orphans.update(cg.get("orphan_functions", []))
    merged_cg["orphan_functions"] = sorted(list(all_orphans))

    html_info = []
    if html_files:
        html_extractor = HtmlExtractor()
        for hf in html_files:
            html_info.append(html_extractor.extract(hf))

    module_systems = [m["module_system"] for m in all_module_info]
    dominant = max(set(module_systems), key=module_systems.count) if module_systems else "Unknown"
    has_commonjs = any(m["has_commonjs"] for m in all_module_info)
    has_es6 = any(m["has_es6"] for m in all_module_info)
    has_iife = any(m["has_iife"] for m in all_module_info)

    all_global_objs = []
    for m in all_module_info:
        all_global_objs.extend(m.get("global_objects", []))

    aggregated_module = {
        "file": str(dir_path),
        "module_system": dominant,
        "bundler": {"detected": [], "traces": {}},
        "global_objects": all_global_objs,
        "import_count": len(all_imports),
        "export_count": sum(m.get("export_count", 0) for m in all_module_info),
        "has_commonjs": has_commonjs,
        "has_es6": has_es6,
        "has_iife": has_iife,
    }

    # Data Flow Analysis (simplified for directory)
    data_flow_analyzer = DataFlowAnalyzer()
    data_flow = data_flow_analyzer.analyze(aggregated_data, all_functions)

    report_gen = ReportGenerator()
    report = report_gen.generate(
        module_info=aggregated_module,
        state=mutable_state,
        function_groups=groups,
        entry_points=all_entry_points,
        call_graph=merged_cg,
        filename=dir_path.name,
        html_info=html_info,
        functions_raw=all_functions,
        mode=mode,
        data_flow=data_flow,
    )

    return report


def main():
    parser = argparse.ArgumentParser(description="JS Architecture Collector")
    parser.add_argument("--file", type=str, help="Single JS file to analyze")
    parser.add_argument("--dir", type=str, help="Directory with JS files to analyze")
    parser.add_argument("--html", type=str, help="HTML file(s) to analyze (comma-separated)")
    parser.add_argument("--output", type=str, default=str(CONFIG["output_dir"]), help="Output directory")
    parser.add_argument("--mode", type=str, choices=["normal", "extended"], default="normal",
                        help="Report mode: normal (compact) or extended (LLM architect)")
    args = parser.parse_args()

    if not args.file and not args.dir:
        console.print("[red]Error: specify --file or --dir[/red]")
        parser.print_help()
        return

    html_files = []
    if args.html:
        for hf in args.html.split(","):
            p = Path(hf.strip())
            if p.exists():
                html_files.append(p)
            else:
                console.print(f"[yellow]Warning: HTML file not found: {p}[/yellow]")

    if args.file:
        path = Path(args.file)
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            return
        console.print(f"[cyan]Analyzing file: {path.name}[/cyan]")
        report = analyze_file(path, html_files, mode=args.mode)
    else:
        path = Path(args.dir)
        if not path.exists():
            console.print(f"[red]Directory not found: {path}[/red]")
            return
        console.print(f"[cyan]Analyzing directory: {path}[/cyan]")
        report = analyze_directory(path, html_files, mode=args.mode)

    report_gen = ReportGenerator()
    report_gen.print_summary(report)

    output_dir = Path(args.output)
    report_gen.save(report, output_dir)

    console.print("[green]Done![/green]")


if __name__ == "__main__":
    main()
