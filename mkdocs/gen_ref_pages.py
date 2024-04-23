"""Generate the code reference pages and navigation."""
# https://mkdocstrings.github.io/recipes/#automatic-code-reference-pages


from pathlib import Path

import mkdocs_gen_files

IGNORE = {"__pycache__", "tests", "test", "examples", "docs", "doc", "build", "dist", "__init__", "__main__", "main"}

nav = mkdocs_gen_files.Nav()

src = Path(__file__).parent.parent / "src"

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    # if parts[-1] == "__init__":
    #     parts = parts[:-1]
    #     doc_path = doc_path.with_name("index.md")
    #     full_doc_path = full_doc_path.with_name("index.md")
    #     continue
    # elif parts[-1] == "__main__":
    #     continue

    if parts[-1] in IGNORE:
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
