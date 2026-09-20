import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import spacy
from loguru import logger

from app.agents.base import BaseAgent, AgentException

# Resolved path to fine-tuned spaCy NER model
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "legal_ner_ediscovery_v1"

# Regex patterns for deterministic CASE_REFERENCE extraction
# NOTE: Per data/entity_labeling/ner_evaluation_results.json, the fine-tuned neural model's
# CASE_REFERENCE component achieved 0.0 F1 (0.0 precision, 0.0 recall, support=1) on the
# held-out test split due to severe annotation sparsity. Following the model self-review
# recommendation, neural CASE_REFERENCE predictions are discarded, and regex is used as
# the sole, authoritative source for this entity type.
CASE_REFERENCE_PATTERNS = [
    # Case / Docket / Matter / Civil Action / Arbitration numbers
    re.compile(r"(?i)\b(?:Docket\s+(?:Nos?\.?|#)?|FERC\s+Docket(?:\s+Nos?\.?)?)\s*:?\s*(?:[A-Z0-9]{1,8}[-–/][A-Z0-9-–/]+|\d{4,8})\b"),
    re.compile(r"(?i)\b(?:Case\s+(?:Nos?\.?|#)?|Matter\s+(?:Nos?\.?|#)?|Civil\s+Action\s+(?:No\.?|#)|Proceeding\s+(?:No\.?|#)|Arbitration\s+(?:No\.?|#))\s*:?\s*(?:[A-Z0-9]{1,8}[-–/][A-Z0-9-–/]+|\d{3,10}(?:-[\w-]+)?)\b"),
    re.compile(r"\bCase\s+No\.?\s*[\w-]+\b", re.IGNORECASE),
    # Adversarial litigation names (e.g., Apex v. RailCorp, ENA v. Triad)
    re.compile(r"\b([A-Z][A-Za-z0-9&.\'-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&.\'-]+)?)[^\S\r\n]+v[s.]*[^\S\r\n]+([A-Z][A-Za-z0-9&.\'-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&.\'-]+)?)\b"),
    # In re matters (e.g., In re Enron Corp., In re Apex Logistics)
    re.compile(r"\bIn\s+re\s+([A-Z][A-Za-z0-9\s,&.\'-]{2,30}?)(?:\s+Litigation|\s+Bankruptcy|,|\n|\.|\)|;)"),
    # Regulatory docket IDs (e.g., EL01-47, RP00-42)
    re.compile(r"\b([A-Z]{2}\d{2}-\d+(?:-\d+)?)\b"),
]

_nlp_pipeline: Optional[spacy.language.Language] = None


def get_ner_pipeline() -> spacy.language.Language:
    """Loads and caches the fine-tuned Legal NER pipeline singleton."""
    global _nlp_pipeline
    if _nlp_pipeline is None:
        if MODEL_DIR.exists():
            try:
                logger.info(f"[EntityExtraction] Loading fine-tuned legal NER model from: {MODEL_DIR}")
                _nlp_pipeline = spacy.load(str(MODEL_DIR))
            except (MemoryError, Exception) as e:
                logger.warning(f"[EntityExtraction] Failed to load fine-tuned model ({e}). Falling back to blank model.")
                _nlp_pipeline = spacy.blank("en")
        else:
            logger.warning(f"[EntityExtraction] Model path {MODEL_DIR} not found. Falling back to blank model.")
            _nlp_pipeline = spacy.blank("en")
    return _nlp_pipeline


class EntityExtractionInput(BaseModel):
    document_id: str
    text: str


class EntityItem(BaseModel):
    """Unified entity representation capturing entity text, label, source, and offsets."""
    text: str
    label: str
    source: str  # 'fine_tuned_model' or 'regex'
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class Entities(BaseModel):
    people: List[str] = []
    organizations: List[str] = []
    courts: List[str] = []
    lawyers: List[str] = []
    addresses: List[str] = []
    money: List[str] = []
    dates: List[str] = []
    acts: List[str] = []
    case_numbers: List[str] = []
    # Extended legal entities from fine-tuned model & regex
    attorneys: List[str] = []
    custodians: List[str] = []
    privilege_markers: List[str] = []
    case_references: List[str] = []
    locations: List[str] = []


class EntityExtractionOutput(BaseModel):
    document_id: str
    entities: Entities
    entity_list: List[EntityItem] = []
    confidence_score: float = 0.95


# Alias for compatibility with existing references
EntityOutput = EntityExtractionOutput


class EntityExtractionAgent(BaseAgent[EntityExtractionInput, EntityExtractionOutput]):
    """
    Extracts entities using the fine-tuned Legal NER model (legal_ner_ediscovery_v1).
    - ATTORNEY, CUSTODIAN, PRIVILEGE_MARKER: extracted from fine-tuned neural heads.
    - Base generic entities (PERSON, ORG, DATE, MONEY, GPE, LAW): extracted from fine-tuned base layer.
    - CASE_REFERENCE: extracted via deterministic regex patterns (per ner_evaluation_results.json finding).
    """

    def __init__(self):
        super().__init__(
            name="EntityExtractionAgent",
            prompt_version="2.0.0",
            input_model=EntityExtractionInput,
            output_model=EntityExtractionOutput,
        )
        self.nlp = get_ner_pipeline()

    async def _execute(self, validated_input: EntityExtractionInput) -> dict:
        logger.info(f"[{self.name}] Extracting entities for document {validated_input.document_id}")
        
        try:
            text = validated_input.text or ""
            doc = self.nlp(text)

            entity_list: List[EntityItem] = []
            
            people_set = set()
            orgs_set = set()
            courts_set = set()
            lawyers_set = set()
            custodians_set = set()
            privilege_markers_set = set()
            dates_set = set()
            money_set = set()
            locations_set = set()
            addresses_set = set()
            acts_set = set()
            case_numbers_set = set()

            # 1. Extract from fine-tuned neural model
            for ent in doc.ents:
                ent_text = ent.text.strip()
                if not ent_text:
                    continue

                label = ent.label_

                # NOTE: Per data/entity_labeling/ner_evaluation_results.json, CASE_REFERENCE achieved
                # 0.0 F1 (0.0 precision, 0.0 recall, support=1) on the held-out test split due
                # to extreme sparsity in the training annotations. We discard any neural CASE_REFERENCE
                # predictions and rely exclusively on deterministic regex patterns below.
                if label == "CASE_REFERENCE":
                    continue

                entity_list.append(EntityItem(
                    text=ent_text,
                    label=label,
                    source="fine_tuned_model",
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                ))

                if label == "ATTORNEY":
                    lawyers_set.add(ent_text)
                elif label == "CUSTODIAN":
                    custodians_set.add(ent_text)
                    people_set.add(ent_text)
                elif label == "PRIVILEGE_MARKER":
                    privilege_markers_set.add(ent_text)
                elif label == "PERSON":
                    people_set.add(ent_text)
                elif label == "ORG":
                    orgs_set.add(ent_text)
                    if "court" in ent_text.lower() or "tribunal" in ent_text.lower():
                        clean_court = re.sub(r'^(?:the|a|an)\s+', '', ent_text, flags=re.IGNORECASE)
                        courts_set.add(clean_court)
                elif label == "DATE":
                    dates_set.add(ent_text)
                elif label == "MONEY":
                    money_set.add(ent_text)
                elif label in ("GPE", "LOC", "FAC"):
                    locations_set.add(ent_text)
                    addresses_set.add(ent_text)
                    if "court" in ent_text.lower() or "tribunal" in ent_text.lower():
                        clean_court = re.sub(r'^(?:the|a|an)\s+', '', ent_text, flags=re.IGNORECASE)
                        courts_set.add(clean_court)
                elif label == "LAW":
                    acts_set.add(ent_text)

            # 2. Extract CASE_REFERENCE via deterministic regex patterns
            for pat in CASE_REFERENCE_PATTERNS:
                for match in pat.finditer(text):
                    c_text = match.group(0).strip()
                    if c_text and c_text not in case_numbers_set:
                        case_numbers_set.add(c_text)
                        entity_list.append(EntityItem(
                            text=c_text,
                            label="CASE_REFERENCE",
                            source="regex",
                            start_char=match.start(),
                            end_char=match.end(),
                        ))

            # 3. Supplemental regex for currency patterns ($X,XXX.XX)
            for m in re.finditer(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', text):
                m_text = m.group(0).strip()
                if m_text not in money_set:
                    money_set.add(m_text)
                    entity_list.append(EntityItem(
                        text=m_text,
                        label="MONEY",
                        source="regex",
                        start_char=m.start(),
                        end_char=m.end(),
                    ))

            # Build structured Entities output matching existing schema
            entities = Entities(
                people=sorted(list(people_set)),
                organizations=sorted(list(orgs_set)),
                courts=sorted(list(courts_set)),
                lawyers=sorted(list(lawyers_set)),
                addresses=sorted(list(addresses_set)),
                money=sorted(list(money_set)),
                dates=sorted(list(dates_set)),
                acts=sorted(list(acts_set)),
                case_numbers=sorted(list(case_numbers_set)),
                attorneys=sorted(list(lawyers_set)),
                custodians=sorted(list(custodians_set)),
                privilege_markers=sorted(list(privilege_markers_set)),
                case_references=sorted(list(case_numbers_set)),
                locations=sorted(list(locations_set)),
            )

            return {
                "document_id": validated_input.document_id,
                "entities": entities.model_dump(),
                "entity_list": [item.model_dump() for item in entity_list],
                "confidence_score": 0.95,
            }
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            raise AgentException(f"Entity extraction failed: {e}")
