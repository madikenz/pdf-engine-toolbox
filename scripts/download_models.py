"""Pre-download PaddleOCR PP-OCRv5 and PPStructureV3 models during Docker build.

This avoids ~300 MB download on first request at runtime.
Runs with || true semantics — failure here is non-fatal.
"""
from paddleocr import PaddleOCR, PPStructureV3

PaddleOCR(
    ocr_version="PP-OCRv5",
    lang="en",
    device="cpu",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=True,
)

PPStructureV3(
    device="cpu",
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    use_seal_recognition=False,
    use_formula_recognition=False,
    use_chart_recognition=False,
    use_table_recognition=True,
)
