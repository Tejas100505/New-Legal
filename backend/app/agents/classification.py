from typing import Any, Dict, List
import os
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException
from loguru import logger
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

class ClassificationInput(BaseModel):
    text: str = Field(..., description="Extracted text from the document")
    filename: str = Field("unknown", description="Original filename")
    document_id: str | None = Field(None, description="Optional document ID")

class ClassificationOutput(BaseModel):
    document_type: str
    is_privileged: bool
    confidence_score: float = 1.0

    @property
    def category(self) -> str:
        return self.document_type

class ClassificationAgent(BaseAgent[ClassificationInput, ClassificationOutput]):
    """
    Classifies documents using Gemini LLM.
    """
    
    def __init__(self):
        super().__init__(
            name="ClassificationAgent",
            prompt_version="1.0.0",
            input_model=ClassificationInput,
            output_model=ClassificationOutput,
        )
        # Use GOOGLE_API_KEY from environment (loaded by config.py's load_dotenv)
        try:
            from app.config import get_settings
            from app.agents.gemini_client import get_active_google_api_key
            settings = get_settings()
            primary_model = settings.google_model or "gemini-3.5-flash-lite"
            active_key = get_active_google_api_key()
            self.llm = ChatGoogleGenerativeAI(
                model=primary_model,
                temperature=0.0,
                google_api_key=active_key or None,
            )
            fallback_model = getattr(settings, "google_model_fallback", "gemini-3.8-flash")
            self.fallback_llm = ChatGoogleGenerativeAI(
                model=fallback_model,
                temperature=0.0,
                google_api_key=active_key or None,
            ) if fallback_model else None
        except Exception as e:
            logger.warning(f"Could not initialize Gemini LLM for classification: {e}")
            self.llm = None
            self.fallback_llm = None

    async def _execute(self, validated_input: ClassificationInput) -> dict:
        logger.info(f"[{self.name}] Classifying document: {validated_input.filename}")
        
        text_lower = (validated_input.text or "").lower()
        fallback_type = "Contracts" if ("contract" in text_lower or "agreement" in text_lower) else "Document"

        if not self.llm:
            logger.warning("LLM not configured, using mock classification.")
            return {
                "document_type": fallback_type,
                "is_privileged": "privilege" in text_lower or "attorney" in text_lower,
                "confidence_score": 0.95
            }
            
        prompt = PromptTemplate.from_template(
            "You are a legal document classifier. Analyze the following text extracted from a file named {filename}.\n"
            "Determine the document type (e.g., Contract, Invoice, Court Order, Email, Evidence, Notice) "
            "and whether it contains privileged information (true/false).\n\n"
            "Text (truncated if too long):\n{text}\n\n"
            "Respond strictly in JSON format like exactly this: {{\"document_type\": \"...\", \"is_privileged\": false, \"confidence_score\": 0.95}}"
        )
        
        truncated_text = validated_input.text[:15000] if validated_input.text else "Empty document"
        
        from app.agents.gemini_client import is_quota_error, mark_primary_exhausted, get_active_google_api_key, QuotaExhaustedException
        try:
            chain = prompt | self.llm
            response = None
            for attempt in range(3):
                try:
                    response = await chain.ainvoke({"filename": validated_input.filename, "text": truncated_text})
                    break
                except Exception as primary_err:
                    if is_quota_error(primary_err):
                        if mark_primary_exhausted():
                            logger.warning(f"[{self.name}] 429 Quota Exhausted on primary key. Switched to GOOGLE_API_KEY_2. Retrying...")
                            from app.config import get_settings
                            settings = get_settings()
                            primary_model = settings.google_model or "gemini-3.5-flash-lite"
                            self.llm = ChatGoogleGenerativeAI(
                                model=primary_model,
                                temperature=0.0,
                                google_api_key=get_active_google_api_key(),
                            )
                            chain = prompt | self.llm
                            response = await chain.ainvoke({"filename": validated_input.filename, "text": truncated_text})
                            break
                        elif attempt < 2:
                            import asyncio
                            logger.warning(f"[{self.name}] Rate limited (attempt {attempt+1}/3). Waiting 15s...")
                            await asyncio.sleep(15.0)
                            continue
                    if self.fallback_llm and not is_quota_error(primary_err):
                        fallback_name = getattr(self.fallback_llm, "model", "fallback")
                        logger.warning(
                            f"[{self.name}] Primary classification model failed ({primary_err}). "
                            f"Retrying with fallback model {fallback_name}..."
                        )
                        fallback_chain = prompt | self.fallback_llm
                        response = await fallback_chain.ainvoke({"filename": validated_input.filename, "text": truncated_text})
                        break
                    raise primary_err
            
            # Very basic JSON extraction from Markdown if wrapped
            if isinstance(response.content, list):
                parts = []
                for c in response.content:
                    if isinstance(c, dict):
                        parts.append(c.get("text", ""))
                    elif hasattr(c, "text"):
                        parts.append(str(c.text))
                    else:
                        parts.append(str(c))
                raw = "".join(parts)
            else:
                raw = str(response.content)
            
            content = raw.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            import json
            result = json.loads(content)
            
            return {
                "document_type": result.get("document_type", fallback_type),
                "is_privileged": result.get("is_privileged", False),
                "confidence_score": float(result.get("confidence_score", 0.95))
            }
        except Exception as e:
            if is_quota_error(e) or isinstance(e, QuotaExhaustedException):
                raise QuotaExhaustedException(f"[{self.name}] LLM quota exhausted on both keys: {e}") from e
            logger.error(f"Classification failed: {e}")
            # Fallback for non-quota errors
            return {
                "document_type": fallback_type,
                "is_privileged": "privilege" in text_lower or "attorney" in text_lower,
                "confidence_score": 0.95
            }

