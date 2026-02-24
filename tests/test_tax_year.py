"""Test tax year extraction logic."""

from app.services.pdf_service import _extract_tax_year


def test_explicit_tax_year():
    """'Tax Year: 2024' should be extracted."""
    assert _extract_tax_year("Schedule K-1\nTax Year: 2024\nPartner's Share") == "2024"


def test_tax_year_before_label():
    """'2023 Tax Year' should be extracted."""
    assert _extract_tax_year("Form 1040\n2023 Tax Year\nU.S. Individual") == "2023"


def test_year_ending_pattern():
    """'for the year ending December 31, 2024' should be extracted."""
    text = "Form 1099-INT\nfor the tax year ending December 31, 2024"
    assert _extract_tax_year(text) == "2024"


def test_form_with_year_in_parens():
    """'Form W-2 (2023)' should extract 2023."""
    assert _extract_tax_year("Form W-2 (2023)\nWage and Tax Statement") == "2023"


def test_date_pattern():
    """A date like 'January 31, 2024' should be picked up."""
    text = "Statement Period\nJanuary 31, 2024\nAccount Summary"
    assert _extract_tax_year(text) == "2024"


def test_slash_date_pattern():
    """A date like '12/31/2023' should be picked up."""
    text = "Period ending 12/31/2023\nTotal income"
    assert _extract_tax_year(text) == "2023"


def test_fallback_most_common_year():
    """When no explicit pattern matches, use the most common year."""
    text = "Report generated 2025. Data from 2024. Income 2024. Balance 2024."
    assert _extract_tax_year(text) == "2024"


def test_no_year_found():
    """Text with no 4-digit years returns None."""
    assert _extract_tax_year("Hello World - Generic Document") is None


def test_empty_text():
    """Empty text returns None."""
    assert _extract_tax_year("") is None
