"""Developer tool processors."""
from __future__ import annotations

import base64
import binascii
import json
import re
import secrets
import string
import uuid

from app.tools.registry import ToolResult, register


@register("json-formatter")
def json_formatter(files, text: str, options: dict) -> ToolResult:
    indent = int(options.get("indent", 2) or 0)
    try:
        parsed = json.loads(text or "")
    except json.JSONDecodeError as e:
        return ToolResult(meta={"valid": False, "error": str(e)})
    pretty = json.dumps(parsed, indent=indent if indent > 0 else None, ensure_ascii=False)
    return ToolResult(text=pretty, meta={"valid": True})


@register("json-validator")
def json_validator(files, text: str, options: dict) -> ToolResult:
    try:
        json.loads(text or "")
        return ToolResult(meta={"valid": True, "message": "Valid JSON ✓"})
    except json.JSONDecodeError as e:
        return ToolResult(meta={
            "valid": False,
            "error": e.msg,
            "line": e.lineno,
            "column": e.colno,
        })


@register("json-minifier")
def json_minifier(files, text: str, options: dict) -> ToolResult:
    try:
        parsed = json.loads(text or "")
    except json.JSONDecodeError as e:
        return ToolResult(meta={"valid": False, "error": str(e)})
    return ToolResult(text=json.dumps(parsed, separators=(",", ":"), ensure_ascii=False),
                      meta={"valid": True})


@register("base64-encoder")
def base64_encoder(files, text: str, options: dict) -> ToolResult:
    encoded = base64.b64encode((text or "").encode("utf-8")).decode("ascii")
    return ToolResult(text=encoded)


@register("base64-decoder")
def base64_decoder(files, text: str, options: dict) -> ToolResult:
    try:
        decoded = base64.b64decode((text or "").encode("ascii"), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        return ToolResult(meta={"valid": False, "error": f"Invalid Base64: {e}"})
    return ToolResult(text=decoded, meta={"valid": True})


@register("uuid-generator")
def uuid_generator(files, text: str, options: dict) -> ToolResult:
    count = max(1, min(int(options.get("count", 1) or 1), 500))
    return ToolResult(text="\n".join(str(uuid.uuid4()) for _ in range(count)))


@register("password-generator")
def password_generator(files, text: str, options: dict) -> ToolResult:
    length = max(4, min(int(options.get("length", 16) or 16), 128))
    alphabet = string.ascii_letters
    if options.get("digits", True):
        alphabet += string.digits
    if options.get("symbols", True):
        alphabet += "!@#$%^&*()-_=+[]{};:,.<>?"
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    return ToolResult(text=pwd)


@register("css-minifier")
def css_minifier(files, text: str, options: dict) -> ToolResult:
    css = text or ""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)          # comments
    css = re.sub(r"\s+", " ", css)                                # collapse whitespace
    css = re.sub(r"\s*([{}:;,>~+])\s*", r"\1", css)               # around tokens
    css = css.replace(";}", "}").strip()
    return ToolResult(text=css, meta={"original": len(text or ""), "minified": len(css)})


@register("js-minifier")
def js_minifier(files, text: str, options: dict) -> ToolResult:
    js = text or ""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)            # block comments
    js = re.sub(r"(?<![:\\])//[^\n]*", "", js)                    # line comments
    lines = [ln.strip() for ln in js.splitlines()]
    js = "\n".join(ln for ln in lines if ln)
    return ToolResult(text=js, meta={"original": len(text or ""), "minified": len(js)})


@register("html-formatter")
def html_formatter(files, text: str, options: dict) -> ToolResult:
    indent_size = int(options.get("indent", 2) or 0)
    pad = " " * indent_size
    # Split into tags and text nodes.
    tokens = re.split(r"(<[^>]+>)", text or "")
    out: list[str] = []
    depth = 0
    void = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed",
            "source", "track", "wbr"}
    for tok in tokens:
        chunk = tok.strip()
        if not chunk:
            continue
        if chunk.startswith("</"):
            depth = max(depth - 1, 0)
            out.append(pad * depth + chunk)
        elif chunk.startswith("<"):
            tag = re.match(r"<\s*([a-zA-Z0-9]+)", chunk)
            name = tag.group(1).lower() if tag else ""
            self_closing = chunk.endswith("/>") or name in void or chunk.startswith("<!")
            out.append(pad * depth + chunk)
            if not self_closing:
                depth += 1
        else:
            out.append(pad * depth + chunk)
    return ToolResult(text="\n".join(out))


# ===========================================================================
# Shared helpers
# ===========================================================================

def _int(options: dict, key: str, default: int) -> int:
    try:
        return int(float(str(options.get(key, default)).strip() or default))
    except (TypeError, ValueError):
        return default


def _flag(options: dict, key: str, default: bool = False) -> bool:
    value = options.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _load_json(text: str) -> tuple[object | None, str | None]:
    """Parse JSON, returning the error message instead of raising."""
    if not (text or "").strip():
        return None, "Paste some JSON."
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON on line {e.lineno}, column {e.colno}: {e.msg}"


# ===========================================================================
# JSON
# ===========================================================================

@register("json-viewer")
def json_viewer(files, text: str, options: dict) -> ToolResult:
    """Flattens JSON into one path per value, which is what you actually search."""
    data, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": error})

    rows: list[str] = []
    depth = {"max": 0}

    def walk(node, path: str, level: int) -> None:
        depth["max"] = max(depth["max"], level)
        if isinstance(node, dict):
            if not node:
                rows.append(f"{path} = {{}} (empty object)")
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else key, level + 1)
        elif isinstance(node, list):
            if not node:
                rows.append(f"{path} = [] (empty array)")
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]", level + 1)
        else:
            rows.append(f"{path or '$'} = {json.dumps(node)}")

    walk(data, "", 0)
    limit = max(1, min(_int(options, "limit", 500), 5000))
    return ToolResult(text="\n".join(rows[:limit]), meta={
        "total_values": len(rows),
        "shown": min(len(rows), limit),
        "max_depth": depth["max"],
        "root_type": type(data).__name__,
    })


@register("json-diff")
def json_diff(files, text: str, options: dict) -> ToolResult:
    """Compares two JSON documents by path, not by text.

    A textual diff flags reordered keys and reindented lines as changes; this
    only reports values that genuinely differ.
    """
    left, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": error})
    right_raw = str(options.get("compare_with", ""))
    if not right_raw.strip():
        return ToolResult(meta={"error": "Paste the second JSON document."})
    try:
        right = json.loads(right_raw)
    except json.JSONDecodeError as e:
        return ToolResult(meta={"error": f"Second document is invalid JSON: {e.msg}"})

    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []

    def compare(a, b, path: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in a.keys() | b.keys():
                where = f"{path}.{key}" if path else key
                if key not in b:
                    removed.append(f"{where} = {json.dumps(a[key])}")
                elif key not in a:
                    added.append(f"{where} = {json.dumps(b[key])}")
                else:
                    compare(a[key], b[key], where)
        elif isinstance(a, list) and isinstance(b, list):
            for i in range(max(len(a), len(b))):
                where = f"{path}[{i}]"
                if i >= len(b):
                    removed.append(f"{where} = {json.dumps(a[i])}")
                elif i >= len(a):
                    added.append(f"{where} = {json.dumps(b[i])}")
                else:
                    compare(a[i], b[i], where)
        elif a != b:
            changed.append(f"{path or '$'}: {json.dumps(a)} -> {json.dumps(b)}")

    compare(left, right, "")
    lines = ([f"+ {x}" for x in added] + [f"- {x}" for x in removed]
             + [f"~ {x}" for x in changed])
    return ToolResult(text="\n".join(lines) or "The two documents are identical.", meta={
        "identical": not lines,
        "added": len(added), "removed": len(removed), "changed": len(changed),
    })


@register("jsonpath-tester")
def jsonpath_tester(files, text: str, options: dict) -> ToolResult:
    """A dotted-path query, with [n] and [*] for arrays.

    Deliberately a small subset of JSONPath rather than the whole grammar: the
    full spec includes filter expressions, and evaluating those means running
    user-supplied code on the server.
    """
    data, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": error})
    query = str(options.get("query", "")).strip().lstrip("$").lstrip(".")
    if not query:
        return ToolResult(meta={"error": "Enter a path, e.g. users[0].email or users[*].name"})

    nodes = [data]
    for part in re.findall(r"[^.\[\]]+|\[\*\]|\[\d+\]", query):
        nxt = []
        for node in nodes:
            if part == "[*]":
                if isinstance(node, list):
                    nxt.extend(node)
                elif isinstance(node, dict):
                    nxt.extend(node.values())
            elif part.startswith("[") and part.endswith("]"):
                i = int(part[1:-1])
                if isinstance(node, list) and -len(node) <= i < len(node):
                    nxt.append(node[i])
            elif isinstance(node, dict) and part in node:
                nxt.append(node[part])
        nodes = nxt
        if not nodes:
            break
    if not nodes:
        return ToolResult(text="", meta={"matches": 0, "note": "Nothing matched that path."})
    return ToolResult(text=json.dumps(nodes if len(nodes) > 1 else nodes[0], indent=2),
                      meta={"matches": len(nodes)})


@register("json-yaml-converter")
def json_yaml_converter(files, text: str, options: dict) -> ToolResult:
    import yaml

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some JSON or YAML."})
    if str(options.get("direction", "json_to_yaml")) == "json_to_yaml":
        data, error = _load_json(src)
        if error:
            return ToolResult(meta={"error": error})
        out = yaml.safe_dump(data, sort_keys=_flag(options, "sort_keys"),
                             allow_unicode=True, default_flow_style=False)
        return ToolResult(text=out)
    try:
        # safe_load, never load: full YAML can construct arbitrary Python objects,
        # which turns "paste your config here" into remote code execution.
        data = yaml.safe_load(src)
    except yaml.YAMLError as e:
        return ToolResult(meta={"error": f"Invalid YAML: {str(e).splitlines()[0]}"})
    return ToolResult(text=json.dumps(data, indent=_int(options, "indent", 2), ensure_ascii=False))


def _dict_to_xml(node, tag: str, indent: int, level: int = 0) -> str:
    from xml.sax.saxutils import escape

    pad = " " * (indent * level)
    safe_tag = re.sub(r"[^A-Za-z0-9_.-]", "_", str(tag)) or "item"
    if safe_tag[0].isdigit():
        safe_tag = "_" + safe_tag
    if isinstance(node, dict):
        inner = "\n".join(_dict_to_xml(v, k, indent, level + 1) for k, v in node.items())
        return f"{pad}<{safe_tag}>\n{inner}\n{pad}</{safe_tag}>" if inner else f"{pad}<{safe_tag}/>"
    if isinstance(node, list):
        return "\n".join(_dict_to_xml(v, safe_tag, indent, level) for v in node)
    value = "" if node is None else escape(str(node))
    return f"{pad}<{safe_tag}>{value}</{safe_tag}>"


@register("json-xml-converter")
def json_xml_converter(files, text: str, options: dict) -> ToolResult:
    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some JSON or XML."})
    root = str(options.get("root", "root")) or "root"
    indent = _int(options, "indent", 2)
    if str(options.get("direction", "json_to_xml")) == "json_to_xml":
        data, error = _load_json(src)
        if error:
            return ToolResult(meta={"error": error})
        body = _dict_to_xml(data, root, indent)
        return ToolResult(text='<?xml version="1.0" encoding="UTF-8"?>\n' + body)

    import xml.etree.ElementTree as ET

    if len(src) > 2_000_000:
        return ToolResult(meta={"error": "That XML is over 2 MB. Trim it down first."})
    try:
        # ElementTree ignores DTDs and refuses undefined entities, so the classic
        # entity-expansion and external-entity attacks do not apply here.
        element = ET.fromstring(src)
    except ET.ParseError as e:
        return ToolResult(meta={"error": f"Invalid XML: {e}"})

    def convert(el):
        children = list(el)
        if not children:
            return (el.text or "").strip()
        out: dict = {}
        for child in children:
            value = convert(child)
            if child.tag in out:
                # Repeated tags are how XML writes a list; collect them into one.
                if not isinstance(out[child.tag], list):
                    out[child.tag] = [out[child.tag]]
                out[child.tag].append(value)
            else:
                out[child.tag] = value
        return out

    return ToolResult(text=json.dumps({element.tag: convert(element)}, indent=indent, ensure_ascii=False))


@register("json-csv-converter")
def json_csv_converter(files, text: str, options: dict) -> ToolResult:
    """JSON ⇄ CSV/TSV, both directions."""
    import csv
    import io

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some JSON or CSV."})
    delim = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}.get(
        str(options.get("delimiter", "comma")), ",")

    if str(options.get("direction", "json_to_csv")) == "json_to_csv":
        data, error = _load_json(src)
        if error:
            return ToolResult(meta={"error": error})
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return ToolResult(meta={"error": "CSV needs an array of objects."})
        if not all(isinstance(row, dict) for row in data):
            return ToolResult(meta={"error": "Every item in the array must be an object."})
        # Union of keys, in first-seen order, so a row missing a field still lines up.
        headers: list[str] = []
        for row in data:
            for key in row:
                if key not in headers:
                    headers.append(key)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, delimiter=delim,
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in data:
            writer.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                             for k, v in row.items()})
        return ToolResult(text=buf.getvalue().rstrip("\n"),
                          meta={"rows": len(data), "columns": len(headers)})

    reader = csv.DictReader(io.StringIO(src), delimiter=delim)
    rows = list(reader)
    if not rows:
        return ToolResult(meta={"error": "No data rows found. The first line must be the header."})
    if _flag(options, "parse_numbers", True):
        for row in rows:
            for key, value in list(row.items()):
                if value is None or value == "":
                    continue
                try:
                    row[key] = int(value) if re.fullmatch(r"-?\d+", value) else float(value)
                except ValueError:
                    pass
    return ToolResult(text=json.dumps(rows, indent=_int(options, "indent", 2), ensure_ascii=False),
                      meta={"rows": len(rows), "columns": len(rows[0])})


def _to_toml(data: dict, prefix: str = "") -> str:
    """Minimal TOML writer — tomllib only reads."""
    def fmt(value) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(fmt(v) for v in value) + "]"
        return json.dumps(str(value))

    scalars, tables = [], []
    for key, value in data.items():
        if isinstance(value, dict):
            name = f"{prefix}.{key}" if prefix else key
            tables.append(f"\n[{name}]\n" + _to_toml(value, name))
        else:
            scalars.append(f"{key} = {fmt(value)}")
    return "\n".join(scalars) + "".join(tables)


@register("toml-ini-converter")
def toml_ini_converter(files, text: str, options: dict) -> ToolResult:
    """Between TOML, INI and JSON."""
    import configparser
    import io
    import tomllib

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some TOML, INI or JSON."})
    direction = str(options.get("direction", "toml_to_json"))
    try:
        if direction == "toml_to_json":
            return ToolResult(text=json.dumps(tomllib.loads(src), indent=2, ensure_ascii=False))
        if direction == "ini_to_json":
            parser = configparser.ConfigParser()
            parser.read_string(src)
            out = {s: dict(parser[s]) for s in parser.sections()}
            if parser.defaults():
                out["DEFAULT"] = dict(parser.defaults())
            return ToolResult(text=json.dumps(out, indent=2, ensure_ascii=False))
        data, error = _load_json(src)
        if error:
            return ToolResult(meta={"error": error})
        if not isinstance(data, dict):
            return ToolResult(meta={"error": "TOML and INI both need an object at the top level."})
        if direction == "json_to_toml":
            return ToolResult(text=_to_toml(data).strip())
        parser = configparser.ConfigParser()
        for section, values in data.items():
            if not isinstance(values, dict):
                return ToolResult(meta={"error": "INI needs every top-level key to be a section object."})
            parser[section] = {k: str(v) for k, v in values.items()}
        buf = io.StringIO()
        parser.write(buf)
        return ToolResult(text=buf.getvalue().strip())
    except (tomllib.TOMLDecodeError, configparser.Error) as e:
        return ToolResult(meta={"error": f"Could not parse that: {e}"})


# ===========================================================================
# Formatters, minifiers and validators
# ===========================================================================

def _strip_strings(code: str) -> list[tuple[int, int]]:
    """Spans covered by string literals or comments, so scanners can skip them.

    Brace and bracket counting is meaningless without this: a `"{"` inside a
    string would otherwise be reported as an unclosed block.
    """
    spans, i, n = [], 0, len(code)
    while i < n:
        ch = code[i]
        if ch in "\"'`":
            start, quote = i, ch
            i += 1
            while i < n and code[i] != quote:
                i += 2 if code[i] == "\\" else 1
            i = min(i + 1, n)  # step PAST the closing quote, not onto it
            spans.append((start, i))
        elif code.startswith("//", i):
            start = i
            i = code.find("\n", i)
            i = n if i == -1 else i
            spans.append((start, i))
        elif code.startswith("/*", i):
            start = i
            end = code.find("*/", i + 2)
            i = n if end == -1 else end + 2
            spans.append((start, i))
        else:
            i += 1
    return spans


def _outside_strings(code: str) -> str:
    """The code with every string and comment blanked out (length preserved)."""
    chars = list(code)
    for start, end in _strip_strings(code):
        for i in range(start, min(end, len(chars))):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def _check_balance(code: str) -> list[dict]:
    """Unbalanced brackets, reported with the line they open or close on."""
    scan = _outside_strings(code)
    pairs = {")": "(", "]": "[", "}": "{"}
    stack, issues = [], []
    line = 1
    for i, ch in enumerate(scan):
        if ch == "\n":
            line += 1
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in pairs:
            if not stack:
                issues.append({"line": line, "problem": f"closing '{ch}' with nothing open"})
            elif stack[-1][0] != pairs[ch]:
                opener, opened_line = stack.pop()
                issues.append({"line": line,
                               "problem": f"'{ch}' does not match '{opener}' opened on line {opened_line}"})
            else:
                stack.pop()
    for opener, opened_line in stack:
        issues.append({"line": opened_line, "problem": f"'{opener}' is never closed"})
    return issues


@register("css-beautifier")
def css_beautifier(files, text: str, options: dict) -> ToolResult:
    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some CSS."})
    indent = " " * max(0, min(_int(options, "indent", 2), 8))
    src = re.sub(r"\s+", " ", re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)) if _flag(
        options, "remove_comments") else re.sub(r"\s+", " ", src)
    out, level = [], 0
    token = ""
    for ch in src:
        if ch == "{":
            out.append(indent * level + token.strip() + " {")
            token = ""
            level += 1
        elif ch == "}":
            if token.strip():
                out.append(indent * level + token.strip())
            token = ""
            level = max(0, level - 1)
            out.append(indent * level + "}")
        elif ch == ";":
            out.append(indent * level + token.strip() + ";")
            token = ""
        else:
            token += ch
    if token.strip():
        out.append(indent * level + token.strip())
    return ToolResult(text="\n".join(ln for ln in out if ln.strip()),
                      meta={"rules": src.count("{")})


@register("js-beautifier")
def js_beautifier(files, text: str, options: dict) -> ToolResult:
    """Re-indents JavaScript and TypeScript by block depth.

    A structural re-indent, not a full parser: it will not rewrap long lines or
    normalise your semicolons, but it never changes what the code does.
    """
    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some JavaScript or TypeScript."})
    indent = " " * max(0, min(_int(options, "indent", 2), 8))
    # Put a line break after every {, } and ; that isn't inside a string, so a
    # minified one-liner has lines to indent in the first place. Done on a masked
    # copy and applied by index, which keeps string contents untouched.
    mask = _outside_strings(src)
    pieces, start = [], 0
    for i, ch in enumerate(mask):
        if ch in "{};":
            pieces.append(src[start:i + 1])
            start = i + 1
    pieces.append(src[start:])
    src = "\n".join(p.strip() for p in pieces if p.strip())
    scan = _outside_strings(src)
    out, level = [], 0
    for raw_line, mask_line in zip(src.split("\n"), scan.split("\n")):
        line = raw_line.strip()
        if not line:
            if _flag(options, "keep_blank_lines", True):
                out.append("")
            continue
        closes_first = mask_line.strip()[:1] in ")]}"
        if closes_first:
            level = max(0, level - 1)
        out.append(indent * level + line)
        opened = sum(mask_line.count(c) for c in "([{")
        closed = sum(mask_line.count(c) for c in ")]}")
        level = max(0, level + opened - closed + (1 if closes_first else 0))
    return ToolResult(text="\n".join(out), meta={"lines": len(out)})


_SQL_KEYWORDS = ("SELECT","FROM","WHERE","INNER JOIN","LEFT JOIN","RIGHT JOIN","FULL JOIN",
                 "CROSS JOIN","JOIN","GROUP BY","ORDER BY","HAVING","LIMIT","OFFSET","UNION ALL",
                 "UNION","INSERT INTO","VALUES","UPDATE","SET","DELETE FROM","CREATE TABLE",
                 "ALTER TABLE","DROP TABLE","ON","AND","OR")


@register("sql-formatter")
def sql_formatter(files, text: str, options: dict) -> ToolResult:
    src = " ".join((text or "").split())
    if not src:
        return ToolResult(meta={"error": "Paste an SQL statement."})
    upper = _flag(options, "uppercase_keywords", True)
    # One alternation, longest keyword first, applied in a single pass. Running a
    # rule per keyword meant "JOIN" re-matched inside text that the "INNER JOIN"
    # rule had already rewritten, splitting it across two lines.
    alternation = "|".join(kw.replace(" ", r"\s+") for kw in
                           sorted(_SQL_KEYWORDS, key=len, reverse=True))
    pattern = re.compile(rf"(?<![\w.])({alternation})(?![\w.])", re.IGNORECASE)
    inline = {"ON", "AND", "OR"}

    def place(match: re.Match) -> str:
        keyword = " ".join(match.group(0).split()).upper()
        shown = keyword if upper else keyword.lower()
        return f"  {shown}" if keyword in inline else f"\n{shown}"

    out = pattern.sub(place, src)
    if _flag(options, "commas_on_new_lines"):
        out = out.replace(", ", ",\n  ")
    # The keyword already had a space in front of it, so the two-space indent
    # for ON/AND/OR came out as three. Normalise the run.
    lines = [re.sub(r" {2,}", "  ", ln).rstrip() for ln in out.split("\n") if ln.strip()]
    formatted = "\n".join(lines)
    return ToolResult(text=formatted if formatted.rstrip().endswith(";") else formatted + ";")


@register("sql-minifier")
def sql_minifier(files, text: str, options: dict) -> ToolResult:
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste an SQL statement."})
    out = re.sub(r"--[^\n]*", " ", src)
    out = re.sub(r"/\*.*?\*/", " ", out, flags=re.DOTALL)
    out = " ".join(out.split())
    out = re.sub(r"\s*([(),;])\s*", r"\1", out)
    return ToolResult(text=out, meta={
        "characters_before": len(src), "characters_after": len(out),
        "saved_percent": round(100 - len(out) / max(1, len(src)) * 100, 1),
    })


@register("xml-formatter")
def xml_formatter(files, text: str, options: dict) -> ToolResult:
    import xml.dom.minidom

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some XML."})
    if len(src) > 2_000_000:
        return ToolResult(meta={"error": "That XML is over 2 MB. Trim it down first."})
    try:
        dom = xml.dom.minidom.parseString(src)
    except Exception as e:  # noqa: BLE001 — minidom raises several unrelated types
        return ToolResult(meta={"error": f"Invalid XML: {e}"})
    if _flag(options, "minify"):
        out = re.sub(r">\s+<", "><", src).strip()
    else:
        indent = " " * max(0, min(_int(options, "indent", 2), 8))
        pretty = dom.toprettyxml(indent=indent)
        # minidom leaves a blank line wherever the source already had whitespace.
        out = "\n".join(ln for ln in pretty.split("\n") if ln.strip())
    return ToolResult(text=out, meta={"root": dom.documentElement.tagName})


@register("html-minifier")
def html_minifier(files, text: str, options: dict) -> ToolResult:
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some HTML."})
    # <pre> and <textarea> render their whitespace, so their contents are lifted
    # out, left untouched, and put back at the end.
    kept: list[str] = []

    def stash(m: re.Match) -> str:
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    out = re.sub(r"<(pre|textarea)\b.*?</\1>", stash, src, flags=re.DOTALL | re.IGNORECASE)
    if _flag(options, "remove_comments", True):
        out = re.sub(r"<!--(?!\[if).*?-->", "", out, flags=re.DOTALL)
    out = re.sub(r">\s+<", "><", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], out).strip()
    return ToolResult(text=out, meta={
        "characters_before": len(src), "characters_after": len(out),
        "saved_percent": round(100 - len(out) / max(1, len(src)) * 100, 1),
    })


@register("js-obfuscator")
def js_obfuscator(files, text: str, options: dict) -> ToolResult:
    """Makes JavaScript hard to read by hiding its string literals.

    It rewrites strings as \\xNN escapes and strips comments. Identifiers are
    deliberately left alone — renaming them is what breaks working code, and
    anyone determined can undo this in a console either way. Treat it as
    discouragement, never as protection.
    """
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some JavaScript."})
    spans = _strip_strings(src)
    pieces, last, hidden = [], 0, 0
    for start, end in spans:
        chunk = src[start:end]
        pieces.append(src[last:start])
        if chunk[:1] in "\"'" and chunk[-1:] == chunk[:1] and len(chunk) >= 2:
            body = chunk[1:-1]
            if "\\" not in body:
                pieces.append('"' + "".join(f"\\x{ord(c):02x}" if ord(c) < 128 else c
                                            for c in body) + '"')
                hidden += 1
            else:
                pieces.append(chunk)
        elif chunk.startswith("//") or chunk.startswith("/*"):
            pieces.append("")  # comment removed
        else:
            pieces.append(chunk)
        last = end
    pieces.append(src[last:])
    out = "".join(pieces)
    if _flag(options, "minify", True):
        out = "\n".join(ln.strip() for ln in out.split("\n") if ln.strip())
    return ToolResult(text=out, meta={
        "strings_hidden": hidden,
        "note": "Obscures the source; it does not protect it. Never hide secrets this way.",
    })


@register("html-validator")
def html_validator(files, text: str, options: dict) -> ToolResult:
    """Checks the mistakes that actually break rendering."""
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some HTML."})
    void = {"area","base","br","col","embed","hr","img","input","link","meta","param",
            "source","track","wbr","!doctype"}
    issues: list[dict] = []
    stack: list[tuple[str, int]] = []
    for m in re.finditer(r"<(/?)([a-zA-Z!][\w!-]*)([^>]*?)(/?)>", src):
        closing, tag, attrs, self_close = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        line = src.count("\n", 0, m.start()) + 1
        if tag in void or self_close:
            continue
        if closing:
            if not stack:
                issues.append({"line": line, "problem": f"</{tag}> with nothing open"})
            elif stack[-1][0] != tag:
                issues.append({"line": line,
                               "problem": f"</{tag}> closes out of order — <{stack[-1][0]}> "
                                          f"opened on line {stack[-1][1]} is still open"})
                stack.pop()
            else:
                stack.pop()
        else:
            stack.append((tag, line))
        if not closing and re.search(r'=\s*[^"\'\s>][^\s>]*', attrs):
            issues.append({"line": line, "problem": f"<{tag}> has an unquoted attribute value"})
    for tag, line in stack:
        issues.append({"line": line, "problem": f"<{tag}> is never closed"})
    for m in re.finditer(r"<img\b(?![^>]*\balt=)[^>]*>", src, re.IGNORECASE):
        issues.append({"line": src.count("\n", 0, m.start()) + 1,
                       "problem": "<img> has no alt attribute"})
    return ToolResult(meta={
        "valid": not issues,
        "issues_found": len(issues),
        "issues": issues[:100],
        "note": "Structural checks — this is not the full W3C validator.",
    })


@register("css-validator")
def css_validator(files, text: str, options: dict) -> ToolResult:
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some CSS."})
    issues = _check_balance(src)
    body = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    for block in re.finditer(r"\{([^{}]*)\}", body):
        base_line = body.count("\n", 0, block.start()) + 1
        for decl in block.group(1).split(";"):
            if not decl.strip():
                continue
            if ":" not in decl:
                issues.append({"line": base_line,
                               "problem": f"declaration with no colon: {decl.strip()[:40]!r}"})
            elif not decl.split(":", 1)[1].strip():
                issues.append({"line": base_line,
                               "problem": f"{decl.split(':')[0].strip()!r} has no value"})
    # A missing final semicolon is legal but is the usual cause of a rule that
    # silently stops working after someone appends to it.
    for block in re.finditer(r"\{([^{}]*[^\s;{}])\s*\}", body):
        issues.append({"line": body.count("\n", 0, block.start()) + 1,
                       "problem": "last declaration has no trailing semicolon"})
    return ToolResult(meta={
        "valid": not issues, "issues_found": len(issues), "issues": issues[:100],
        "rules": body.count("{"),
    })


@register("js-validator")
def js_validator(files, text: str, options: dict) -> ToolResult:
    """Syntax sanity checks, not a linter.

    Real linting means parsing JavaScript, which this server does not do. What
    it can tell you for certain is whether your brackets, quotes and comments
    close — which is what most "why is my script dead" turns out to be.
    """
    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some JavaScript."})
    issues = _check_balance(src)
    scan = _outside_strings(src)
    if src.count("/*") > scan.count("/*") and "*/" not in src[src.rfind("/*"):]:
        issues.append({"line": src.count("\n", 0, src.rfind("/*")) + 1,
                       "problem": "block comment is never closed"})
    for quote in "\"'`":
        # An odd count outside comments usually means a quote was left open.
        if _outside_strings(src).count(quote) % 2:
            issues.append({"line": 0, "problem": f"unbalanced {quote} quote"})
    for m in re.finditer(r"\b(if|while|for)\s*\([^)]*[^=!<>]=[^=][^)]*\)", scan):
        issues.append({"line": src.count("\n", 0, m.start()) + 1,
                       "problem": "assignment (=) inside a condition — did you mean == or ===?"})
    return ToolResult(meta={
        "looks_balanced": not issues, "issues_found": len(issues), "issues": issues[:100],
        "note": "Bracket and quote checks only — this does not parse JavaScript.",
    })


# ===========================================================================
# Hashing, encoding and crypto
# ===========================================================================

_HASHES = ("md5", "sha1", "sha224", "sha256", "sha384", "sha512", "sha3_256", "sha3_512", "blake2b")


@register("hash-generator")
def hash_generator(files, text: str, options: dict) -> ToolResult:
    """Message digests for text.

    MD5 and SHA-1 are included because you still meet them in old checksums and
    legacy APIs — both are broken for anything security-related, and the output
    says so. Never hash a password with these: use bcrypt or Argon2.
    """
    import hashlib

    src = text or ""
    if not src:
        return ToolResult(meta={"error": "Paste some text to hash."})
    wanted = str(options.get("algorithm", "all"))
    algorithms = _HASHES if wanted == "all" else (wanted,)
    if wanted != "all" and wanted not in _HASHES:
        return ToolResult(meta={"error": "Choose one of the listed algorithms."})
    data = src.encode("utf-8")
    digests = {name: hashlib.new(name, data).hexdigest() for name in algorithms}
    if _flag(options, "uppercase"):
        digests = {k: v.upper() for k, v in digests.items()}
    meta: dict = {"input_bytes": len(data), **digests}
    if any(a in ("md5", "sha1") for a in algorithms):
        meta["warning"] = "MD5 and SHA-1 are broken. Use SHA-256 or better for anything that matters."
    return ToolResult(text="\n".join(f"{k}: {v}" for k, v in digests.items()), meta=meta)


@register("file-hash-checker")
def file_hash_checker(files, text: str, options: dict) -> ToolResult:
    """Hash an uploaded file and, optionally, compare it against a published one."""
    import hashlib

    if not files:
        return ToolResult(meta={"error": "Upload a file to hash."})
    algorithm = str(options.get("algorithm", "sha256"))
    if algorithm not in _HASHES:
        return ToolResult(meta={"error": "Choose one of the listed algorithms."})
    digest = hashlib.new(algorithm)
    size = 0
    with open(files[0], "rb") as handle:
        # Read in chunks so a large upload never has to sit in memory whole.
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    result = digest.hexdigest()
    meta = {"file": files[0].name, "size_bytes": size, "algorithm": algorithm, "hash": result}
    expected = str(options.get("expected", "")).strip().lower()
    if expected:
        # Constant-time compare: this is exactly the check an attacker would
        # time, and it costs nothing to do properly.
        meta["matches"] = secrets.compare_digest(result, expected)
    return ToolResult(text=result, meta=meta)


@register("hmac-generator")
def hmac_generator(files, text: str, options: dict) -> ToolResult:
    import hashlib
    import hmac as _hmac

    src = text or ""
    key = str(options.get("key", ""))
    if not src or not key:
        return ToolResult(meta={"error": "Enter both a message and a secret key."})
    algorithm = str(options.get("algorithm", "sha256"))
    if algorithm not in _HASHES:
        return ToolResult(meta={"error": "Choose one of the listed algorithms."})
    mac = _hmac.new(key.encode("utf-8"), src.encode("utf-8"), getattr(hashlib, algorithm))
    hex_digest = mac.hexdigest()
    return ToolResult(text=hex_digest, meta={
        "algorithm": algorithm,
        "hex": hex_digest,
        "base64": base64.b64encode(mac.digest()).decode("ascii"),
    })


@register("crc32-checksum")
def crc32_checksum(files, text: str, options: dict) -> ToolResult:
    import zlib

    src = text or ""
    if not src and not files:
        return ToolResult(meta={"error": "Paste some text or upload a file."})
    if files:
        data = files[0].read_bytes()
        name = files[0].name
    else:
        data = src.encode("utf-8")
        name = None
    crc = zlib.crc32(data) & 0xFFFFFFFF
    adler = zlib.adler32(data) & 0xFFFFFFFF
    return ToolResult(text=f"{crc:08x}", meta={
        "source": name or "pasted text", "bytes": len(data),
        "crc32_hex": f"{crc:08x}", "crc32_decimal": crc,
        "adler32_hex": f"{adler:08x}",
    })


@register("base32-base58-converter")
def base32_base58_converter(files, text: str, options: dict) -> ToolResult:
    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste some text."})
    scheme = str(options.get("scheme", "base32"))
    encoding = str(options.get("mode", "encode")) == "encode"
    # The Bitcoin alphabet: 0, O, I and l are left out because they are the
    # characters people confuse when reading a string aloud.
    b58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    try:
        if scheme == "base58":
            if encoding:
                data = src.encode("utf-8")
                number = int.from_bytes(data, "big")
                out = ""
                while number:
                    number, rem = divmod(number, 58)
                    out = b58[rem] + out
                # Leading zero bytes carry no value but must survive the round trip.
                out = "1" * (len(data) - len(data.lstrip(b"\0"))) + (out or "1")
            else:
                number = 0
                for ch in src:
                    if ch not in b58:
                        return ToolResult(meta={"error": f"{ch!r} is not a Base58 character."})
                    number = number * 58 + b58.index(ch)
                body = number.to_bytes((number.bit_length() + 7) // 8, "big")
                out = (b"\0" * (len(src) - len(src.lstrip("1"))) + body).decode("utf-8")
        else:
            if encoding:
                out = base64.b32encode(src.encode("utf-8")).decode("ascii")
            else:
                padded = src.upper() + "=" * (-len(src.rstrip("=")) % 8)
                out = base64.b32decode(padded).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return ToolResult(meta={"error": f"That isn't valid {scheme} input."})
    return ToolResult(text=out, meta={"scheme": scheme})


@register("jwt-decoder")
def jwt_decoder(files, text: str, options: dict) -> ToolResult:
    """Reads a JWT's header and payload without verifying it.

    Decoding is not verification. Anyone can change a payload and re-encode it;
    only checking the signature against the issuer's key proves a token is real.
    The claims below are shown for inspection, never as something to trust.
    """
    from datetime import datetime, timezone

    token = (text or "").strip().replace("Bearer ", "")
    parts = token.split(".")
    if len(parts) not in (2, 3):
        return ToolResult(meta={"error": "A JWT has three dot-separated parts."})

    def segment(raw: str) -> dict | None:
        try:
            return json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return None

    header, payload = segment(parts[0]), segment(parts[1])
    if header is None or payload is None:
        return ToolResult(meta={"error": "That isn't a readable JWT."})
    readable = {}
    for claim in ("exp", "iat", "nbf"):
        if isinstance(payload.get(claim), (int, float)):
            readable[claim] = datetime.fromtimestamp(payload[claim], timezone.utc).isoformat()
    expired = None
    if isinstance(payload.get("exp"), (int, float)):
        expired = datetime.now(timezone.utc).timestamp() > payload["exp"]
    return ToolResult(
        text=json.dumps({"header": header, "payload": payload}, indent=2, ensure_ascii=False),
        meta={
            "algorithm": header.get("alg"),
            "expired": expired,
            "timestamps": readable,
            "signature_present": len(parts) == 3 and bool(parts[2]),
            "warning": "Decoded only — the signature has NOT been verified.",
        })


@register("jwt-encoder")
def jwt_encoder(files, text: str, options: dict) -> ToolResult:
    """Signs a JSON payload into a JWT with HMAC.

    Only the HS family is offered: RS/ES signing needs a private key, and asking
    people to paste a private key into a website is the wrong habit to teach.
    """
    from jose import jwt as jose_jwt

    payload, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": "Paste the payload as JSON, e.g. " '{"sub": "123"}'})
    if not isinstance(payload, dict):
        return ToolResult(meta={"error": "The payload must be a JSON object."})
    secret = str(options.get("secret", ""))
    if len(secret) < 8:
        return ToolResult(meta={"error": "Use a secret of at least 8 characters."})
    algorithm = str(options.get("algorithm", "HS256"))
    if algorithm not in {"HS256", "HS384", "HS512"}:
        return ToolResult(meta={"error": "Choose HS256, HS384 or HS512."})
    minutes = _int(options, "expires_minutes", 0)
    if minutes > 0:
        from datetime import datetime, timedelta, timezone
        payload = {**payload,
                   "exp": int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())}
    token = jose_jwt.encode(payload, secret, algorithm=algorithm)
    return ToolResult(text=token, meta={
        "algorithm": algorithm,
        "note": "Generated in the open — never sign a production token on a public website.",
    })


@register("aes-encrypt-decrypt")
def aes_encrypt_decrypt(files, text: str, options: dict) -> ToolResult:
    """AES-256-GCM with a passphrase.

    GCM, not CBC: it authenticates as well as encrypts, so tampered ciphertext
    fails loudly instead of decrypting to garbage. The key comes from PBKDF2 with
    a random salt, and both salt and nonce are stored with the output — which is
    why encrypting the same text twice gives different results. That is correct.

    This runs on the server. Anything genuinely sensitive should not be pasted
    into a website at all, whoever runs it.
    """
    from cryptography.hazmat.primitives import hashes as _hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    src = text or ""
    password = str(options.get("password", ""))
    if not src.strip():
        return ToolResult(meta={"error": "Paste the text to encrypt or decrypt."})
    if len(password) < 8:
        return ToolResult(meta={"error": "Use a passphrase of at least 8 characters."})

    def derive(salt: bytes) -> bytes:
        return PBKDF2HMAC(algorithm=_hashes.SHA256(), length=32, salt=salt,
                          iterations=200_000).derive(password.encode("utf-8"))

    if str(options.get("mode", "encrypt")) == "encrypt":
        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        blob = AESGCM(derive(salt)).encrypt(nonce, src.encode("utf-8"), None)
        return ToolResult(text=base64.b64encode(salt + nonce + blob).decode("ascii"),
                          meta={"cipher": "AES-256-GCM", "kdf": "PBKDF2-SHA256, 200k iterations"})
    try:
        raw = base64.b64decode(src.strip())
        salt, nonce, blob = raw[:16], raw[16:28], raw[28:]
        plain = AESGCM(derive(salt)).decrypt(nonce, blob, None)
        return ToolResult(text=plain.decode("utf-8"), meta={"cipher": "AES-256-GCM"})
    except Exception:  # noqa: BLE001 — wrong password and tampering both land here
        return ToolResult(meta={"error": "Could not decrypt. Wrong passphrase, or the text was altered."})


@register("gzip-compressor")
def gzip_compressor(files, text: str, options: dict) -> ToolResult:
    import gzip
    import zlib

    src = text or ""
    if not src.strip():
        return ToolResult(meta={"error": "Paste some text."})
    algorithm = str(options.get("algorithm", "gzip"))
    if str(options.get("mode", "compress")) == "compress":
        data = src.encode("utf-8")
        level = max(1, min(_int(options, "level", 9), 9))
        packed = (gzip.compress(data, level) if algorithm == "gzip"
                  else zlib.compress(data, level))
        return ToolResult(text=base64.b64encode(packed).decode("ascii"), meta={
            "original_bytes": len(data), "compressed_bytes": len(packed),
            "saved_percent": round(100 - len(packed) / max(1, len(data)) * 100, 1),
            "note": "Output is Base64 so it survives copy and paste.",
        })
    # Decompressed INCREMENTALLY with a ceiling, not in one call. A 250 KB paste
    # expands to 200 MB in under a tenth of a second, and a handful of those at
    # once is enough to have the box kill the whole process.
    limit = 8 * 1024 * 1024
    try:
        raw = base64.b64decode(src.strip())
        # 16 + MAX_WBITS tells zlib the stream carries a gzip header.
        stream = zlib.decompressobj(16 + zlib.MAX_WBITS if algorithm == "gzip" else zlib.MAX_WBITS)
        data = stream.decompress(raw, limit)
        if stream.unconsumed_tail or not stream.eof:
            return ToolResult(meta={
                "error": f"That expands to more than {limit // (1024 * 1024)} MB. "
                         "Decompress it locally instead."
            })
        return ToolResult(text=data.decode("utf-8"), meta={"bytes": len(data)})
    except Exception:  # noqa: BLE001 — several unrelated exception types
        return ToolResult(meta={"error": "That isn't valid Base64-encoded compressed data."})


@register("escape-unescape-string")
def escape_unescape_string(files, text: str, options: dict) -> ToolResult:
    """String escaping for the language you are pasting into."""
    import html as _html

    src = text or ""
    if not src:
        return ToolResult(meta={"error": "Paste some text."})
    language = str(options.get("language", "javascript"))
    escaping = str(options.get("mode", "escape")) == "escape"
    try:
        if language == "html":
            out = _html.escape(src, quote=True) if escaping else _html.unescape(src)
        elif language == "sql":
            out = src.replace("'", "''") if escaping else src.replace("''", "'")
        elif language == "csv":
            out = ('"' + src.replace('"', '""') + '"') if escaping else \
                  src.strip('"').replace('""', '"')
        elif language == "regex":
            out = re.escape(src) if escaping else re.sub(r"\\(.)", r"\1", src)
        elif language == "shell":
            out = "'" + src.replace("'", "'\\''") + "'" if escaping else \
                  src.strip("'").replace("'\\''", "'")
        elif language == "json":
            out = json.dumps(src) if escaping else json.loads(src)
        else:  # javascript / python — both use backslash escapes
            if escaping:
                out = json.dumps(src)[1:-1]
            else:
                out = json.loads('"' + src.replace('"', '\\"') + '"')
    except (json.JSONDecodeError, ValueError):
        return ToolResult(meta={"error": "That text isn't escaped in the way this language expects."})
    return ToolResult(text=out, meta={"language": language})


@register("htpasswd-generator")
def htpasswd_generator(files, text: str, options: dict) -> ToolResult:
    """An Apache/nginx .htpasswd line.

    bcrypt is the default because it is the only option here with a real work
    factor. MD5-crypt and SHA-1 are offered for servers that still require them,
    and are labelled as the weak choices they are.
    """
    username = str(options.get("username", "")).strip()
    password = str(options.get("password", ""))
    if not username or not password:
        return ToolResult(meta={"error": "Enter both a username and a password."})
    if ":" in username:
        return ToolResult(meta={"error": "A username cannot contain a colon."})
    scheme = str(options.get("scheme", "bcrypt"))
    if scheme == "bcrypt":
        import bcrypt as _bcrypt
        rounds = max(4, min(_int(options, "rounds", 12), 15))
        digest = _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt(rounds)).decode("ascii")
        note = f"bcrypt, cost {rounds}"
    elif scheme == "sha1":
        import hashlib
        digest = "{SHA}" + base64.b64encode(hashlib.sha1(password.encode("utf-8")).digest()).decode()
        note = "SHA-1 — unsalted and fast to crack. Only for servers that demand it."
    else:
        from passlib.hash import apr_md5_crypt
        digest = apr_md5_crypt.hash(password)
        note = "Apache MD5 — weak by modern standards, but widely supported."
    return ToolResult(text=f"{username}:{digest}", meta={"scheme": scheme, "note": note})


@register("credit-card-validator")
def credit_card_validator(files, text: str, options: dict) -> ToolResult:
    """Checks a card number's Luhn checksum and identifies the issuer.

    A structural check only: it proves the digits are self-consistent, never
    that the card exists, is funded, or belongs to anyone. Nothing is stored.
    """
    digits = re.sub(r"\D", "", text or "")
    if not digits:
        return ToolResult(meta={"error": "Enter a card number."})
    if not 12 <= len(digits) <= 19:
        return ToolResult(meta={"error": "Card numbers are 12 to 19 digits long."})
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    brands = [
        ("Visa", r"^4\d{12}(\d{3})?(\d{3})?$"),
        ("Mastercard", r"^(5[1-5]\d{14}|2(2[2-9]\d{12}|[3-6]\d{13}|7[01]\d{12}|720\d{12}))$"),
        ("American Express", r"^3[47]\d{13}$"),
        ("Discover", r"^6(?:011|5\d{2}|4[4-9]\d)\d{12}$"),
        ("JCB", r"^35(?:2[89]|[3-8]\d)\d{12}$"),
        ("Diners Club", r"^3(?:0[0-5]|[68]\d)\d{11}$"),
        ("UnionPay", r"^62\d{14,17}$"),
    ]
    brand = next((name for name, pattern in brands if re.match(pattern, digits)), "Unknown")
    return ToolResult(meta={
        "valid_checksum": total % 10 == 0,
        "brand": brand,
        "digits": len(digits),
        "masked": digits[:4] + "*" * (len(digits) - 8) + digits[-4:] if len(digits) > 8 else "****",
        "note": "Luhn check only — this says nothing about whether the card is real or active.",
    })


# ===========================================================================
# Colour and CSS
# ===========================================================================

def _parse_color(value: str) -> tuple[int, int, int, float] | None:
    """Accepts hex (3, 4, 6 or 8 digits), rgb()/rgba() and hsl()/hsla()."""
    import colorsys

    raw = (value or "").strip().lower()
    if not raw:
        return None
    hex_match = re.fullmatch(r"#?([0-9a-f]{3,8})", raw)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) in (3, 4):
            digits = "".join(c * 2 for c in digits)
        if len(digits) == 6:
            r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
            return r, g, b, 1.0
        if len(digits) == 8:
            r, g, b, a = (int(digits[i:i + 2], 16) for i in (0, 2, 4, 6))
            return r, g, b, round(a / 255, 3)
        return None
    numbers = re.findall(r"-?\d*\.?\d+", raw)
    if raw.startswith("rgb") and len(numbers) >= 3:
        r, g, b = (max(0, min(255, int(float(n)))) for n in numbers[:3])
        return r, g, b, float(numbers[3]) if len(numbers) > 3 else 1.0
    if raw.startswith("hsl") and len(numbers) >= 3:
        h = float(numbers[0]) % 360 / 360
        s = max(0.0, min(1.0, float(numbers[1]) / 100))
        light = max(0.0, min(1.0, float(numbers[2]) / 100))
        r, g, b = (round(c * 255) for c in colorsys.hls_to_rgb(h, light, s))
        return int(r), int(g), int(b), float(numbers[3]) if len(numbers) > 3 else 1.0
    return None


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAG relative luminance — the gamma step is what makes it perceptual."""
    channels = []
    for c in rgb:
        c = c / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


@register("color-converter")
def color_converter(files, text: str, options: dict) -> ToolResult:
    import colorsys

    parsed = _parse_color(text or str(options.get("color", "")))
    if parsed is None:
        return ToolResult(meta={"error": "Enter a colour as #hex, rgb(...) or hsl(...)."})
    r, g, b, a = parsed
    h, light, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    k = 1 - max(r, g, b) / 255
    cmyk = (0, 0, 0, 100) if k == 1 else tuple(
        round(x * 100) for x in ((1 - r / 255 - k) / (1 - k), (1 - g / 255 - k) / (1 - k),
                                 (1 - b / 255 - k) / (1 - k), k))
    return ToolResult(meta={
        "hex": f"#{r:02x}{g:02x}{b:02x}",
        "hex_with_alpha": f"#{r:02x}{g:02x}{b:02x}{round(a * 255):02x}",
        "rgb": f"rgb({r}, {g}, {b})",
        "rgba": f"rgba({r}, {g}, {b}, {a})",
        "hsl": f"hsl({round(h * 360)}, {round(s * 100)}%, {round(light * 100)}%)",
        "hsv": f"hsv({round(hue * 360)}, {round(sat * 100)}%, {round(val * 100)}%)",
        "cmyk": f"cmyk({cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%)",
        "luminance": round(_relative_luminance((r, g, b)), 4),
        "is_dark": _relative_luminance((r, g, b)) < 0.5,
    })


@register("contrast-checker")
def contrast_checker(files, text: str, options: dict) -> ToolResult:
    """WCAG contrast ratio, with the pass/fail thresholds spelled out."""
    fg = _parse_color(text or str(options.get("foreground", "")))
    bg = _parse_color(str(options.get("background", "#ffffff")))
    if fg is None or bg is None:
        return ToolResult(meta={"error": "Enter both colours as #hex, rgb(...) or hsl(...)."})
    l1, l2 = _relative_luminance(fg[:3]), _relative_luminance(bg[:3])
    lighter, darker = max(l1, l2), min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return ToolResult(meta={
        "contrast_ratio": f"{ratio:.2f}:1",
        "normal_text_aa": ratio >= 4.5,
        "normal_text_aaa": ratio >= 7,
        "large_text_aa": ratio >= 3,
        "large_text_aaa": ratio >= 4.5,
        "ui_components_aa": ratio >= 3,
        "verdict": ("Passes AAA" if ratio >= 7 else "Passes AA" if ratio >= 4.5
                    else "Large text only" if ratio >= 3 else "Fails WCAG"),
        "note": "Large text means 18pt, or 14pt bold, and above.",
    })


@register("css-gradient-generator")
def css_gradient_generator(files, text: str, options: dict) -> ToolResult:
    colors = [c.strip() for c in re.split(r"[,\n]+", text or "") if c.strip()]
    if len(colors) < 2:
        colors = [str(options.get("color_1", "#4f46e5")), str(options.get("color_2", "#ec4899"))]
    parsed = [_parse_color(c) for c in colors]
    if any(p is None for p in parsed):
        return ToolResult(meta={"error": "One of those colours could not be read."})
    stops = ", ".join(f"#{p[0]:02x}{p[1]:02x}{p[2]:02x}" for p in parsed)
    kind = str(options.get("type", "linear"))
    if kind == "radial":
        css = f"radial-gradient(circle, {stops})"
    elif kind == "conic":
        css = f"conic-gradient(from {_int(options, 'angle', 90)}deg, {stops})"
    else:
        css = f"linear-gradient({_int(options, 'angle', 90)}deg, {stops})"
    return ToolResult(text=f"background: {css};", meta={"gradient": css, "stops": len(parsed)})


@register("box-shadow-generator")
def box_shadow_generator(files, text: str, options: dict) -> ToolResult:
    color = _parse_color(str(options.get("color", "#000000"))) or (0, 0, 0, 1.0)
    opacity = max(0.0, min(float(str(options.get("opacity", 0.25)) or 0.25), 1.0))
    shadow = (f"{_int(options, 'x', 0)}px {_int(options, 'y', 4)}px "
              f"{_int(options, 'blur', 12)}px {_int(options, 'spread', 0)}px "
              f"rgba({color[0]}, {color[1]}, {color[2]}, {opacity})")
    if _flag(options, "inset"):
        shadow = "inset " + shadow
    radius = _int(options, "border_radius", 12)
    return ToolResult(text=f"box-shadow: {shadow};\nborder-radius: {radius}px;",
                      meta={"box_shadow": shadow, "border_radius": f"{radius}px"})


@register("flexbox-grid-generator")
def flexbox_grid_generator(files, text: str, options: dict) -> ToolResult:
    gap = _int(options, "gap", 16)
    if str(options.get("layout", "flex")) == "grid":
        columns = max(1, min(_int(options, "columns", 3), 12))
        mode = str(options.get("column_mode", "equal"))
        template = ("repeat(auto-fit, minmax(220px, 1fr))" if mode == "responsive"
                    else f"repeat({columns}, 1fr)")
        css = (".container {\n  display: grid;\n"
               f"  grid-template-columns: {template};\n"
               f"  gap: {gap}px;\n"
               f"  align-items: {options.get('align', 'stretch')};\n}}")
    else:
        css = (".container {\n  display: flex;\n"
               f"  flex-direction: {options.get('direction', 'row')};\n"
               f"  justify-content: {options.get('justify', 'flex-start')};\n"
               f"  align-items: {options.get('align', 'stretch')};\n"
               f"  flex-wrap: {'wrap' if _flag(options, 'wrap', True) else 'nowrap'};\n"
               f"  gap: {gap}px;\n}}")
    return ToolResult(text=css)


_EASINGS = {
    "ease": (0.25, 0.1, 0.25, 1.0), "ease-in": (0.42, 0, 1.0, 1.0),
    "ease-out": (0, 0, 0.58, 1.0), "ease-in-out": (0.42, 0, 0.58, 1.0),
    "ease-in-quad": (0.11, 0, 0.5, 0), "ease-out-quad": (0.5, 1, 0.89, 1),
    "ease-in-out-quad": (0.45, 0, 0.55, 1), "ease-in-cubic": (0.32, 0, 0.67, 0),
    "ease-out-cubic": (0.33, 1, 0.68, 1), "ease-in-out-cubic": (0.65, 0, 0.35, 1),
    "ease-out-back": (0.34, 1.56, 0.64, 1), "ease-in-out-back": (0.68, -0.6, 0.32, 1.6),
    "linear": (0, 0, 1, 1),
}


@register("cubic-bezier-generator")
def cubic_bezier_generator(files, text: str, options: dict) -> ToolResult:
    """A named easing curve, or your own control points, plus a sampled preview."""
    preset = str(options.get("preset", "custom"))
    if preset in _EASINGS:
        x1, y1, x2, y2 = _EASINGS[preset]
    else:
        try:
            x1 = float(str(options.get("x1", 0.25)))
            y1 = float(str(options.get("y1", 0.1)))
            x2 = float(str(options.get("x2", 0.25)))
            y2 = float(str(options.get("y2", 1.0)))
        except ValueError:
            return ToolResult(meta={"error": "Control points must be numbers."})
    if not (0 <= x1 <= 1 and 0 <= x2 <= 1):
        return ToolResult(meta={"error": "x1 and x2 must be between 0 and 1 — CSS requires it."})

    def bezier(t: float, a: float, b: float) -> float:
        return 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t ** 2 * b + t ** 3

    samples = [round(bezier(i / 10, y1, y2), 3) for i in range(11)]
    curve = f"cubic-bezier({x1}, {y1}, {x2}, {y2})"
    duration = _int(options, "duration_ms", 300)
    return ToolResult(
        text=f"transition: all {duration}ms {curve};\nanimation-timing-function: {curve};",
        meta={"curve": curve, "progress_at_each_10_percent": samples})


_CSS_UNITS = {"px": 1.0, "pt": 96 / 72, "pc": 16.0, "in": 96.0, "cm": 96 / 2.54, "mm": 96 / 25.4}


@register("css-unit-converter")
def css_unit_converter(files, text: str, options: dict) -> ToolResult:
    """Between px, rem, em, %, pt and the physical units.

    rem, em and % are all relative, so they need a base to convert from —
    that is what the root and parent font sizes below are for.
    """
    try:
        value = float(str(text or options.get("value", 16)).strip() or 16)
    except ValueError:
        return ToolResult(meta={"error": "Enter a number to convert."})
    root = float(str(options.get("root_font_size", 16)) or 16)
    parent = float(str(options.get("parent_font_size", 16)) or 16)
    unit = str(options.get("from", "px"))
    if root <= 0 or parent <= 0:
        return ToolResult(meta={"error": "Font sizes must be above zero."})
    if unit == "rem":
        px = value * root
    elif unit == "em":
        px = value * parent
    elif unit == "%":
        px = value / 100 * parent
    elif unit in _CSS_UNITS:
        px = value * _CSS_UNITS[unit]
    else:
        return ToolResult(meta={"error": "Choose one of the listed units."})
    out = {"px": round(px, 4), "rem": round(px / root, 4), "em": round(px / parent, 4),
           "percent": round(px / parent * 100, 2)}
    out.update({u: round(px / factor, 4) for u, factor in _CSS_UNITS.items() if u != "px"})
    return ToolResult(meta=out)


# ===========================================================================
# Time and numbers
# ===========================================================================

@register("unix-timestamp-converter")
def unix_timestamp_converter(files, text: str, options: dict) -> ToolResult:
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo, available_timezones

    raw = (text or "").strip()
    zone_name = str(options.get("timezone", "UTC")).strip() or "UTC"
    if zone_name not in available_timezones():
        return ToolResult(meta={"error": f"Unknown time zone: {zone_name}. Try UTC or Asia/Karachi."})
    zone = ZoneInfo(zone_name)
    if not raw:
        now = datetime.now(timezone.utc)
        return ToolResult(text=str(int(now.timestamp())), meta={
            "seconds": int(now.timestamp()), "milliseconds": int(now.timestamp() * 1000),
            "utc": now.isoformat(), "local": now.astimezone(zone).isoformat(),
        })
    if re.fullmatch(r"-?\d{1,19}", raw):
        number = int(raw)
        # 13 digits is milliseconds, 16 is microseconds — guessing from the
        # magnitude is what every other converter does, and it is what people
        # paste without thinking about the unit.
        if abs(number) > 10 ** 14:
            seconds, unit = number / 1_000_000, "microseconds"
        elif abs(number) > 10 ** 11:
            seconds, unit = number / 1000, "milliseconds"
        else:
            seconds, unit = float(number), "seconds"
        try:
            moment = datetime.fromtimestamp(seconds, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return ToolResult(meta={"error": "That timestamp is outside the supported range."})
        return ToolResult(text=moment.astimezone(zone).isoformat(), meta={
            "read_as": unit, "seconds": int(seconds),
            "utc": moment.isoformat(), zone_name: moment.astimezone(zone).isoformat(),
            "day": moment.strftime("%A"), "relative_days_from_now":
                round((moment - datetime.now(timezone.utc)).total_seconds() / 86400, 2),
        })
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return ToolResult(meta={"error": "Enter a Unix timestamp, or a date as YYYY-MM-DD HH:MM."})
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return ToolResult(text=str(int(parsed.timestamp())), meta={
        "seconds": int(parsed.timestamp()), "milliseconds": int(parsed.timestamp() * 1000),
        "utc": parsed.astimezone(timezone.utc).isoformat(),
    })


_BYTE_UNITS = {"B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4,
               "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3, "TiB": 1024 ** 4}


@register("byte-size-converter")
def byte_size_converter(files, text: str, options: dict) -> ToolResult:
    """Between every data-size unit, keeping KB and KiB apart.

    Both scales are shown side by side because they are not the same: a "1 TB"
    drive holds 1000^4 bytes, which a computer reports as about 0.91 TiB. That
    gap is where the missing space goes.
    """
    try:
        value = float(str(text or options.get("value", 1)).strip() or 1)
    except ValueError:
        return ToolResult(meta={"error": "Enter a number."})
    unit = str(options.get("from", "MB"))
    if unit not in _BYTE_UNITS:
        return ToolResult(meta={"error": "Choose one of the listed units."})
    total = value * _BYTE_UNITS[unit]
    out = {name: round(total / factor, 6) for name, factor in _BYTE_UNITS.items()}
    out["bits"] = round(total * 8)
    return ToolResult(meta=out)


@register("ieee754-converter")
def ieee754_converter(files, text: str, options: dict) -> ToolResult:
    """A float's exact bit pattern — and the value those bits really hold."""
    import struct

    raw = (text or "").strip()
    if not raw:
        return ToolResult(meta={"error": "Enter a decimal number, or a hex bit pattern."})
    precision = str(options.get("precision", "64"))
    fmt, bits = (">f", 32) if precision == "32" else (">d", 64)
    hex_match = re.fullmatch(r"(?:0x)?([0-9a-fA-F]+)", raw)
    if hex_match and len(hex_match.group(1)) == bits // 4:
        packed = bytes.fromhex(hex_match.group(1))
        value = struct.unpack(fmt, packed)[0]
    else:
        try:
            value = float(raw)
        except ValueError:
            return ToolResult(meta={"error": "Enter a decimal number, or a full hex bit pattern."})
        packed = struct.pack(fmt, value)
    binary = "".join(f"{b:08b}" for b in packed)
    exponent_bits = 8 if bits == 32 else 11
    stored = struct.unpack(fmt, packed)[0]
    return ToolResult(meta={
        "input": raw,
        "stored_value": stored,
        "exact_decimal": f"{stored:.17g}",
        "hex": packed.hex(),
        "binary": binary,
        "sign": "negative" if binary[0] == "1" else "positive",
        "exponent_bits": binary[1:1 + exponent_bits],
        "mantissa_bits": binary[1 + exponent_bits:],
        "note": "Where stored_value differs from your input, that is float rounding, not a bug.",
    })


_CRON_FIELDS = ("minute", "hour", "day of month", "month", "day of week")
_CRON_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


@register("cron-expression-tool")
def cron_expression_tool(files, text: str, options: dict) -> ToolResult:
    """Explains a cron expression in plain English, and lists its next runs."""
    from datetime import datetime, timedelta

    expression = " ".join((text or "").split())
    shortcuts = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
                 "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
                 "@hourly": "0 * * * *"}
    expression = shortcuts.get(expression, expression)
    if not expression:
        return ToolResult(meta={"error": "Enter a cron expression, e.g. 0 9 * * 1-5"})
    parts = expression.split()
    if len(parts) != 5:
        return ToolResult(meta={"error": f"A cron expression has 5 fields, not {len(parts)}."})

    def expand(field: str, low: int, high: int) -> set[int] | None:
        values: set[int] = set()
        for chunk in field.split(","):
            step = 1
            if "/" in chunk:
                chunk, _, raw_step = chunk.partition("/")
                if not raw_step.isdigit() or int(raw_step) == 0:
                    return None
                step = int(raw_step)
            if chunk in ("*", "?"):
                start, end = low, high
            elif "-" in chunk.lstrip("-"):
                a, _, b = chunk.partition("-")
                if not (a.isdigit() and b.isdigit()):
                    return None
                start, end = int(a), int(b)
            elif chunk.isdigit():
                start = end = int(chunk)
            else:
                return None
            if start < low or end > high or start > end:
                return None
            values.update(range(start, end + 1, step))
        return values

    expanded = []
    for field, name, (low, high) in zip(parts, _CRON_FIELDS, _CRON_RANGES):
        values = expand(field, low, high)
        if values is None:
            return ToolResult(meta={"error": f"The {name} field ({field!r}) isn't valid."})
        expanded.append(values)
    minutes, hours, days, months, weekdays = expanded
    weekdays = {0 if d == 7 else d for d in weekdays}  # cron accepts both 0 and 7 for Sunday

    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_words = "every day" if len(weekdays) >= 7 else ", ".join(
        names[(d - 1) % 7] for d in sorted(weekdays))
    when = ("every minute" if len(minutes) == 60 and len(hours) == 24
            else f"at {', '.join(f'{h:02d}:{m:02d}' for h in sorted(hours)[:4] for m in sorted(minutes)[:4])}")

    now = datetime.now().replace(second=0, microsecond=0)
    upcoming, cursor = [], now + timedelta(minutes=1)
    # Scan a year ahead at most, so an expression that can never fire (31 February)
    # stops instead of looping forever.
    for _ in range(527_040):
        if (cursor.minute in minutes and cursor.hour in hours and cursor.day in days
                and cursor.month in months and (cursor.weekday() + 1) % 7 in weekdays):
            upcoming.append(cursor.strftime("%Y-%m-%d %H:%M (%A)"))
            if len(upcoming) >= 5:
                break
        cursor += timedelta(minutes=1)
    return ToolResult(meta={
        "expression": expression,
        "explanation": f"Runs {when}, on {day_words}.",
        "next_runs": upcoming or ["This expression never fires — check the date fields."],
        "fields": {name: field for name, field in zip(_CRON_FIELDS, parts)},
    })


# ===========================================================================
# Network
# ===========================================================================

@register("subnet-calculator")
def subnet_calculator(files, text: str, options: dict) -> ToolResult:
    """CIDR maths for IPv4 and IPv6, from the stdlib's own address library."""
    import ipaddress

    raw = (text or "").strip() or str(options.get("cidr", ""))
    if not raw:
        return ToolResult(meta={"error": "Enter a network, e.g. 192.168.1.0/24"})
    try:
        network = ipaddress.ip_network(raw, strict=False)
    except ValueError as e:
        return ToolResult(meta={"error": f"Not a valid network: {e}"})
    meta: dict = {
        "network": str(network.network_address),
        "prefix": f"/{network.prefixlen}",
        "version": f"IPv{network.version}",
        "total_addresses": network.num_addresses,
        "is_private": network.is_private,
    }
    if network.version == 4:
        hosts = max(0, network.num_addresses - 2) if network.prefixlen < 31 else network.num_addresses
        meta.update({
            "netmask": str(network.netmask),
            "wildcard": str(network.hostmask),
            "broadcast": str(network.broadcast_address),
            "usable_hosts": hosts,
            "first_host": str(network.network_address + 1) if hosts and network.prefixlen < 31 else str(network.network_address),
            "last_host": str(network.broadcast_address - 1) if hosts and network.prefixlen < 31 else str(network.broadcast_address),
        })
    else:
        meta["first_address"] = str(network.network_address)
        meta["last_address"] = str(network.broadcast_address)
    return ToolResult(meta=meta)


@register("user-agent-parser")
def user_agent_parser(files, text: str, options: dict) -> ToolResult:
    """Reads a User-Agent string.

    Pattern matching over a string the client controls entirely — useful for
    reading your own logs, never a basis for a security decision.
    """
    ua = (text or "").strip()
    if not ua:
        return ToolResult(meta={"error": "Paste a User-Agent string."})

    def find(patterns: list[tuple[str, str]]) -> tuple[str, str | None]:
        for name, pattern in patterns:
            m = re.search(pattern, ua, re.IGNORECASE)
            if m:
                return name, (m.group(1) if m.groups() else None)
        return "Unknown", None

    # Order matters: Edge and Opera both carry "Chrome", and Chrome carries
    # "Safari", so the more specific names have to be tested first.
    browser, browser_version = find([
        ("Edge", r"Edg(?:e|A|iOS)?/([\d.]+)"), ("Opera", r"OPR/([\d.]+)"),
        ("Samsung Internet", r"SamsungBrowser/([\d.]+)"),
        ("Chrome", r"Chrome/([\d.]+)"), ("Firefox", r"Firefox/([\d.]+)"),
        ("Safari", r"Version/([\d.]+).*Safari"), ("Internet Explorer", r"MSIE ([\d.]+)|rv:([\d.]+)\) like Gecko"),
    ])
    os_name, os_version = find([
        ("Windows", r"Windows NT ([\d.]+)"), ("Android", r"Android ([\d.]+)"),
        ("iOS", r"(?:iPhone )?OS ([\d_]+)"), ("macOS", r"Mac OS X ([\d_]+)"),
        ("Chrome OS", r"CrOS \S+ ([\d.]+)"), ("Linux", r"(Linux)"),
    ])
    windows = {"10.0": "10 or 11", "6.3": "8.1", "6.2": "8", "6.1": "7"}
    if os_name == "Windows" and os_version in windows:
        os_version = windows[os_version]
    is_bot = bool(re.search(r"bot|crawl|spider|slurp|bingpreview|headless", ua, re.IGNORECASE))
    mobile = bool(re.search(r"Mobi|Android|iPhone|iPad|iPod", ua, re.IGNORECASE))
    return ToolResult(meta={
        "browser": browser, "browser_version": browser_version,
        "operating_system": os_name,
        "os_version": (os_version or "").replace("_", ".") or None,
        "device_type": "Bot" if is_bot else ("Tablet" if "iPad" in ua or ("Android" in ua and "Mobi" not in ua) else "Mobile" if mobile else "Desktop"),
        "is_bot": is_bot,
        "note": "A User-Agent is self-reported and trivially faked. Never gate access on it.",
    })


# ===========================================================================
# Regex
# ===========================================================================

@register("regex-tester")
def regex_tester(files, text: str, options: dict) -> ToolResult:
    """Tests a pattern against your text and shows every match and group.

    Compiled with a guard on pattern length: a short pattern like (a+)+$ can be
    made to take exponential time on the right input, and this runs server-side.
    """
    from app.core.regex_guard import UnsafePattern, compile_pattern, find_all, substitute

    pattern_src = str(options.get("pattern", ""))
    if not pattern_src:
        return ToolResult(meta={"error": "Enter a regular expression."})
    subject = text or ""
    if len(subject) > 200_000:
        return ToolResult(meta={"error": "Test against 200 KB of text or less."})
    flags = 0
    if _flag(options, "ignore_case"):
        flags |= re.IGNORECASE
    if _flag(options, "multiline"):
        flags |= re.MULTILINE
    if _flag(options, "dot_all"):
        flags |= re.DOTALL
    try:
        pattern = compile_pattern(pattern_src, flags)
        found = find_all(pattern, subject)
    except UnsafePattern as e:
        return ToolResult(meta={"error": str(e)})
    matches = []
    for m in found:
        entry = {"match": m.group(0), "start": m.start(), "end": m.end(),
                 "line": subject.count("\n", 0, m.start()) + 1}
        if m.groups():
            entry["groups"] = list(m.groups())
        if m.groupdict():
            entry["named_groups"] = m.groupdict()
        matches.append(entry)
    replacement = options.get("replace_with")
    result: dict = {
        "pattern": pattern_src,
        "matches": len(matches),
        "group_count": pattern.groups,
        "results": matches,
    }
    output = "\n".join(m["match"] for m in matches)
    if isinstance(replacement, str) and replacement != "":
        try:
            output, _ = substitute(pattern, replacement, subject)
            result["mode"] = "replaced"
        except (UnsafePattern, re.error) as e:
            return ToolResult(meta={"error": str(e)})
    return ToolResult(text=output, meta=result)


_REGEX_REFERENCE = [
    ("Characters", [(".", "any character except a newline"), ("\\d", "digit 0-9"),
                    ("\\D", "not a digit"), ("\\w", "letter, digit or underscore"),
                    ("\\W", "not a word character"), ("\\s", "whitespace"),
                    ("\\S", "not whitespace"), ("[abc]", "a, b or c"),
                    ("[^abc]", "anything except a, b or c"), ("[a-z]", "any lowercase letter")]),
    ("Repetition", [("*", "0 or more"), ("+", "1 or more"), ("?", "0 or 1"),
                    ("{3}", "exactly 3"), ("{2,}", "2 or more"), ("{2,5}", "between 2 and 5"),
                    ("*?", "0 or more, as few as possible")]),
    ("Anchors", [("^", "start of the string, or of a line with the m flag"),
                 ("$", "end of the string, or of a line with the m flag"),
                 ("\\b", "word boundary"), ("\\B", "not a word boundary")]),
    ("Groups", [("(abc)", "capturing group"), ("(?:abc)", "group without capturing"),
                ("(?<name>abc)", "named group"), ("a|b", "a or b"),
                ("\\1", "whatever group 1 matched")]),
    ("Lookaround", [("(?=abc)", "followed by abc"), ("(?!abc)", "not followed by abc"),
                    ("(?<=abc)", "preceded by abc"), ("(?<!abc)", "not preceded by abc")]),
    ("Flags", [("i", "ignore case"), ("m", "^ and $ match each line"),
               ("s", ". also matches newlines"), ("g", "find every match, not just the first")]),
    ("Common patterns", [
        (r"^[\w.+-]+@[\w-]+\.[\w.]{2,}$", "email address"),
        (r"^https?://[^\s]+$", "URL"),
        (r"^\d{4}-\d{2}-\d{2}$", "date as YYYY-MM-DD"),
        (r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", "hex colour"),
        (r"^\+?\d[\d\s().-]{7,}$", "phone number"),
        (r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", "password: 8+ with upper, lower and a digit"),
    ]),
]


@register("regex-cheat-sheet")
def regex_cheat_sheet(files, text: str, options: dict) -> ToolResult:
    query = (text or "").strip().lower()
    sections = []
    for title, rows in _REGEX_REFERENCE:
        keep = [(a, b) for a, b in rows if not query or query in a.lower() or query in b.lower()]
        if keep:
            sections.append({"section": title,
                             "entries": [{"pattern": a, "means": b} for a, b in keep]})
    if not sections:
        return ToolResult(meta={"error": f"Nothing matches {query!r}. Leave the box empty for everything."})
    lines = []
    for section in sections:
        lines.append(f"## {section['section']}")
        lines += [f"  {e['pattern']:<18} {e['means']}" for e in section["entries"]]
        lines.append("")
    return ToolResult(text="\n".join(lines).strip(), meta={"sections": sections})


# ===========================================================================
# Generators and references
# ===========================================================================

@register("markdown-table-generator")
def markdown_table_generator(files, text: str, options: dict) -> ToolResult:
    """Turns pasted CSV or TSV into an aligned Markdown table."""
    import csv
    import io

    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste your rows as CSV or TSV."})
    delim = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}.get(
        str(options.get("delimiter", "comma")), ",")
    rows = [r for r in csv.reader(io.StringIO(src), delimiter=delim) if any(c.strip() for c in r)]
    if len(rows) < 1:
        return ToolResult(meta={"error": "No rows found."})
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    align = str(options.get("align", "left"))
    if _flag(options, "pad", True):
        widths = [max(len(str(r[i])) for r in rows) for i in range(width)]
    else:
        widths = [0] * width
    bar = {"left": lambda w: ":" + "-" * max(2, w + 1),
           "center": lambda w: ":" + "-" * max(1, w) + ":",
           "right": lambda w: "-" * max(2, w + 1) + ":"}[align]
    lines = ["| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(rows[0])) + " |",
             "| " + " | ".join(bar(widths[i]) for i in range(width)) + " |"]
    lines += ["| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)) + " |"
              for r in rows[1:]]
    return ToolResult(text="\n".join(lines), meta={"rows": len(rows) - 1, "columns": width})


@register("readme-generator")
def readme_generator(files, text: str, options: dict) -> ToolResult:
    name = str(options.get("project", "")).strip() or (text or "").strip().split("\n")[0] or "My Project"
    description = str(options.get("description", "")).strip() or "A short description of what this does."
    language = str(options.get("language", "node"))
    install = {"node": "npm install", "python": "pip install -r requirements.txt",
               "go": "go mod download", "rust": "cargo build", "php": "composer install"}
    run = {"node": "npm start", "python": "python main.py", "go": "go run .",
           "rust": "cargo run", "php": "php -S localhost:8000"}
    sections = [
        f"# {name}", "", description, "",
        "## Installation", "", "```bash",
        f"git clone https://github.com/your-name/{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}.git",
        f"cd {re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}",
        install.get(language, "make install"), "```", "",
        "## Usage", "", "```bash", run.get(language, "make run"), "```", "",
    ]
    if _flag(options, "include_features", True):
        sections += ["## Features", "", "- Feature one", "- Feature two", "- Feature three", ""]
    if _flag(options, "include_contributing", True):
        sections += ["## Contributing", "",
                     "Pull requests are welcome. For large changes, open an issue first so we can "
                     "agree on the approach.", ""]
    licence = str(options.get("license", "MIT"))
    if licence != "none":
        sections += ["## License", "", f"{licence}", ""]
    return ToolResult(text="\n".join(sections).strip())


_GITIGNORE = {
    "node": ["node_modules/", "npm-debug.log*", "yarn-error.log*", ".pnpm-debug.log*",
             "dist/", "build/", ".next/", "coverage/", "*.tsbuildinfo"],
    "python": ["__pycache__/", "*.py[cod]", "*.egg-info/", ".venv/", "venv/", "env/",
               ".pytest_cache/", ".mypy_cache/", ".coverage", "dist/", "build/"],
    "java": ["*.class", "target/", "build/", "*.jar", ".gradle/"],
    "go": ["*.exe", "*.test", "*.out", "vendor/", "bin/"],
    "rust": ["target/", "**/*.rs.bk", "Cargo.lock"],
    "php": ["vendor/", "composer.phar", ".phpunit.result.cache"],
    "unity": ["Library/", "Temp/", "Obj/", "Build/", "Logs/", "*.csproj", "*.sln"],
    "macos": [".DS_Store", ".AppleDouble", ".LSOverride", "Icon\r", "._*"],
    "windows": ["Thumbs.db", "ehthumbs.db", "Desktop.ini", "$RECYCLE.BIN/", "*.lnk"],
    "linux": ["*~", ".fuse_hidden*", ".directory", ".Trash-*"],
    "editors": [".vscode/", ".idea/", "*.swp", "*.swo", "*.sublime-workspace"],
    "secrets": [".env", ".env.*", "!.env.example", "*.pem", "*.key", "secrets.json"],
}


@register("gitignore-generator")
def gitignore_generator(files, text: str, options: dict) -> ToolResult:
    """Builds a .gitignore from the stacks you actually use."""
    wanted = [w.strip().lower() for w in
              re.split(r"[,\s]+", str(options.get("stacks", "")) or (text or "")) if w.strip()]
    if not wanted:
        wanted = ["node", "macos", "editors", "secrets"]
    unknown = [w for w in wanted if w not in _GITIGNORE]
    if unknown:
        return ToolResult(meta={
            "error": f"Unknown: {', '.join(unknown)}. Available: {', '.join(sorted(_GITIGNORE))}"
        })
    blocks = []
    for stack in dict.fromkeys(wanted):
        blocks.append(f"# {stack.capitalize()}\n" + "\n".join(_GITIGNORE[stack]))
    return ToolResult(text="\n\n".join(blocks), meta={"stacks": list(dict.fromkeys(wanted))})


@register("mock-sql-generator")
def mock_sql_generator(files, text: str, options: dict) -> ToolResult:
    """CREATE TABLE plus INSERT rows, inferred from a JSON sample."""
    data, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": "Paste a JSON array of objects to model the table on."})
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data or not all(isinstance(r, dict) for r in data):
        return ToolResult(meta={"error": "Expected a JSON array of objects."})
    table = re.sub(r"[^A-Za-z0-9_]", "_", str(options.get("table", "records")) or "records")

    # column name -> (original JSON key, SQL type). Keeping the original key is
    # what lets a field like "first name" be read back off each row after its
    # column name has been sanitised.
    columns: dict[str, tuple[str, str]] = {}
    for row in data:
        for key, value in row.items():
            column = re.sub(r"[^A-Za-z0-9_]", "_", key)
            kind = ("BOOLEAN" if isinstance(value, bool)
                    else "INTEGER" if isinstance(value, int)
                    else "REAL" if isinstance(value, float)
                    else "TEXT")
            # A column seen as more than one type has to widen. INTEGER and REAL
            # widen to REAL, which still holds both; anything else falls to TEXT.
            if column in columns and columns[column][1] != kind:
                previous = columns[column][1]
                kind = ("REAL" if {previous, kind} == {"INTEGER", "REAL"} else "TEXT")
            columns[column] = (key, kind)

    lines = [f"CREATE TABLE {table} ("]
    # Only add a surrogate key when the data has no id of its own — otherwise the
    # table came out with the column declared twice, which will not run.
    if "id" not in columns:
        lines.append("  id INTEGER PRIMARY KEY,")
    body = [f"  {c} {t}" + (" PRIMARY KEY" if c == "id" else "")
            for c, (_, t) in columns.items()]
    lines.append(",\n".join(body))
    lines.append(");")
    ddl = "\n".join(lines)

    def literal(value) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (dict, list)):
            return "'" + json.dumps(value).replace("'", "''") + "'"
        return "'" + str(value).replace("'", "''") + "'"

    names = ", ".join(columns)
    inserts = [
        f"INSERT INTO {table} ({names}) VALUES ("
        + ", ".join(literal(row.get(source)) for source, _ in columns.values()) + ");"
        for row in data
    ]
    return ToolResult(text=ddl + "\n\n" + "\n".join(inserts),
                      meta={"table": table, "columns": len(columns), "rows": len(data)})


@register("connection-string-builder")
def connection_string_builder(files, text: str, options: dict) -> ToolResult:
    """Builds a database URL, escaping the parts that need it.

    The password is percent-encoded: an unescaped @ or / in a password is the
    single most common reason a connection string silently points somewhere else.
    """
    import urllib.parse as _url

    engine = str(options.get("engine", "postgresql"))
    host = str(options.get("host", "localhost")).strip() or "localhost"
    database = str(options.get("database", "mydb")).strip()
    user = str(options.get("username", "")).strip()
    password = str(options.get("password", ""))
    port = _int(options, "port", 0)
    defaults = {"postgresql": 5432, "mysql": 3306, "mongodb": 27017, "redis": 6379,
                "mssql": 1433, "sqlite": 0}
    if not database and engine != "redis":
        return ToolResult(meta={"error": "Enter a database name."})
    if engine == "sqlite":
        return ToolResult(text=f"sqlite:///{database or 'app.db'}",
                          meta={"engine": engine, "note": "SQLite is a file — no host or port."})
    port = port or defaults.get(engine, 0)
    credentials = ""
    if user:
        credentials = _url.quote(user, safe="")
        if password:
            credentials += ":" + _url.quote(password, safe="")
        credentials += "@"
    scheme = {"postgresql": "postgresql", "mysql": "mysql+pymysql", "mongodb": "mongodb",
              "redis": "redis", "mssql": "mssql+pyodbc"}[engine]
    url = f"{scheme}://{credentials}{host}:{port}/{database}"
    extras = str(options.get("parameters", "")).strip()
    if extras:
        url += ("&" if "?" in url else "?") + extras.lstrip("?&")
    return ToolResult(text=url, meta={
        "engine": engine, "port": port,
        "password_was_escaped": password != _url.quote(password, safe=""),
        "warning": "Never commit a connection string with a real password.",
    })


@register("srcset-generator")
def srcset_generator(files, text: str, options: dict) -> ToolResult:
    """Builds a responsive <img> with srcset and sizes."""
    path = (text or "").strip() or str(options.get("path", "/images/photo.jpg"))
    stem, _, extension = path.rpartition(".")
    if not stem:
        stem, extension = path, "jpg"
    raw_widths = str(options.get("widths", "480, 768, 1024, 1440, 1920"))
    widths = sorted({int(w) for w in re.findall(r"\d+", raw_widths) if 16 <= int(w) <= 8000})
    if not widths:
        return ToolResult(meta={"error": "Enter at least one width between 16 and 8000."})
    pattern = str(options.get("pattern", "{stem}-{w}.{ext}"))
    srcset = ", ".join(
        pattern.format(stem=stem, w=w, ext=extension) + f" {w}w" for w in widths)
    sizes = str(options.get("sizes", "(max-width: 768px) 100vw, 50vw"))
    alt = str(options.get("alt", "")) or "Describe the image here"
    html = (f'<img\n  src="{pattern.format(stem=stem, w=widths[len(widths) // 2], ext=extension)}"\n'
            f'  srcset="{srcset}"\n  sizes="{sizes}"\n'
            f'  width="{widths[-1]}" height="{round(widths[-1] * 2 / 3)}"\n'
            f'  alt="{alt}"\n  loading="lazy"\n  decoding="async">')
    return ToolResult(text=html, meta={
        "widths": widths,
        "note": "width and height are placeholders — set the real ones so the layout doesn't shift.",
    })


@register("svg-optimizer")
def svg_optimizer(files, text: str, options: dict) -> ToolResult:
    """Strips the editor cruft that makes an exported SVG four times bigger."""
    src = (text or "").strip()
    if not src:
        return ToolResult(meta={"error": "Paste your SVG markup."})
    if "<svg" not in src.lower():
        return ToolResult(meta={"error": "That doesn't look like SVG."})
    before = len(src)
    out = re.sub(r"<!--.*?-->", "", src, flags=re.DOTALL)
    out = re.sub(r"<\?xml.*?\?>", "", out, flags=re.DOTALL)
    out = re.sub(r"<!DOCTYPE[^>]*>", "", out, flags=re.IGNORECASE)
    # Editor metadata: Inkscape, Illustrator and Sketch all leave blocks behind.
    out = re.sub(r"<(metadata|sodipodi:namedview|title|desc)\b.*?</\1>", "", out,
                 flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"\s(sodipodi|inkscape|xmlns:(sodipodi|inkscape|serif|dc|cc|rdf))(:[\w-]+)?=\"[^\"]*\"",
                 "", out, flags=re.IGNORECASE)
    if _flag(options, "remove_ids", True):
        out = re.sub(r'\sid="[^"]*"', "", out)
    if _flag(options, "round_numbers", True):
        precision = max(0, min(_int(options, "precision", 2), 6))
        out = re.sub(r"-?\d+\.\d{3,}",
                     lambda m: f"{round(float(m.group(0)), precision):g}", out)
    out = re.sub(r">\s+<", "><", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return ToolResult(text=out, meta={
        "characters_before": before, "characters_after": len(out),
        "saved_percent": round(100 - len(out) / max(1, before) * 100, 1),
        "note": "Structural cleanup only — path geometry is never rewritten.",
    })


_HTTP_STATUS = {
    100: "Continue", 101: "Switching Protocols", 103: "Early Hints",
    200: "OK", 201: "Created", 202: "Accepted", 204: "No Content", 206: "Partial Content",
    301: "Moved Permanently", 302: "Found", 303: "See Other", 304: "Not Modified",
    307: "Temporary Redirect", 308: "Permanent Redirect",
    400: "Bad Request", 401: "Unauthorized", 402: "Payment Required", 403: "Forbidden",
    404: "Not Found", 405: "Method Not Allowed", 406: "Not Acceptable", 408: "Request Timeout",
    409: "Conflict", 410: "Gone", 411: "Length Required", 413: "Payload Too Large",
    414: "URI Too Long", 415: "Unsupported Media Type", 418: "I'm a teapot",
    422: "Unprocessable Content", 425: "Too Early", 428: "Precondition Required",
    429: "Too Many Requests", 431: "Request Header Fields Too Large",
    451: "Unavailable For Legal Reasons",
    500: "Internal Server Error", 501: "Not Implemented", 502: "Bad Gateway",
    503: "Service Unavailable", 504: "Gateway Timeout", 505: "HTTP Version Not Supported",
    507: "Insufficient Storage", 511: "Network Authentication Required",
}
_STATUS_NOTES = {
    301: "Permanent. Browsers and search engines cache it — hard to undo.",
    302: "Temporary. The original URL keeps its ranking.",
    401: "Not authenticated. Use 403 when the user is known but not allowed.",
    403: "Authenticated but not permitted. Do not use for 'not logged in'.",
    404: "Not found, and no opinion on whether it ever existed. Use 410 for gone-for-good.",
    422: "The request was understood but the data failed validation.",
    429: "Rate limited. Send a Retry-After header with it.",
    502: "An upstream server returned something invalid — usually your own backend.",
    503: "Temporarily down. Send Retry-After so clients back off sensibly.",
}


@register("http-status-reference")
def http_status_reference(files, text: str, options: dict) -> ToolResult:
    query = (text or "").strip().lower()
    rows = []
    for code, name in sorted(_HTTP_STATUS.items()):
        if query and query not in str(code) and query not in name.lower():
            continue
        classes = {1: "Informational", 2: "Success", 3: "Redirect",
                   4: "Client error", 5: "Server error"}
        rows.append({"code": code, "name": name, "class": classes[code // 100],
                     **({"note": _STATUS_NOTES[code]} if code in _STATUS_NOTES else {})})
    if not rows:
        return ToolResult(meta={"error": f"No status code matches {query!r}."})
    return ToolResult(
        text="\n".join(f"{r['code']}  {r['name']}" + (f"  — {r['note']}" if "note" in r else "")
                       for r in rows),
        meta={"matches": len(rows), "statuses": rows})


_MIME = {
    "html": "text/html", "htm": "text/html", "css": "text/css", "js": "text/javascript",
    "mjs": "text/javascript", "json": "application/json", "xml": "application/xml",
    "txt": "text/plain", "csv": "text/csv", "md": "text/markdown", "ics": "text/calendar",
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif",
    "webp": "image/webp", "avif": "image/avif", "svg": "image/svg+xml", "ico": "image/x-icon",
    "bmp": "image/bmp", "tiff": "image/tiff", "heic": "image/heic",
    "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg", "m4a": "audio/mp4",
    "flac": "audio/flac", "aac": "audio/aac",
    "mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime", "avi": "video/x-msvideo",
    "mkv": "video/x-matroska",
    "pdf": "application/pdf", "zip": "application/zip", "gz": "application/gzip",
    "tar": "application/x-tar", "rar": "application/vnd.rar", "7z": "application/x-7z-compressed",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "woff": "font/woff", "woff2": "font/woff2", "ttf": "font/ttf", "otf": "font/otf",
    "wasm": "application/wasm", "apk": "application/vnd.android.package-archive",
}


@register("mime-type-lookup")
def mime_type_lookup(files, text: str, options: dict) -> ToolResult:
    query = (text or "").strip().lower().lstrip(".")
    if not query:
        return ToolResult(text="\n".join(f".{k:<6} {v}" for k, v in sorted(_MIME.items())),
                          meta={"total": len(_MIME)})
    if "." in query:
        query = query.rsplit(".", 1)[-1]
    if query in _MIME:
        return ToolResult(text=_MIME[query], meta={"extension": f".{query}", "mime_type": _MIME[query]})
    matches = {k: v for k, v in _MIME.items() if query in v or query in k}
    if not matches:
        return ToolResult(meta={"error": f"No MIME type known for {query!r}."})
    return ToolResult(text="\n".join(f".{k:<6} {v}" for k, v in sorted(matches.items())),
                      meta={"matches": len(matches)})


@register("ascii-unicode-table")
def ascii_unicode_table(files, text: str, options: dict) -> ToolResult:
    """The ASCII table, or the details of whatever characters you paste."""
    import unicodedata

    src = text or ""
    if src.strip():
        rows = []
        for ch in src[:200]:
            rows.append({
                "character": ch if ch.isprintable() else repr(ch),
                "code_point": f"U+{ord(ch):04X}",
                "decimal": ord(ch),
                "hex": f"{ord(ch):x}",
                "name": unicodedata.name(ch, "(no name)"),
                "category": unicodedata.category(ch),
                "utf8_bytes": " ".join(f"{b:02x}" for b in ch.encode("utf-8")),
            })
        return ToolResult(
            text="\n".join(f"{r['character']}  {r['code_point']}  {r['decimal']:<6} {r['name']}"
                           for r in rows),
            meta={"characters": len(rows), "details": rows})
    control = {0: "NUL", 7: "BEL", 8: "BS", 9: "TAB", 10: "LF", 13: "CR", 27: "ESC", 127: "DEL"}
    start = max(0, _int(options, "start", 32))
    end = min(127, max(start, _int(options, "end", 126)))
    lines = [f"{n:<5} {n:02x}   {n:03o}    {control.get(n, chr(n) if 32 <= n < 127 else '')}"
             for n in range(start, end + 1)]
    return ToolResult(text="Dec   Hex  Oct    Char\n" + "\n".join(lines),
                      meta={"from": start, "to": end})


_ENTITY_REFERENCE = {
    "&amp;": "& ampersand", "&lt;": "< less than", "&gt;": "> greater than",
    "&quot;": '" double quote', "&apos;": "' apostrophe", "&nbsp;": "non-breaking space",
    "&copy;": "© copyright", "&reg;": "® registered", "&trade;": "™ trademark",
    "&hellip;": "… ellipsis", "&mdash;": "— em dash", "&ndash;": "– en dash",
    "&bull;": "• bullet", "&middot;": "· middle dot", "&deg;": "° degree",
    "&plusmn;": "± plus-minus", "&times;": "× multiply", "&divide;": "÷ divide",
    "&frac12;": "½ one half", "&frac14;": "¼ one quarter", "&sup2;": "² squared",
    "&euro;": "€ euro", "&pound;": "£ pound", "&yen;": "¥ yen", "&cent;": "¢ cent",
    "&larr;": "← left arrow", "&rarr;": "→ right arrow", "&uarr;": "↑ up arrow",
    "&darr;": "↓ down arrow", "&harr;": "↔ left-right arrow",
    "&check;": "✓ check mark", "&cross;": "✗ cross", "&star;": "★ star",
    "&hearts;": "♥ heart", "&spades;": "♠ spade", "&clubs;": "♣ club", "&diams;": "♦ diamond",
    "&laquo;": "« left quote", "&raquo;": "» right quote", "&ldquo;": "“ left double quote",
    "&rdquo;": "” right double quote", "&lsquo;": "‘ left single quote",
    "&rsquo;": "’ right single quote", "&dagger;": "† dagger", "&sect;": "§ section",
    "&para;": "¶ paragraph", "&permil;": "‰ per mille", "&infin;": "∞ infinity",
    "&ne;": "≠ not equal", "&le;": "≤ less or equal", "&ge;": "≥ greater or equal",
    "&asymp;": "≈ approximately", "&radic;": "√ square root", "&sum;": "∑ sum",
}


@register("html-entity-reference")
def html_entity_reference(files, text: str, options: dict) -> ToolResult:
    import html as _html

    query = (text or "").strip().lower()
    rows = {k: v for k, v in _ENTITY_REFERENCE.items()
            if not query or query in k.lower() or query in v.lower()}
    if not rows:
        return ToolResult(meta={"error": f"Nothing matches {query!r}."})
    lines = []
    for entity, meaning in rows.items():
        char = _html.unescape(entity)
        lines.append(f"{entity:<12} {char:<3} &#{ord(char) if len(char) == 1 else 0};  {meaning}")
    return ToolResult(text="\n".join(lines), meta={"entries": len(rows)})


_TYPE_MAP = {
    "typescript": {"str": "string", "int": "number", "float": "number", "bool": "boolean",
                   "NoneType": "null", "list": "any[]", "dict": "Record<string, any>"},
    "python": {"str": "str", "int": "int", "float": "float", "bool": "bool",
               "NoneType": "None", "list": "list", "dict": "dict"},
    "go": {"str": "string", "int": "int", "float": "float64", "bool": "bool",
           "NoneType": "interface{}", "list": "[]interface{}", "dict": "map[string]interface{}"},
}


@register("json-to-types")
def json_to_types(files, text: str, options: dict) -> ToolResult:
    """Generates a type or model from a JSON sample.

    Inferred from one example, so an optional field that happens to be absent —
    or a null that is really a string — will come out wrong. Always read it
    before committing it.
    """
    data, error = _load_json(text)
    if error:
        return ToolResult(meta={"error": error})
    language = str(options.get("language", "typescript"))
    if language not in _TYPE_MAP:
        return ToolResult(meta={"error": "Choose typescript, python or go."})
    root = re.sub(r"[^A-Za-z0-9]", "", str(options.get("name", "Root")).title()) or "Root"
    types = _TYPE_MAP[language]
    blocks: list[str] = []
    seen: set[str] = set()

    def pascal(name: str) -> str:
        return "".join(part.title() for part in re.split(r"[^A-Za-z0-9]+", name) if part) or "Item"

    def describe(value, hint: str) -> str:
        if isinstance(value, dict):
            emit(value, hint)
            return hint
        if isinstance(value, list):
            if not value:
                return types["list"]
            inner = describe(value[0], pascal(hint.rstrip("s")) or "Item")
            return f"{inner}[]" if language == "typescript" else \
                   (f"[]{inner}" if language == "go" else f"list[{inner}]")
        if isinstance(value, bool):
            return types["bool"]
        return types.get(type(value).__name__, types["dict"])

    def emit(obj: dict, name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        fields = [(key, describe(value, pascal(key))) for key, value in obj.items()]
        if language == "typescript":
            body = "\n".join(f"  {k}: {t};" for k, t in fields)
            blocks.append(f"export interface {name} {{\n{body}\n}}")
        elif language == "python":
            body = "\n".join(f"    {re.sub(r'[^a-z0-9_]', '_', k.lower())}: {t}" for k, t in fields)
            blocks.append(f"@dataclass\nclass {name}:\n{body}")
        else:
            body = "\n".join(f"\t{pascal(k)} {t} `json:\"{k}\"`" for k, t in fields)
            blocks.append(f"type {name} struct {{\n{body}\n}}")

    if isinstance(data, list):
        if not data or not isinstance(data[0], dict):
            return ToolResult(meta={"error": "Give an object, or an array of objects."})
        emit(data[0], root)
    elif isinstance(data, dict):
        emit(data, root)
    else:
        return ToolResult(meta={"error": "Give an object, or an array of objects."})
    header = "from dataclasses import dataclass\n\n\n" if language == "python" else ""
    # Nested types are emitted as they are discovered, so the root ends up first;
    # reversing puts dependencies before the thing that uses them.
    return ToolResult(text=header + "\n\n".join(reversed(blocks)),
                      meta={"language": language, "types": len(blocks)})


@register("curl-to-code")
def curl_to_code(files, text: str, options: dict) -> ToolResult:
    """Rewrites a cURL command as code in another language."""
    import shlex

    command = " ".join((text or "").strip().replace("\\\n", " ").split())
    if not command.startswith("curl"):
        return ToolResult(meta={"error": "Paste a command that starts with 'curl'."})
    try:
        tokens = shlex.split(command)[1:]
    except ValueError:
        return ToolResult(meta={"error": "That command has an unbalanced quote."})
    url, method, headers, body = "", "", {}, None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in ("-X", "--request") and i + 1 < len(tokens):
            method = tokens[i + 1].upper()
            i += 2
        elif token in ("-H", "--header") and i + 1 < len(tokens):
            name, _, value = tokens[i + 1].partition(":")
            headers[name.strip()] = value.strip()
            i += 2
        elif token in ("-d", "--data", "--data-raw", "--data-binary") and i + 1 < len(tokens):
            body = tokens[i + 1]
            i += 2
        elif token in ("-u", "--user") and i + 1 < len(tokens):
            headers["Authorization"] = "Basic " + base64.b64encode(
                tokens[i + 1].encode()).decode()
            i += 2
        elif token.startswith("-"):
            i += 1  # a flag we do not model (-L, -k, -s …)
        else:
            url = token
            i += 1
    if not url:
        return ToolResult(meta={"error": "No URL found in that command."})
    method = method or ("POST" if body else "GET")
    language = str(options.get("language", "javascript"))
    if language == "python":
        lines = ["import requests", "", f'url = "{url}"']
        if headers:
            lines.append("headers = " + json.dumps(headers, indent=4))
        if body:
            lines.append(f"data = {body!r}")
        call = f'response = requests.{method.lower()}(url'
        call += ", headers=headers" if headers else ""
        call += ", data=data" if body else ""
        lines += ["", call + ")", "print(response.status_code, response.text)"]
        code = "\n".join(lines)
    elif language == "go":
        code = (f'req, _ := http.NewRequest("{method}", "{url}", '
                + (f'strings.NewReader({json.dumps(body)})' if body else "nil") + ")\n"
                + "".join(f'req.Header.Set({json.dumps(k)}, {json.dumps(v)})\n'
                          for k, v in headers.items())
                + "resp, err := http.DefaultClient.Do(req)")
    elif language == "php":
        code = ("$ch = curl_init();\n"
                f'curl_setopt($ch, CURLOPT_URL, "{url}");\n'
                "curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);\n"
                f'curl_setopt($ch, CURLOPT_CUSTOMREQUEST, "{method}");\n'
                + (f"curl_setopt($ch, CURLOPT_HTTPHEADER, {json.dumps([f'{k}: {v}' for k, v in headers.items()])});\n" if headers else "")
                + (f"curl_setopt($ch, CURLOPT_POSTFIELDS, {json.dumps(body)});\n" if body else "")
                + "$response = curl_exec($ch);\ncurl_close($ch);")
    else:
        options_block = {"method": method}
        if headers:
            options_block["headers"] = headers
        if body:
            options_block["body"] = body
        code = (f'const response = await fetch("{url}", '
                + json.dumps(options_block, indent=2) + ");\n"
                + "const data = await response.json();\nconsole.log(data);")
    return ToolResult(text=code, meta={"method": method, "url": url, "headers": len(headers),
                                       "language": language})
