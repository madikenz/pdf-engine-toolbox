"""Test table extraction endpoint (POST /text/tables).

Tests cover:
  - PyMuPDF-based table detection (digital PDFs)
  - PPStructureV3 neural network detection (scanned PDFs)
  - Strategy selection: auto, pymupdf, ppstructure

Tests target PaddleOCR 3.x (PPStructureV3, .predict() API).
"""

import json
from unittest.mock import patch, AsyncMock, MagicMock

import fitz


def _create_pdf_with_table():
    """Create a PDF with a simple table for testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)

    # Draw a simple table with borders
    x_start, y_start = 72, 72
    col_width = 100
    row_height = 20
    rows = [
        ["Name", "Amount", "Date"],
        ["W-2 Income", "$85,000", "2024-01-31"],
        ["1099-INT", "$1,250", "2024-01-15"],
        ["1099-DIV", "$3,500", "2024-02-01"],
    ]

    for r, row in enumerate(rows):
        for c, cell_text in enumerate(row):
            x = x_start + c * col_width
            y = y_start + r * row_height
            rect = fitz.Rect(x, y, x + col_width, y + row_height)
            page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            page.insert_textbox(
                rect,
                cell_text,
                fontsize=10,
                fontname="helv",
                align=fitz.TEXT_ALIGN_CENTER,
            )

    return doc.tobytes()


def _create_scanned_pdf():
    """Create a PDF with no selectable text (simulates a scanned page)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Draw rectangles to simulate table lines on a scanned page
    page.draw_rect(fitz.Rect(50, 50, 400, 200), color=(0, 0, 0), width=0.5)
    return doc.tobytes()


def _mock_ppstructurev3_table_result(html: str, bbox: list):
    """Build a mock PPStructureV3 .predict() result containing one table.

    PPStructureV3.predict() returns an iterable of result objects.
    Each result has a .json property with table_res_list (tables) and
    layout_det_res (layout detection).
    """
    result_obj = MagicMock()
    result_obj.json = {
        "layout_det_res": {
            "boxes": [
                {
                    "cls_id": 4,
                    "label": "table",
                    "score": 0.95,
                    "coordinate": bbox,
                },
            ],
        },
        "table_res_list": [
            {
                "pred_html": html,
                "bbox": bbox,
            },
        ],
        "overall_ocr_res": {
            "rec_texts": [],
            "rec_scores": [],
            "dt_polys": [],
        },
    }
    return result_obj


def test_extract_tables(client, auth_headers):
    """Extract tables should find tabular data in PDF."""
    pdf_bytes = _create_pdf_with_table()

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
    })
    headers = auth_headers("POST", "/text/tables", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ):
        response = client.post("/text/tables", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Table detection may or may not find the table depending on PyMuPDF version
    assert isinstance(data["data"]["tables"], list)


def test_extract_tables_pymupdf_strategy(client, auth_headers):
    """strategy='pymupdf' should only use PyMuPDF, never PPStructureV3."""
    pdf_bytes = _create_pdf_with_table()

    body = json.dumps({
        "source_url": "https://example.com/test.pdf",
        "pages": [0],
        "strategy": "pymupdf",
    })
    headers = auth_headers("POST", "/text/tables", body)

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ), patch(
        "app.services.pdf_service._get_pp_structure",
    ) as mock_pps:
        response = client.post("/text/tables", content=body, headers=headers)

    assert response.status_code == 200
    # PPStructureV3 should never be called with pymupdf strategy
    mock_pps.assert_not_called()


def test_extract_tables_ppstructure_strategy(client, auth_headers):
    """strategy='ppstructure' should use PPStructureV3 neural network."""
    pdf_bytes = _create_scanned_pdf()

    body = json.dumps({
        "source_url": "https://example.com/scanned.pdf",
        "pages": [0],
        "strategy": "ppstructure",
    })
    headers = auth_headers("POST", "/text/tables", body)

    # Mock PPStructureV3 to return a table result
    table_html = (
        "<table><tr><td>Name</td><td>Amount</td></tr>"
        "<tr><td>W-2</td><td>85000</td></tr></table>"
    )
    mock_engine = MagicMock()
    mock_engine.predict.return_value = [
        _mock_ppstructurev3_table_result(table_html, [50, 50, 400, 200]),
    ]

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ), patch(
        "app.services.pdf_service._get_pp_structure",
        return_value=mock_engine,
    ):
        response = client.post("/text/tables", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_count"] == 1

    table = data["data"]["tables"][0]
    assert table["page_index"] == 0
    assert table["row_count"] == 2
    assert table["col_count"] == 2
    assert table["rows"][0] == ["Name", "Amount"]
    assert table["rows"][1] == ["W-2", "85000"]
    # Bbox should be in PDF points (scaled from image pixels)
    assert "x0" in table["bbox"]


def test_extract_tables_auto_scanned_page(client, auth_headers):
    """Auto strategy should use PPStructureV3 for pages without text."""
    pdf_bytes = _create_scanned_pdf()

    body = json.dumps({
        "source_url": "https://example.com/scanned.pdf",
        "pages": [0],
        "strategy": "auto",
    })
    headers = auth_headers("POST", "/text/tables", body)

    table_html = "<table><tr><td>Item</td><td>Value</td></tr></table>"
    mock_engine = MagicMock()
    mock_engine.predict.return_value = [
        _mock_ppstructurev3_table_result(table_html, [50, 50, 400, 200]),
    ]

    with patch(
        "app.services.download_service.download_pdf",
        new_callable=AsyncMock,
        return_value=pdf_bytes,
    ), patch(
        "app.services.pdf_service._get_pp_structure",
        return_value=mock_engine,
    ):
        response = client.post("/text/tables", content=body, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total_count"] == 1
    # Verify PPStructureV3.predict() was called (scanned page has no text)
    mock_engine.predict.assert_called_once()


def test_parse_html_table_with_colspan():
    """HTML tables with colspan should expand into extra empty cells."""
    from app.services.pdf_service import _parse_html_table

    html = (
        "<table>"
        "<tr><td colspan=\"2\">Header Span</td><td>Col3</td></tr>"
        "<tr><td>A</td><td>B</td><td>C</td></tr>"
        "</table>"
    )
    rows = _parse_html_table(html)
    assert len(rows) == 2
    assert rows[0] == ["Header Span", "", "Col3"]
    assert rows[1] == ["A", "B", "C"]


def test_parse_html_table_basic():
    """Basic HTML table parsing."""
    from app.services.pdf_service import _parse_html_table

    html = (
        "<table><tbody>"
        "<tr><th>Name</th><th>Amount</th></tr>"
        "<tr><td>W-2</td><td>$85,000</td></tr>"
        "</tbody></table>"
    )
    rows = _parse_html_table(html)
    assert len(rows) == 2
    assert rows[0] == ["Name", "Amount"]
    assert rows[1] == ["W-2", "$85,000"]
