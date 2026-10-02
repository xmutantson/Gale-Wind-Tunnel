"""Read-only checks for this flattened Inventor package; no CAD application required."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import xml.etree.ElementTree as ET


PROJECT = "Main With Subparts.ipj"
ASSEMBLY = "Main With Subparts.iam"
STEP = "Main With Subparts.stp"
NATIVE_SUFFIXES = {".ipt", ".iam"}


def read_text(path):
    """Inventor logs/projects may be UTF-16; STEP and Markdown are usually UTF-8."""
    data = path.read_bytes()
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    return data.decode(encoding)


def step_code(text):
    """Mask STEP strings/comments so their contents cannot masquerade as entities."""
    result = []
    i = 0
    while i < len(text):
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated STEP comment")
            end += 2
        elif text[i] == "'":
            end = i + 1
            while end < len(text):
                if text[end] == "'":
                    if end + 1 < len(text) and text[end + 1] == "'":
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            else:
                raise ValueError("Unterminated STEP string")
        else:
            result.append(text[i])
            i += 1
            continue
        result.append("".join("\n" if c == "\n" else " " for c in text[i:end]))
        i = end
    return "".join(result)


def check_step(text):
    """Check text structure/references only, not STEP grammar, topology or dimensions."""
    code = step_code(text)
    problems = []
    if not code.lstrip().startswith("ISO-10303-21;"):
        problems.append("Missing STEP opening marker")
    if not code.rstrip().endswith("END-ISO-10303-21;"):
        problems.append("Missing STEP closing marker")
    for marker, expected in (("HEADER", 1), ("DATA", 1), ("ENDSEC", 2)):
        count = len(re.findall(r"\b" + marker + r"\s*;", code))
        if count != expected:
            problems.append(f"Expected {expected} {marker} section marker(s); found {count}")
    definitions = Counter(re.findall(r"(?:^|;)\s*#(\d+)\s*=", code))
    if not definitions:
        problems.append("No STEP entity definitions found")
    duplicates = sorted((n for n, count in definitions.items() if count > 1), key=int)
    undefined = sorted(set(re.findall(r"#(\d+)", code)) - definitions.keys(), key=int)
    if duplicates:
        problems.append("Duplicate STEP entity IDs: " + ", ".join(duplicates[:10]))
    if undefined:
        problems.append("Undefined STEP entity references: " + ", ".join(undefined[:10]))
    counts = {
        name: len(re.findall(r"#\d+\s*=\s*" + name + r"\s*\(", code))
        for name in ("PRODUCT", "NEXT_ASSEMBLY_USAGE_OCCURRENCE", "MANIFOLD_SOLID_BREP", "CLOSED_SHELL")
    }
    return {"entities": len(definitions), "entity_types": counts}, problems


def validate(root):
    root = Path(root).resolve()
    report = {"errors": [], "warnings": [], "manifest": {}, "step": {}, "assets": []}

    def issue(level, code, path, message):
        report[level].append({"code": code, "path": path, "message": message})

    def local_file(name):
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"File resolves outside package: {name}")
        return path

    def load(name):
        return read_text(local_file(name))

    if not root.is_dir():
        issue("errors", "package_missing", ".", "Package directory does not exist")
        return report

    # Materialize once: directory iteration can fail either when started or
    # partway through consumption. Keep that failure in the structured report.
    try:
        entries = list(root.iterdir())
    except OSError as exc:
        entries = []
        issue("errors", "inventory_unreadable", ".", str(exc))

    try:
        log = load("packngo.log")
        declared = re.search(r"^Number of Files Copied:\s*(\d+)\s*$", log, re.MULTILINE)
        if not declared:
            raise ValueError("Missing Number of Files Copied in packngo.log")
        if not re.search(r"^Keep folder hierarchy:\s*No\s*$", log, re.MULTILINE):
            raise ValueError("Validator requires a flattened Pack and Go manifest (Keep folder hierarchy: No)")
        names = []
        for line in log.splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and PureWindowsPath(fields[0]).suffix.lower() in NATIVE_SUFFIXES:
                names.append(PureWindowsPath(fields[0]).name)
        report["manifest"] = {"declared_files": int(declared[1]), "listed_files": len(names)}
        if len(names) != int(declared[1]):
            issue("errors", "manifest_count", "packngo.log", "Declared and listed native file counts differ")
        if len({name.casefold() for name in names}) != len(names):
            issue("errors", "manifest_duplicate", "packngo.log", "Duplicate filenames in flattened manifest")
        for name in sorted(set(names)):
            if not local_file(name).is_file():
                issue("errors", "native_missing", name, "Native file listed in packngo.log is absent")
        expected = {name.casefold() for name in names}
        for path in sorted(entries):
            if path.suffix.lower() in NATIVE_SUFFIXES and path.name.casefold() not in expected:
                issue("warnings", "native_unlisted", path.name, "Native file is not listed in the historical manifest; review package inventory")
    except (OSError, UnicodeError, ValueError) as exc:
        issue("errors", "manifest_unreadable", "packngo.log", str(exc))

    try:
        project = ET.fromstring(load(PROJECT))
        if project.tag != "InventorProject":
            raise ValueError("Expected InventorProject XML root")
        for node in project.findall(".//Path"):
            value = (node.text or "").strip()
            if not value or value == ".":
                continue
            windows_path = PureWindowsPath(value)
            if windows_path.drive or windows_path.root or ".." in windows_path.parts:
                issue("warnings", "project_external_resource", value, "Project resource is not package-relative; verify it in Inventor")
                continue
            relative = Path(*windows_path.parts)
            resource = local_file(relative)
            if not resource.exists():
                issue("warnings", "project_resource_missing", relative.as_posix(), "Configured project resource is absent; installed defaults may differ")
    except (OSError, UnicodeError, ValueError, ET.ParseError) as exc:
        issue("errors", "project_unreadable", PROJECT, str(exc))

    try:
        report["step"], problems = check_step(load(STEP))
        for problem in problems:
            issue("errors", "step_text", STEP, problem)
    except (OSError, UnicodeError, ValueError) as exc:
        issue("errors", "step_unreadable", STEP, str(exc))

    required = {PROJECT, ASSEMBLY, STEP}
    candidates = {path.name for path in entries if path.suffix.lower() in NATIVE_SUFFIXES}
    for name in sorted(candidates | required):
        try:
            data = local_file(name).read_bytes()
            if not data:
                issue("errors", "asset_empty", name, "CAD asset is empty")
            report["assets"].append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        except (OSError, ValueError) as exc:
            issue("errors", "asset_unreadable", name, str(exc))
    # One material library can be configured for both appearance and physical properties.
    report["warnings"] = list({json.dumps(item, sort_keys=True): item for item in report["warnings"]}.values())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Package root (defaults to this repository)")
    parser.add_argument("--json", action="store_true", help="Print findings and SHA-256 inventory as JSON")
    args = parser.parse_args(argv)
    report = validate(args.root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for level in ("errors", "warnings"):
            for item in report[level]:
                print(f"{level[:-1].upper()} [{item['code']}] {item['path']}: {item['message']}")
        print(f"Checked {len(report['assets'])} CAD assets; {len(report['errors'])} error(s), {len(report['warnings'])} warning(s).")
        print("Text/package checks only; CAD opening, geometry and performance are not validated.")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
