"""Export a clean, identity-free copy of this repository.

    python tools/export_base.py OUT_DIR

Starts from `git archive HEAD` (so only tracked files, never local data), removes
everything that belongs to one business, applies the exact-text edits in
RULES (each must match, so a change upstream that breaks a rule fails loudly
instead of leaking text), writes the generic files, then scans the result for
identity strings (forbidden.txt) and fails if any remain.

The output has no git history. Initialise it as a new repository.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent

# ---- paths that belong to one business and are not part of the base
REMOVE = [
    "docs", "spec.md", "README.md", "app/static/img", "app/swiggy_ratings.json",
    "data/menu.json", "data/petpooja_menu_raw.json", "data/updates.json",
    "data/whatsapp_catalog_sheet.txt", "scripts/build_menu.py", "scripts/merge_petpooja.py",
    "scripts/petpooja_test_orders.py", "scripts/make_catalog_cards.py", "scripts/whatsapp_repl.py",
    "app/templates/bio.html", "tools",
]

# (relative path, old text, new text); old must occur, every occurrence is replaced
RULES: list[tuple[str, str, str]] = []
# file -> import line to add before its first top-level import
IMPORTS: dict[str, str] = {}
# (glob, regex, replacement) applied to every matching text file after RULES
REGEX_RULES: list[tuple[str, str, str]] = []
# file -> import line to add before its first top-level import
IMPORTS: dict[str, str] = {}

exec((TOOLS / "export_rules.py").read_text())


def run(out: Path) -> int:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tar = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(out)], input=tar, check=True)
    for p in REMOVE:
        t = out / p
        if t.is_dir():
            shutil.rmtree(t)
        elif t.exists():
            t.unlink()
    problems = []
    for rel, old, new in RULES:
        f = out / rel
        if not f.exists():
            problems.append(f"missing file for rule: {rel}")
            continue
        s = f.read_text()
        if old not in s:
            problems.append(f"rule no longer matches in {rel}: {old[:60]!r}")
            continue
        f.write_text(s.replace(old, new))
    for rel, line in IMPORTS.items():
        f = out / rel
        s = f.read_text()
        if line in s:
            continue
        m = re.search(r"^(from |import )", s, re.M)
        f.write_text(s[: m.start()] + line + "\n" + s[m.start():] if m else line + "\n" + s)
    for glob, pat, new in REGEX_RULES:
        for f in out.glob(glob):
            if f.is_file():
                try:
                    s = f.read_text()
                except UnicodeDecodeError:
                    continue
                f.write_text(re.sub(pat, new, s))
    gen = TOOLS / "base_files"
    if gen.exists():
        shutil.copytree(gen, out, dirs_exist_ok=True)
    forb = re.compile((TOOLS / "forbidden.txt").read_text().strip(), re.I)
    for f in sorted(out.rglob("*")):
        if f.is_file() and ".git/" not in str(f):
            try:
                text = f.read_text()
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if forb.search(line):
                    problems.append(f"{f.relative_to(out)}:{n}: {line.strip()[:110]}")
    if problems:
        print(f"{len(problems)} problem(s):")
        print("\n".join(problems))
        return 1
    print("clean:", out)
    return 0


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1])))
