import os
import re

PY_RAW = "scripts/packages_raw.txt"
JS_RAW = "scripts/packages_raw_js.txt"
OUT = "scripts/packages_sorted.md"


def parse_python(path):
    """Parse robocopy-style ``name: Bytes : N`` lines (size in bytes)."""
    if not os.path.exists(path):
        return []
    packages = []
    with open(path) as f:
        for line in f:
            match = re.match(r"(.+?):\s+Bytes :\s+(\d+)", line)
            if match:
                packages.append((match.group(1).strip(), int(match.group(2))))
    packages.sort(key=lambda x: x[1], reverse=True)
    return packages


def parse_js(path):
    """Parse ``name: SIZE_MB`` lines emitted by measure-packages.ps1 for node_modules."""
    if not os.path.exists(path):
        return []
    packages = []
    with open(path) as f:
        for line in f:
            match = re.match(r"(.+?):\s+([\d.]+)\s*$", line)
            if match:
                packages.append((match.group(1).strip(), float(match.group(2))))
    packages.sort(key=lambda x: x[1], reverse=True)
    return packages


py_packages = parse_python(PY_RAW)
js_packages = parse_js(JS_RAW)

with open(OUT, "w") as f:
    f.write("## Python (venv site-packages)\n\n")
    f.write("| Package | Size (MB) |\n")
    f.write("|---|---|\n")
    for name, size in py_packages:
        mb = round(size / (1024 * 1024), 1)
        f.write(f"| {name} | {mb} |\n")
    if py_packages:
        py_total = round(sum(s for _, s in py_packages) / (1024 * 1024), 1)
        f.write(f"\n**Total: {py_total} MB**\n")

    if js_packages:
        f.write("\n## JavaScript (node_modules, top 30)\n\n")
        f.write("| Package | Size (MB) |\n")
        f.write("|---|---|\n")
        for name, mb in js_packages:
            f.write(f"| {name} | {mb} |\n")
        js_total = round(sum(s for _, s in js_packages), 1)
        f.write(f"\n**Top 30 Total: {js_total} MB**\n")

print("Written to packages_sorted.md")
