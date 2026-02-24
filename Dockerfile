FROM python:3.12-slim

WORKDIR /app

# Install system dependencies:
# - curl: for health checks
# - libgomp1: OpenMP runtime required by PaddlePaddle
# - libheif: for HEIC image support (iPhone photos)
# - libgl1: required by opencv-python-headless
# - libreoffice-core + writer + calc + impress: for office-to-PDF conversion
# - fonts-liberation: standard fonts for LibreOffice rendering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
        libheif-dev \
        libgl1 \
        libreoffice-core \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir setuptools && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download PaddleOCR PP-OCRv5 models + PPStructureV3 table models
# during build (avoids ~300 MB download at runtime).
# Allow failure: if model pre-download fails (e.g. segfault in CI),
# models will download on first request instead.
RUN python -c "\
from paddleocr import PaddleOCR, PPStructureV3; \
PaddleOCR(ocr_version='PP-OCRv5', lang='en', device='cpu', \
    use_doc_orientation_classify=False, use_doc_unwarping=False, \
    use_textline_orientation=True); \
PPStructureV3(device='cpu', lang='en', \
    use_doc_orientation_classify=False, use_doc_unwarping=False, \
    use_textline_orientation=False, use_seal_recognition=False, \
    use_formula_recognition=False, use_chart_recognition=False, \
    use_table_recognition=True)" || echo "Model pre-download failed; models will download at runtime"

# Copy application code
COPY app/ ./app/

# Create non-root user and cache/temp directories
# Copy PaddleX models if they were pre-downloaded
RUN useradd -m -r appuser && \
    mkdir -p /app/cache /tmp/libreoffice && \
    (cp -r /root/.paddlex /home/appuser/.paddlex 2>/dev/null || true) && \
    chown -R appuser:appuser /app /tmp/libreoffice /home/appuser

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
