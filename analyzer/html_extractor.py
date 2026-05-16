"""Extract <script> tags and global calls from HTML files."""
from pathlib import Path
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


class HtmlExtractor:
    """Extracts script information from HTML files."""

    def extract(self, html_path: Path) -> Dict[str, Any]:
        """Extract all script-related info from an HTML file."""
        content = html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "lxml")

        scripts = []
        for idx, tag in enumerate(soup.find_all("script")):
            script_info = {
                "index": idx,
                "src": tag.get("src"),
                "type": tag.get("type", "text/javascript"),
                "inline": tag.string.strip() if tag.string else None,
                "line": tag.sourceline if hasattr(tag, "sourceline") else None,
            }
            scripts.append(script_info)

        # Find global calls after scripts (simple heuristic)
        global_calls = self._find_global_calls(soup)

        return {
            "file": str(html_path),
            "scripts": scripts,
            "script_count": len(scripts),
            "global_calls": global_calls,
        }

    def _find_global_calls(self, soup: BeautifulSoup) -> List[Dict]:
        """Find patterns like window.App.init(), document.addEventListener, etc."""
        calls = []
        # Search for inline scripts that contain window.* or document.* calls
        for script in soup.find_all("script"):
            if script.string:
                text = script.string
                for pattern in ["window.", "document.", "globalThis.", "self."]:
                    if pattern in text:
                        # Extract rough call signatures
                        lines = text.split("\n")
                        for line in lines:
                            stripped = line.strip()
                            if stripped.startswith(pattern) and "(" in stripped:
                                calls.append({
                                    "pattern": pattern.rstrip("."),
                                    "call": stripped[:120],
                                    "line": line,
                                })
        return calls
