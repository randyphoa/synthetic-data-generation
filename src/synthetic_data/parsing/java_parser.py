"""Phase 1: Parse Java source files using tree-sitter and extract method info."""

from __future__ import annotations

import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from synthetic_data.models.cfg_node import FieldInfo, MethodInfo, Parameter

JAVA_LANGUAGE = Language(tsjava.language())


def parse_file(path: str) -> tuple:
    """Parse a Java source file. Returns (tree, source_bytes)."""
    parser = Parser(JAVA_LANGUAGE)
    with open(path, "rb") as f:
        source = f.read()
    tree = parser.parse(source)
    return tree, source


def parse_source(source: str | bytes) -> tuple:
    """Parse Java source code string. Returns (tree, source_bytes)."""
    parser = Parser(JAVA_LANGUAGE)
    if isinstance(source, str):
        source = source.encode()
    tree = parser.parse(source)
    return tree, source


def extract_class_name(tree, source: bytes) -> str | None:
    """Extract the top-level class name from a parsed tree."""
    for child in tree.root_node.children:
        if child.type == "class_declaration":
            for c in child.children:
                if c.type == "identifier":
                    return _text(c, source)
    return None


def extract_fields(tree, source: bytes) -> list[FieldInfo]:
    """Extract instance field declarations from a parsed tree."""
    fields: list[FieldInfo] = []
    for child in tree.root_node.children:
        if child.type == "class_declaration":
            _find_fields(child, source, fields)
    return fields


def _find_fields(node, source: bytes, fields: list[FieldInfo]):
    """Walk class body to find field_declaration nodes."""
    for child in node.children:
        if child.type == "class_body":
            for member in child.children:
                if member.type == "field_declaration":
                    field_info = _parse_field(member, source)
                    if field_info:
                        fields.append(field_info)


def _parse_field(node, source: bytes) -> FieldInfo | None:
    """Parse a field_declaration into FieldInfo."""
    java_type = None
    name = None
    # Skip static fields
    for child in node.children:
        if child.type == "modifiers":
            mods_text = _text(child, source)
            if "static" in mods_text:
                return None
    for child in node.children:
        if child.type in (
            "type_identifier",
            "integral_type",
            "floating_point_type",
            "boolean_type",
            "generic_type",
            "array_type",
        ):
            java_type = _text(child, source)
        elif child.type == "variable_declarator":
            for c in child.children:
                if c.type == "identifier":
                    name = _text(c, source)
                    break
    if name and java_type:
        return FieldInfo(name=name, java_type=java_type)
    return None


def extract_constructors(tree, source: bytes) -> list[MethodInfo]:
    """Extract constructor declarations from a parsed tree.

    Returns MethodInfo objects where name is the class name (constructor name).
    """
    constructors: list[MethodInfo] = []
    _find_constructors(tree.root_node, source, constructors)
    return constructors


def extract_constructor_field_map(tree, source: bytes) -> dict[str, str]:
    """Parse constructor bodies for `this.field = param` patterns.

    Returns a dict mapping field name → constructor parameter name.
    """
    constructors = extract_constructors(tree, source)
    field_map: dict[str, str] = {}
    for ctor in constructors:
        if ctor.node is None:
            continue
        param_names = {p.name for p in ctor.parameters}
        body = _find_body_node(ctor.node)
        if body is None:
            continue
        for stmt in _walk_statements(body):
            _parse_field_assignment(stmt, source, param_names, field_map)
    return field_map


def _find_constructors(node, source: bytes, constructors: list[MethodInfo]):
    """Walk tree to find constructor_declaration nodes."""
    if node.type == "constructor_declaration":
        info = _parse_constructor(node, source)
        if info:
            constructors.append(info)
    for child in node.children:
        _find_constructors(child, source, constructors)


def _parse_constructor(node, source: bytes) -> MethodInfo | None:
    """Parse a constructor_declaration into MethodInfo."""
    name = None
    params: list[Parameter] = []

    for child in node.children:
        if child.type == "identifier":
            name = _text(child, source)
        elif child.type == "formal_parameters":
            params = _extract_parameters(child, source)

    if name is None:
        return None

    return MethodInfo(name=name, parameters=params, return_type=None, node=node)


def _find_body_node(node):
    """Find the constructor_body or block child of a declaration node."""
    for child in node.children:
        if child.type in ("constructor_body", "block"):
            return child
    return None


def _walk_statements(body_node):
    """Yield statement-level children from a body/block node."""
    for child in body_node.children:
        if child.type == "expression_statement":
            yield child
        elif child.type in ("block", "constructor_body"):
            yield from _walk_statements(child)


def _parse_field_assignment(
    stmt_node, source: bytes, param_names: set[str], field_map: dict[str, str]
):
    """If stmt is `this.field = param;`, add field→param to field_map."""
    for child in stmt_node.children:
        if child.type == "assignment_expression":
            left = child.child_by_field_name("left")
            right = child.child_by_field_name("right")
            if left is None or right is None:
                continue
            # Left must be this.field (field_access with this as object)
            if left.type == "field_access":
                obj = left.child_by_field_name("object")
                field = left.child_by_field_name("field")
                if obj is None or field is None:
                    continue
                if _text(obj, source) == "this":
                    field_name = _text(field, source)
                    # Right must be a parameter name
                    right_text = _text(right, source)
                    if right_text in param_names:
                        field_map[field_name] = right_text


def extract_methods(tree, source: bytes) -> list[MethodInfo]:
    """Extract all method declarations from a parsed tree."""
    methods: list[MethodInfo] = []
    _find_methods(tree.root_node, source, methods)
    return methods


def _find_methods(node, source: bytes, methods: list[MethodInfo]):
    if node.type == "method_declaration":
        info = _parse_method(node, source)
        if info:
            methods.append(info)
    for child in node.children:
        _find_methods(child, source, methods)


def _parse_method(node, source: bytes) -> MethodInfo | None:
    name = None
    params: list[Parameter] = []
    return_type = None

    for child in node.children:
        if child.type == "identifier":
            name = _text(child, source)
        elif child.type == "formal_parameters":
            params = _extract_parameters(child, source)
        elif child.type in (
            "type_identifier",
            "void_type",
            "integral_type",
            "floating_point_type",
            "boolean_type",
            "generic_type",
            "array_type",
        ):
            return_type = _text(child, source)

    if name is None:
        return None

    return MethodInfo(name=name, parameters=params, return_type=return_type, node=node)


def _extract_parameters(formal_params_node, source: bytes) -> list[Parameter]:
    params: list[Parameter] = []
    for child in formal_params_node.children:
        if child.type == "formal_parameter":
            param = _parse_parameter(child, source)
            if param:
                params.append(param)
    return params


def _parse_parameter(param_node, source: bytes) -> Parameter | None:
    java_type = None
    name = None
    for child in param_node.children:
        if child.type in (
            "type_identifier",
            "integral_type",
            "floating_point_type",
            "boolean_type",
            "generic_type",
            "array_type",
        ):
            java_type = _text(child, source)
        elif child.type == "identifier":
            name = _text(child, source)
    if name and java_type:
        return Parameter(name=name, java_type=java_type)
    return None


def extract_column_annotations(tree, source: bytes) -> dict[str, str]:
    """Extract @Column(name="...") annotations from entity fields.

    Returns a dict mapping Java field name → SQL column name,
    e.g. {"stsTag": "INSPOL_STS_TAG", "comdteC": "INSPOL_COMDTE_C"}.
    """
    mapping: dict[str, str] = {}
    for child in tree.root_node.children:
        if child.type == "class_declaration":
            _find_column_annotations(child, source, mapping)
    return mapping


def _find_column_annotations(node, source: bytes, mapping: dict[str, str]):
    """Walk class body to find fields with @Column annotations."""
    for child in node.children:
        if child.type == "class_body":
            for member in child.children:
                if member.type == "field_declaration":
                    col_name = _extract_column_name(member, source)
                    field_name = _extract_field_name(member, source)
                    if col_name and field_name:
                        mapping[field_name] = col_name


def _extract_column_name(field_node, source: bytes) -> str | None:
    """Extract the column name from @Column(name="...") on a field."""
    for child in field_node.children:
        if child.type == "modifiers":
            for mod in child.children:
                if mod.type == "annotation":
                    ann_text = _text(mod, source)
                    if ann_text.startswith("@Column"):
                        # Parse name="..." from annotation text
                        import re
                        m = re.search(r'name\s*=\s*"([^"]+)"', ann_text)
                        if m:
                            return m.group(1)
    return None


def _extract_field_name(field_node, source: bytes) -> str | None:
    """Extract the field name from a field_declaration."""
    for child in field_node.children:
        if child.type == "variable_declarator":
            for c in child.children:
                if c.type == "identifier":
                    return _text(c, source)
    return None


def extract_table_name(tree, source: bytes) -> str | None:
    """Extract @Table(name="...") from the class declaration.

    Returns the table name string, e.g. "T_INSPOL", or None.
    """
    import re
    for child in tree.root_node.children:
        if child.type == "class_declaration":
            for c in child.children:
                if c.type == "modifiers":
                    for mod in c.children:
                        if mod.type == "annotation":
                            ann_text = _text(mod, source)
                            if ann_text.startswith("@Table"):
                                m = re.search(r'name\s*=\s*"([^"]+)"', ann_text)
                                if m:
                                    return m.group(1)
    return None


def _text(node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")
