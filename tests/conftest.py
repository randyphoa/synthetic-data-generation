from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def customer_classifier_path():
    return FIXTURES_DIR / "CustomerClassifier.java"


@pytest.fixture
def customer_classifier_source(customer_classifier_path):
    return customer_classifier_path.read_text()
