import json
import os
import re

PY_RAW = "scripts/packages_raw.txt"
JS_RAW = "scripts/packages_raw_js.txt"
LOCKFILE = "package-lock.json"
PACKAGE_JSON = "package.json"
PYINSTALLER_SPEC = "main.spec"
OUT = "scripts/packages_sorted.md"

DIST_INFO_RE = re.compile(
    r"^(.+?)-\d[\w.+-]*\.dist-info$",
    re.IGNORECASE,
)


def normalize_py_name(name):
    """Lowercase, hyphens-to-underscores, strip dist-info version suffix."""
    name = name.strip()
    match = DIST_INFO_RE.match(name)
    if match:
        name = match.group(1)
    return name.lower().replace("-", "_")


def parse_pyinstaller_excludes(spec_path):
    """Extract the excludes=[...] list from a PyInstaller spec file.

    Returns a set of normalized module names.
    """
    if not os.path.exists(spec_path):
        return set()
    with open(spec_path) as f:
        content = f.read()
    match = re.search(r"excludes\s*=\s*\[([^\]]*)\]", content)
    if not match:
        return set()
    items = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
    return {normalize_py_name(item) for item in items}


def classify_py(name, excludes):
    """Classify a venv directory entry.

    Returns one of "excluded" (stripped from PyInstaller build), "cache"
    (__pycache__-style noise), or "prod" (shipped in the binary).
    """
    if name == "__pycache__" or name.startswith("."):
        return "cache"
    n = normalize_py_name(name)
    if n in excludes or f"_{n}" in excludes:
        return "excluded"
    return "prod"


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


def classify_js(names, lockfile_path, package_json_path):
    """Classify each top-level node_modules entry by npm scope.

    Uses package-lock.json's per-package ``dev`` / ``devOptional`` flags.
    A package is marked ``dev`` iff every path from the project root to it
    goes through devDependencies (npm sets ``dev: true`` in that case).

    Returns dict: name -> one of "prod", "dev", "cache", "?".
    """
    direct_prod = set()
    if os.path.exists(package_json_path):
        with open(package_json_path) as f:
            pkg = json.load(f)
        direct_prod = set((pkg.get("dependencies") or {}).keys())

    packages = {}
    if os.path.exists(lockfile_path):
        with open(lockfile_path) as f:
            lock = json.load(f)
        packages = lock.get("packages", {})

    def is_dev_entry(entry):
        return bool(entry.get("dev") or entry.get("devOptional"))

    def lookup(name):
        if name.startswith("."):
            return "cache"

        if name in direct_prod:
            return "prod"

        if name.startswith("@"):
            prefix = f"node_modules/{name}/"
            children = [k for k in packages if k.startswith(prefix)]
            if not children:
                return "?"
            if all(is_dev_entry(packages[k]) for k in children):
                return "dev"
            return "prod"

        entry = packages.get(f"node_modules/{name}")
        if entry is None:
            return "?"
        return "dev" if is_dev_entry(entry) else "prod"

    return {name: lookup(name) for name in names}


py_packages = parse_python(PY_RAW)
js_packages = parse_js(JS_RAW)
js_classes = classify_js([n for n, _ in js_packages], LOCKFILE, PACKAGE_JSON)
py_excludes = parse_pyinstaller_excludes(PYINSTALLER_SPEC)
py_classes = {name: classify_py(name, py_excludes) for name, _ in py_packages}

with open(OUT, "w") as f:
    f.write("## Python (venv site-packages)\n\n")
    f.write(
        "Scope is read from the `excludes=` list in `main.spec`: `prod` is "
        "shipped in the PyInstaller binary, `excluded` is stripped from the "
        "build (installed in the dev venv only), `cache` is `__pycache__`.\n\n"
    )
    f.write("| Package | Size (MB) | Scope |\n")
    f.write("|---|---|---|\n")
    py_prod_bytes = 0
    py_excluded_bytes = 0
    py_cache_bytes = 0
    for name, size in py_packages:
        mb = round(size / (1024 * 1024), 1)
        scope = py_classes.get(name, "prod")
        f.write(f"| {name} | {mb} | {scope} |\n")
        if scope == "prod":
            py_prod_bytes += size
        elif scope == "excluded":
            py_excluded_bytes += size
        elif scope == "cache":
            py_cache_bytes += size
    if py_packages:
        total = sum(s for _, s in py_packages)
        prod_mb = round(py_prod_bytes / (1024 * 1024), 1)
        excluded_mb = round(py_excluded_bytes / (1024 * 1024), 1)
        f.write(
            f"\n**Total: {round(total / (1024 * 1024), 1)} MB** "
            f"(prod: {prod_mb} MB, excluded: {excluded_mb} MB)\n"
        )

    if js_packages:
        f.write("\n## JavaScript (node_modules, top 30)\n\n")
        f.write(
            "Scope is read from `package-lock.json`: `prod` is shipped to users, "
            "`dev` is only used during dev/build (safe to ignore for installer "
            "size), `cache` is a build cache folder, `?` is unclassified.\n\n"
        )
        f.write("| Package | Size (MB) | Scope |\n")
        f.write("|---|---|---|\n")
        prod_total = 0.0
        dev_total = 0.0
        for name, mb in js_packages:
            scope = js_classes.get(name, "?")
            f.write(f"| {name} | {mb} | {scope} |\n")
            if scope == "prod":
                prod_total += mb
            elif scope == "dev":
                dev_total += mb
        js_total = round(sum(s for _, s in js_packages), 1)
        f.write(
            f"\n**Top 30 Total: {js_total} MB** "
            f"(prod: {round(prod_total, 1)} MB, dev: {round(dev_total, 1)} MB)\n"
        )

print("Written to packages_sorted.md")
