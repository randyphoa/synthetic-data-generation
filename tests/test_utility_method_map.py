"""Tests for the utility method map registry."""

from synthetic_data.extraction.utility_method_map import UtilityMethodSpec, lookup, register


def test_lookup_known_method():
    """Known methods should return a spec."""
    spec = lookup("MSHUtil", "isEqualsInt")
    assert spec is not None
    assert spec.operator == "=="
    assert spec.arg_count == 2
    assert spec.result_type == "Integer"


def test_lookup_unknown_method():
    """Unknown methods should return None."""
    assert lookup("UnknownClass", "unknownMethod") is None


def test_lookup_one_arg_method():
    """1-arg methods should have a default_value."""
    spec = lookup("ObjectUtils", "isEmpty")
    assert spec is not None
    assert spec.arg_count == 1
    assert spec.default_value is None  # null check
    assert spec.operator == "=="


def test_lookup_string_whitespace():
    """StringUtils.isWhitespace should have default_value of ' '."""
    spec = lookup("StringUtils", "isWhitespace")
    assert spec is not None
    assert spec.default_value == " "
    assert spec.result_type == "String"


def test_lookup_date_methods():
    """Date utility methods should be registered."""
    spec = lookup("DateTimeUtil", "isZeroDate")
    assert spec is not None
    assert spec.operator == "=="
    assert spec.default_value == 0

    spec = lookup("DateTimeUtil", "isGreaterOrEqualsDate")
    assert spec is not None
    assert spec.operator == ">="
    assert spec.arg_count == 2

    spec = lookup("DateTimeUtil", "isLessOrEqualsDate")
    assert spec is not None
    assert spec.operator == "<="


def test_register_custom_method():
    """Users should be able to register custom utility methods."""
    register("MyUtil", "isPositive", UtilityMethodSpec(">", 1, "Integer", 0))
    spec = lookup("MyUtil", "isPositive")
    assert spec is not None
    assert spec.operator == ">"
    assert spec.default_value == 0


def test_all_default_methods_registered():
    """All 12 default methods should be in the registry."""
    expected = [
        ("ServiceUtil", "isSameTag"),
        ("MSHUtil", "isEqualsInt"),
        ("MSHUtil", "isGreaterThanInt"),
        ("MSHUtil", "isGreaterThanOrEqualsInt"),
        ("MSHUtil", "isLesserThanInt"),
        ("ObjectUtils", "isEmpty"),
        ("CollectionUtils", "isEmpty"),
        ("ServiceUtil", "isNullOrEmptyString"),
        ("StringUtils", "isWhitespace"),
        ("DateTimeUtil", "isZeroDate"),
        ("DateTimeUtil", "isGreaterOrEqualsDate"),
        ("DateTimeUtil", "isLessOrEqualsDate"),
    ]
    for cls, method in expected:
        assert lookup(cls, method) is not None, f"{cls}.{method} not registered"
