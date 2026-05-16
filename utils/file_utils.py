"""File loading and path utilities."""
from pathlib import Path
from typing import List, Tuple
from config import CONFIG


def should_exclude(path: Path) -> bool:
    """Check if a file or directory should be excluded from analysis."""
    # Check directory names
    for part in path.parts:
        if part in CONFIG["exclude_dirs"]:
            return True
    # Check file patterns
    for pattern in CONFIG["exclude_files"]:
        if path.match(pattern):
            return True
    return False


def collect_js_files(target: Path) -> List[Path]:
    """Collect all .js files from a file or directory path."""
    files = []
    if target.is_file() and target.suffix == ".js":
        files.append(target)
    elif target.is_dir():
        for p in target.rglob("*.js"):
            if not should_exclude(p):
                files.append(p)
    return sorted(files)


def collect_html_files(target: Path) -> List[Path]:
    """Collect all .html files from a directory, or return single file."""
    files = []
    if target.is_file() and target.suffix == ".html":
        files.append(target)
    elif target.is_dir():
        for p in target.rglob("*.html"):
            if not should_exclude(p):
                files.append(p)
    return sorted(files)
