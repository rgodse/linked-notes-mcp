import ast, pathlib

SRC = pathlib.Path("src/linked_notes_mcp")

def test_server_never_imports_eval_or_optimize():
    py_files = list(SRC.rglob("*.py"))
    assert py_files, f"no source files found under {SRC} (wrong cwd?)"
    offenders = []
    for py in py_files:
        tree = ast.parse(py.read_text())
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            if any(m.split(".")[0] in {"evals", "optimize"} for m in mods):
                offenders.append(str(py))
    assert offenders == [], f"server imports dev-only packages: {offenders}"

def test_eval_optional_dep_group_present():
    import tomllib
    data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
    eval_deps = data["project"]["optional-dependencies"]["eval"]
    assert eval_deps == ["litellm>=1.0.0", "dspy-ai>=2.5"]
