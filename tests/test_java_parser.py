from synthetic_data.parsing.java_parser import extract_methods, parse_file


def test_parse_file(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    assert tree is not None
    assert tree.root_node.type == "program"


def test_extract_methods(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)

    assert len(methods) == 1
    m = methods[0]
    assert m.name == "classify"
    assert m.return_type == "String"
    assert len(m.parameters) == 3

    param_names = [p.name for p in m.parameters]
    assert param_names == ["age", "income", "isMember"]

    param_types = [p.java_type for p in m.parameters]
    assert param_types == ["int", "double", "boolean"]

    assert m.node is not None
    assert m.node.type == "method_declaration"
