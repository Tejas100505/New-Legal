import hashlib
import mimetypes
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent, AgentException


class IngestionInput(BaseModel):
    file_path: Optional[str] = Field(None, description="Path to the saved uploaded file")
    file_bytes: Optional[bytes] = Field(None, description="In-memory bytes of the uploaded file")
    original_filename: str = Field(..., description="Original name of the uploaded file")
    custodian: Optional[str] = Field("Unknown", description="Custodian of the document")
    existing_hashes: list[str] = Field(default_factory=list, description="List of existing document hashes to check for duplicates")


class IngestionOutput(BaseModel):
    filename: str
    upload_timestamp: str
    document_type: str
    custodian: str
    mime_type: str
    file_size: int
    hash: str
    confidence_score: float = 1.0


class CorruptFileException(AgentException):
    pass


class DuplicateFileException(AgentException):
    pass


class UnsupportedFileException(AgentException):
    pass


class DocumentIngestionAgent(BaseAgent[IngestionInput, IngestionOutput]):
    
    SUPPORTED_EXTENSIONS = {
        ".pdf", ".docx", ".txt", ".eml", ".png", ".jpg", ".jpeg", ".tiff", ".zip"
    }
    
    def __init__(self):
        super().__init__(
            name="DocumentIngestionAgent",
            prompt_version="1.0.0",
            input_model=IngestionInput,
            output_model=IngestionOutput,
        )

    async def _execute(self, validated_input: IngestionInput) -> dict:
        ext = Path(validated_input.original_filename).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileException(f"Unsupported file type: {ext}")

        if validated_input.file_bytes is not None:
            content = validated_input.file_bytes
            file_size = len(content)
            if file_size == 0:
                raise CorruptFileException("File is empty or corrupt")
            file_hash = hashlib.sha256(content).hexdigest()

            if ext == ".zip":
                try:
                    import io
                    with zipfile.ZipFile(io.BytesIO(content), 'r') as z:
                        if z.testzip() is not None:
                            raise CorruptFileException("ZIP file is corrupt")
                except zipfile.BadZipFile:
                    raise CorruptFileException("ZIP file is corrupt or not a valid zip")
        else:
            if not validated_input.file_path:
                raise AgentException("Either file_bytes or file_path must be provided")
            file_path = Path(validated_input.file_path)
            if not file_path.exists():
                raise AgentException(f"File not found: {validated_input.file_path}")

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise CorruptFileException("File is empty or corrupt")

            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            file_hash = sha256_hash.hexdigest()

            if ext == ".zip":
                try:
                    with zipfile.ZipFile(file_path, 'r') as z:
                        if z.testzip() is not None:
                            raise CorruptFileException("ZIP file is corrupt")
                except zipfile.BadZipFile:
                    raise CorruptFileException("ZIP file is corrupt or not a valid zip")
                
        # 4. Reject duplicates
        if file_hash in validated_input.existing_hashes:
            raise DuplicateFileException(f"Duplicate file detected. Hash: {file_hash}")

        # Extract metadata (mime type, etc.)
        mime_type, _ = mimetypes.guess_type(validated_input.original_filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Format output
        return {
            "filename": validated_input.original_filename,
            "upload_timestamp": datetime.now(timezone.utc).isoformat() if hasattr(datetime, 'now') else datetime.utcnow().isoformat() + "Z",
            "document_type": ext.lstrip(".").upper(),
            "custodian": validated_input.custodian or "Unknown",
            "mime_type": mime_type,
            "file_size": file_size,
            "hash": file_hash,
            "confidence_score": 1.0
        }
