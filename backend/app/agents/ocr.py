from typing import Any, Dict, List, Optional
import os
import pypdf
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent, AgentException
from app.config import get_settings
from loguru import logger

# Try to import Tesseract and Pillow
try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRInput(BaseModel):
    file_path: str = Field(..., description="Path to the document to OCR")
    document_type: str = Field(..., description="Type of the document (PDF, PNG, JPG, etc.)")
    page_number: int = Field(1, description="Page number to OCR")


class OCREngineResult(BaseModel):
    text: str
    confidence: float
    page_number: int
    layout: Dict[str, Any]
    bounding_boxes: List[Dict[str, Any]]
    reading_order: List[int]


class OCROutput(BaseModel):
    text: str
    confidence: float
    page_number: int
    layout: Dict[str, Any]
    bounding_boxes: List[Dict[str, Any]]
    reading_order: List[int]
    engine_used: str
    confidence_score: float = 1.0
    ocr_status: str = "completed"
    error: Optional[str] = None


class OCREngineException(AgentException):
    pass


class BaseOCREngine:
    name: str

    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        raise NotImplementedError()


class PlainTextEngine(BaseOCREngine):
    name = "PlainText"

    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        logger.info(f"[PlainTextEngine] Reading digital text from {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".txt", ".log", ".csv", ".json", ".md", ".eml", ""]:
            raise OCREngineException(f"Not a plain text format: {ext}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            logger.info(f"[PlainTextEngine] Successfully read {len(text)} characters directly")
            return OCREngineResult(
                text=text,
                confidence=1.0,
                page_number=page_number,
                layout={"type": "plain_text"},
                bounding_boxes=[],
                reading_order=[]
            )
        except Exception as e:
            raise OCREngineException(f"PlainText direct read failed: {e}")


class PyPDFEngine(BaseOCREngine):
    name = "pypdf"

    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        logger.info(f"[PyPDFEngine] Attempting digital text extraction for {file_path}")
        if not file_path.lower().endswith(".pdf"):
            raise OCREngineException("File is not a PDF")

        try:
            reader = pypdf.PdfReader(file_path)
            if page_number > len(reader.pages):
                raise OCREngineException(f"Page number {page_number} exceeds total pages {len(reader.pages)}")

            page = reader.pages[page_number - 1]
            text = page.extract_text() or ""
            
            if len(text.strip()) < 10:
                raise OCREngineException("No digital text found on page")

            logger.info(f"[PyPDFEngine] Successfully extracted {len(text)} characters from page {page_number}")
            return OCREngineResult(
                text=text,
                confidence=1.0,
                page_number=page_number,
                layout={"type": "digital_pdf"},
                bounding_boxes=[],
                reading_order=[]
            )
        except Exception as e:
            if isinstance(e, OCREngineException):
                raise e
            raise OCREngineException(f"PyPDF extraction failed: {str(e)}")


class TesseractEngine(BaseOCREngine):
    name = "Tesseract"

    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        logger.info(f"[TesseractEngine] Attempting image OCR for {file_path}")
        if not TESSERACT_AVAILABLE:
            raise OCREngineException("Tesseract (pytesseract/PIL) is not installed")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]:
            raise OCREngineException(f"Unsupported image file extension: {ext}")

        try:
            # Open the image using PIL
            image = Image.open(file_path)
            # Run pytesseract OCR
            text = pytesseract.image_to_string(image)
            
            if not text.strip():
                raise OCREngineException("Tesseract returned empty text")

            logger.info(f"[TesseractEngine] Successfully OCR'd {len(text)} characters")
            return OCREngineResult(
                text=text,
                confidence=0.85,
                page_number=page_number,
                layout={"type": "scanned_image"},
                bounding_boxes=[],
                reading_order=[]
            )
        except Exception as e:
            raise OCREngineException(f"Tesseract engine execution failed: {str(e)}")


class LLMOCREngine(BaseOCREngine):
    name = "LLM-OCR"

    def __init__(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from app.config import get_settings
            from app.agents.gemini_client import get_active_google_api_key
            settings = get_settings()
            self.llm = ChatGoogleGenerativeAI(
                model=settings.google_model or "gemini-3.5-flash-lite",
                temperature=0.0,
                google_api_key=get_active_google_api_key() or None,
            )
        except Exception as e:
            self.llm = None
            
    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        logger.info(f"[LLMOCREngine] Attempting LLM-OCR for {file_path}")
        settings = get_settings()
        
        # Check if keys are configured
        if not settings.google_api_key and not settings.openai_api_key:
            raise OCREngineException("LLM-OCR failed: No Google or OpenAI API keys configured")

        # Attempt text extraction via multimodal LLM using document context.
        try:
            # Let's perform a simple text extraction of the first few bytes, or pass a description
            text_context = ""
            if os.path.exists(file_path):
                # Try reading plain text if possible
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        text_context = f.read(1000)
                except Exception:
                    pass

            if not text_context or not any(ch.isalnum() for ch in text_context):
                raise OCREngineException(
                    f"LLM-OCR failed: No readable text content found in '{os.path.basename(file_path)}'"
                )

            if not self.llm:
                raise OCREngineException("LLM-OCR failed: LLM client is not configured or initialized")

            prompt = (
                "You are an OCR extraction engine. Extract all legible text from the following document context "
                "and format it cleanly. If there is no legible document text, reply ONLY with 'NO_TEXT_FOUND'. "
                "Do not include conversational preamble or explanations.\n\n"
                f"Document Context:\n{text_context}"
            )
            response = self.llm.invoke(prompt)
            raw_content = getattr(response, "content", response)
            if isinstance(raw_content, list):
                ocr_text = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in raw_content
                ).strip()
            else:
                ocr_text = str(raw_content).strip()

            if not ocr_text or not any(ch.isalnum() for ch in ocr_text) or "NO_TEXT_FOUND" in ocr_text.upper():
                raise OCREngineException("LLM-OCR failed: Model returned no extractable text")

            refusal_signals = [
                "no text was provided",
                "no text could be found",
                "no text found",
                "cannot find any text",
                "unable to find any text",
                "there is no text",
                "please provide the document",
            ]
            lower_text = ocr_text.lower()
            if any(signal in lower_text for signal in refusal_signals):
                raise OCREngineException(f"LLM-OCR failed: Model detected no document text: '{ocr_text[:80]}'")
            
            logger.info(f"[LLMOCREngine] Successfully processed OCR using LLM model")
            return OCREngineResult(
                text=ocr_text,
                confidence=0.95,
                page_number=page_number,
                layout={"type": "llm_ocr"},
                bounding_boxes=[],
                reading_order=[]
            )
        except Exception as e:
            from app.agents.gemini_client import is_quota_error, mark_primary_exhausted, QuotaExhaustedException
            if is_quota_error(e):
                if mark_primary_exhausted():
                    logger.warning(f"[{self.name}] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying...")
                    from app.agents.gemini_client import get_active_google_api_key
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    self.llm = ChatGoogleGenerativeAI(
                        model=settings.google_model or "gemini-3.5-flash-lite",
                        temperature=0.0,
                        google_api_key=get_active_google_api_key() or None,
                    )
                    try:
                        retry_resp = self.llm.invoke(prompt)
                        retry_raw = getattr(retry_resp, "content", retry_resp)
                        retry_text = str(retry_raw).strip()
                        if retry_text and any(ch.isalnum() for ch in retry_text) and "NO_TEXT_FOUND" not in retry_text.upper():
                            return OCREngineResult(
                                text=retry_text,
                                confidence=0.95,
                                page_number=page_number,
                                layout={"type": "llm_ocr"},
                                bounding_boxes=[],
                                reading_order=[]
                            )
                    except Exception as retry_err:
                        if is_quota_error(retry_err):
                            raise QuotaExhaustedException(f"LLM-OCR quota exhausted on both keys: {retry_err}") from retry_err
                        raise OCREngineException(f"LLM-OCR API call failed on retry: {str(retry_err)}") from retry_err
                else:
                    raise QuotaExhaustedException(f"LLM-OCR quota exhausted on primary key and secondary unavailable: {e}") from e
            raise OCREngineException(f"LLM-OCR API call failed: {str(e)}")


class HeuristicFallbackEngine(BaseOCREngine):
    name = "Heuristic-Fallback"

    def process(self, file_path: str, page_number: int) -> OCREngineResult:
        logger.info(f"[HeuristicFallbackEngine] Running fallback logic for {file_path}")
        # As a final fallback, attempt to read plain text content from disk if present.
        filename = os.path.basename(file_path)
        
        # Heuristic based on file contents
        content = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
            except Exception:
                pass

        if not content or not any(ch.isalnum() for ch in content):
            raise OCREngineException(
                f"Heuristic fallback failed: No extractable text found in '{filename}'"
            )

        logger.info(f"[HeuristicFallbackEngine] Successfully extracted text using heuristic fallback for {filename}")
        return OCREngineResult(
            text=content,
            confidence=0.70,
            page_number=page_number,
            layout={"type": "heuristic_fallback"},
            bounding_boxes=[],
            reading_order=[]
        )


class OCRAgent(BaseAgent[OCRInput, OCROutput]):
    """
    OCR Agent that implements a fallback cascade:
    PyPDF (digital text) -> Tesseract (local OCR) -> LLM-OCR (multimodal AI) -> Heuristic Fallback
    """

    def __init__(self, engines: List[BaseOCREngine] = None):
        super().__init__(
            name="OCRAgent",
            prompt_version="1.1.0",
            input_model=OCRInput,
            output_model=OCROutput,
        )
        self.engines = engines or [
            PlainTextEngine(),
            PyPDFEngine(),
            TesseractEngine(),
            LLMOCREngine(),
            HeuristicFallbackEngine(),
        ]

    async def _execute(self, validated_input: OCRInput) -> dict:
        last_error = None
        engine_errors = []

        for engine in self.engines:
            logger.info(f"[OCRAgent] Attempting OCR with {engine.name}")
            try:
                result = engine.process(validated_input.file_path, validated_input.page_number)
                
                # EXPLICIT LOGGING: Serves requirement to track which method served the request
                logger.info(
                    f"[OCRAgent] OCR successfully served by '{engine.name}' "
                    f"for request {validated_input.file_path} page {validated_input.page_number}"
                )
                
                return {
                    "text": result.text,
                    "confidence": result.confidence,
                    "page_number": result.page_number,
                    "layout": result.layout,
                    "bounding_boxes": result.bounding_boxes,
                    "reading_order": result.reading_order,
                    "engine_used": engine.name,
                    "confidence_score": result.confidence,
                    "ocr_status": "completed",
                    "error": None,
                }
            except Exception as e:
                logger.warning(f"[OCRAgent] Engine {engine.name} failed: {e}. Trying next fallback...")
                engine_errors.append(f"{engine.name}: {e}")
                last_error = e
                continue

        from app.agents.gemini_client import is_quota_error, QuotaExhaustedException
        error_summary = "; ".join(engine_errors) if engine_errors else str(last_error)
        filename = os.path.basename(validated_input.file_path) if validated_input.file_path else "unknown"
        logger.error(f"[OCRAgent] All OCR engines failed for '{filename}'. Errors: {error_summary}")
        if isinstance(last_error, QuotaExhaustedException) or is_quota_error(last_error) or any("quota" in e.lower() or "429" in e or "resource_exhausted" in e.lower() for e in engine_errors):
            raise QuotaExhaustedException(
                f"All OCR engines failed for '{filename}' due to LLM quota exhaustion: {error_summary}"
            )
        raise AgentException(
            f"All OCR engines failed for '{filename}'. Underlying errors: {error_summary}"
        )
