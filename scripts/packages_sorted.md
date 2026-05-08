## Python (venv site-packages)

Scope is read from the `excludes=` list in `main.spec`: `prod` is shipped in the PyInstaller binary, `excluded` is stripped from the build (installed in the dev venv only), `cache` is `__pycache__`.

| Package | Size (MB) | Scope |
|---|---|---|
| music21 | 88.6 | prod |
| numpy | 34.3 | prod |
| matplotlib | 27.9 | excluded |
| pygame | 24.6 | prod |
| chardet | 20.8 | excluded |
| numpy.libs | 20.0 | prod |
| fontTools | 15.5 | excluded |
| PIL | 15.2 | prod |
| pip | 10.4 | excluded |
| pythonwin | 10.2 | excluded |
| setuptools | 8.3 | prod |
| pretty_midi | 6.0 | prod |
| win32 | 5.2 | prod |
| PyInstaller | 4.1 | excluded |
| win32comext | 3.1 | excluded |
| _soundfile_data | 2.3 | prod |
| joblib | 2.0 | excluded |
| win32com | 1.9 | excluded |
| mpl_toolkits | 1.5 | excluded |
| pycparser | 1.2 | prod |
| pyparsing | 1.0 | prod |
| _pyinstaller_hooks_contrib | 0.9 | excluded |
| urllib3 | 0.9 | prod |
| dill | 0.8 | prod |
| cffi | 0.8 | prod |
| pywin32_system32 | 0.8 | prod |
| music21-9.9.1.dist-info | 0.7 | prod |
| dateutil | 0.7 | prod |
| contourpy | 0.7 | excluded |
| idna | 0.6 | prod |
| more_itertools | 0.5 | prod |
| adodbapi | 0.5 | excluded |
| pkg_resources | 0.5 | prod |
| packaging | 0.5 | prod |
| charset_normalizer | 0.4 | prod |
| __pycache__ | 0.4 | cache |
| requests | 0.4 | prod |
| mido | 0.3 | prod |
| jsonpickle | 0.3 | excluded |
| certifi | 0.3 | prod |
| isapi | 0.2 | excluded |
| numpy-2.2.6.dist-info | 0.2 | prod |
| fonttools-4.61.1.dist-info | 0.2 | excluded |
| pyinstaller_hooks_contrib-2025.8.dist-info | 0.2 | excluded |
| win32ctypes | 0.2 | prod |
| kiwisolver | 0.2 | excluded |
| matplotlib-3.10.8.dist-info | 0.2 | excluded |
| pip-26.1.1.dist-info | 0.1 | excluded |
| pyinstaller-6.15.0.dist-info | 0.1 | excluded |
| altgraph | 0.1 | excluded |
| pillow-12.1.1.dist-info | 0.1 | prod |
| pywin32-311.dist-info | 0.1 | prod |
| webcolors | 0.1 | prod |
| setuptools-75.6.0.dist-info | 0.1 | prod |
| pygame-2.6.1.dist-info | 0.1 | prod |
| chardet-6.0.0.post1.dist-info | 0.0 | excluded |
| cycler | 0.0 | excluded |
| charset_normalizer-3.4.4.dist-info | 0.0 | prod |
| more_itertools-10.8.0.dist-info | 0.0 | prod |
| ordlookup | 0.0 | prod |
| joblib-1.5.3.dist-info | 0.0 | excluded |
| soundfile-0.13.1.dist-info | 0.0 | prod |
| _distutils_hack | 0.0 | excluded |
| dill-0.4.0.dist-info | 0.0 | prod |
| requests-2.32.5.dist-info | 0.0 | prod |
| packaging-25.0.dist-info | 0.0 | prod |
| python_dateutil-2.9.0.post0.dist-info | 0.0 | prod |
| mido-1.3.3.dist-info | 0.0 | prod |
| urllib3-2.5.0.dist-info | 0.0 | prod |
| jsonpickle-4.1.1.dist-info | 0.0 | excluded |
| idna-3.11.dist-info | 0.0 | prod |
| pywin32_ctypes-0.2.3.dist-info | 0.0 | prod |
| kiwisolver-1.4.9.dist-info | 0.0 | excluded |
| contourpy-1.3.3.dist-info | 0.0 | excluded |
| altgraph-0.17.4.dist-info | 0.0 | excluded |
| pyparsing-3.3.2.dist-info | 0.0 | prod |
| cffi-1.17.1.dist-info | 0.0 | prod |
| cycler-0.12.1.dist-info | 0.0 | excluded |
| pycparser-2.22.dist-info | 0.0 | prod |
| webcolors-25.10.0.dist-info | 0.0 | prod |
| certifi-2026.2.25.dist-info | 0.0 | prod |
| pefile-2023.2.7.dist-info | 0.0 | excluded |
| six-1.17.0.dist-info | 0.0 | prod |
| pretty_midi-0.2.10.dist-info | 0.0 | prod |

**Total: 317.5 MB** (prod: 215.9 MB, excluded: 101.2 MB)

## JavaScript (node_modules, top 30)

Scope is read from `package-lock.json`: `prod` is shipped to users, `dev` is only used during dev/build (safe to ignore for installer size), `cache` is a build cache folder, `?` is unclassified.

| Package | Size (MB) | Scope |
|---|---|---|
| electron | 275.5 | dev |
| app-builder-bin | 206.8 | dev |
| lucide-react | 34.5 | prod |
| typescript | 22.5 | dev |
| @img | 19.0 | dev |
| 7zip-bin | 11.7 | dev |
| @esbuild | 9.5 | dev |
| @babel | 8.1 | dev |
| .vite | 7.8 | cache |
| rxjs | 4.3 | dev |
| react-dom | 4.3 | prod |
| @rollup | 4.3 | dev |
| app-builder-lib | 3.7 | dev |
| eslint | 3.2 | dev |
| vite | 3.1 | dev |
| @types | 2.9 | dev |
| rollup | 2.7 | dev |
| es-abstract | 2.7 | dev |
| node-gyp | 2.1 | dev |
| caniuse-lite | 2.0 | dev |
| @electron | 1.7 | dev |
| path-scurry | 1.6 | dev |
| lodash | 1.3 | dev |
| config-file-ts | 1.2 | dev |
| csstype | 1.2 | dev |
| @eslint | 1.1 | dev |
| esquery | 1.0 | dev |
| ajv | 0.9 | dev |
| async | 0.8 | dev |
| source-map | 0.8 | dev |

**Top 30 Total: 642.3 MB** (prod: 38.8 MB, dev: 595.7 MB)
