from __future__ import annotations

import argparse
import ast
import logging
from pathlib import Path
from typing import Final


LOGGER_NAME: Final[str] = "aegis_art_atelier_builder"

DEFAULT_MODULE_ORDER: Final[tuple[str, ...]] = (
    "config.py",
    "image_utils.py",
    "caption_utils.py",
    "sampling.py",
    "manifest.py",
    "statistics.py",
    "compression.py",
    "etl.py",
)

INTERNAL_MODULES: Final[frozenset[str]] = frozenset(
    {
        "config",
        "image_utils",
        "caption_utils",
        "sampling",
        "manifest",
        "statistics",
        "compression",
        "etl",
    }
)


def configure_logging() -> logging.Logger:
    """Configure console logging for the builder."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    return logging.getLogger(LOGGER_NAME)


def _is_internal_import(node: ast.Import | ast.ImportFrom) -> bool:
    """Return whether an import references one of the project modules."""
    if isinstance(node, ast.Import):
        return any(
            alias.name.split(".")[0] in INTERNAL_MODULES
            for alias in node.names
        )

    if node.level > 0:
        return True

    if node.module is None:
        return False

    return node.module.split(".")[0] in INTERNAL_MODULES


def _is_future_import(node: ast.Import | ast.ImportFrom) -> bool:
    """Return whether an AST node is a future import."""
    return (
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "__future__"
    )


def _is_module_docstring(node: ast.AST, is_first_module: bool) -> bool:
    """Return whether an AST node is a module-level docstring."""
    if is_first_module:
        return False

    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _remove_source_ranges(
    source: str,
    tree: ast.Module,
    is_first_module: bool,
    future_import_already_written: bool,
) -> tuple[str, bool]:
    """Remove imports that cannot remain in the merged file.

    Internal imports are removed because all project modules are concatenated
    into the same namespace. Future imports are retained only from the first
    module because Python requires them to appear at the beginning of a file.
    """
    source_lines = source.splitlines(keepends=True)
    ranges_to_remove: list[tuple[int, int]] = []

    for node in tree.body:
        should_remove = False

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if _is_internal_import(node):
                should_remove = True
            elif _is_future_import(node):
                if future_import_already_written:
                    should_remove = True
                else:
                    future_import_already_written = True

        if _is_module_docstring(node, is_first_module):
            should_remove = True

        if should_remove:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            ranges_to_remove.append((start_line, end_line))

    for start_line, end_line in ranges_to_remove:
        for line_index in range(start_line, end_line):
            source_lines[line_index] = ""

    return "".join(source_lines), future_import_already_written


def _validate_source(path: Path) -> ast.Module:
    """Parse and validate a Python source file."""
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SyntaxError(
            f"Source module contains invalid Python syntax: {path}"
        ) from exc


def merge_modules(
    source_dir: Path,
    output_file: Path,
    module_order: tuple[str, ...] = DEFAULT_MODULE_ORDER,
) -> Path:
    """Merge modular ETL files into one standalone Python script.

    Args:
        source_dir: Directory containing the modular source files.
        output_file: Destination path for the generated single-file script.
        module_order: Ordered module filenames to concatenate.

    Returns:
        Path to the generated standalone file.

    Raises:
        FileNotFoundError: If a required module is missing.
        SyntaxError: If a module cannot be parsed.
        OSError: If the output cannot be written.
    """
    source_dir = Path(source_dir)
    output_file = Path(output_file)

    if not source_dir.is_dir():
        raise NotADirectoryError(
            f"Source directory does not exist: {source_dir}"
        )

    merged_sections: list[str] = []
    future_import_already_written = False

    for module_index, module_name in enumerate(module_order):
        module_path = source_dir / module_name

        if not module_path.is_file():
            raise FileNotFoundError(
                f"Required module is missing: {module_path}"
            )

        tree = _validate_source(module_path)
        source = module_path.read_text(encoding="utf-8")

        processed_source, future_import_already_written = (
            _remove_source_ranges(
                source=source,
                tree=tree,
                is_first_module=module_index == 0,
                future_import_already_written=future_import_already_written,
            )
        )

        section_header = (
            f"\n\n# -----------------------------------------------------------------\n"
            f"# Merged module: {module_name}\n"
            f"# -----------------------------------------------------------------\n\n"
        )

        merged_sections.append(section_header)
        merged_sections.append(processed_source.rstrip())
        merged_sections.append("\n")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        "".join(merged_sections),
        encoding="utf-8",
        newline="\n",
    )

    _validate_source(output_file)

    return output_file


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the module builder."""
    parser = argparse.ArgumentParser(
        description=(
            "Merge the modular Aegis-Art-Atelier ETL implementation into "
            "one standalone Python file."
        )
    )

    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("."),
        help="Directory containing the modular Python files.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("aegis_art_atelier_etl.py"),
        help="Path for the generated standalone ETL script.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output file.",
    )

    return parser.parse_args()


def main() -> None:
    """Build the standalone ETL script."""
    logger = configure_logging()
    args = parse_arguments()

    if args.output_file.exists() and not args.force:
        raise FileExistsError(
            f"Output file already exists: {args.output_file}. "
            "Use --force to replace it."
        )

    output_file = merge_modules(
        source_dir=args.source_dir,
        output_file=args.output_file,
    )

    logger.info("Standalone ETL script created: %s", output_file)
    logger.info(
        "Run it with: python %s --output-dir /content/aegis_art_atelier_22k",
        output_file,
    )


if __name__ == "__main__":
    main()