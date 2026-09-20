"""
OCR package — provider adapters for document text extraction.

Supports multiple OCR engines behind a common interface:
    - PaddleOCR (primary)
    - PyMuPDF (text-layer extraction)
    - Tesseract (fallback)
    - DocTR / EasyOCR (additional fallbacks)

Implementations are added in Part 2.
"""
