import os
import tempfile
import pytest
import hashlib
from pathlib import Path
from app.agents.ingestion import (
    DocumentIngestionAgent,
    IngestionInput,
    CorruptFileException,
    DuplicateFileException,
    UnsupportedFileException
)

@pytest.fixture
def agent():
    return DocumentIngestionAgent()

@pytest.fixture
def sample_pdf():
    # Create a dummy PDF file
    fd, path = tempfile.mkstemp(suffix=".pdf")
    with os.fdopen(fd, 'wb') as f:
        f.write(b"%PDF-1.4\n%Fake PDF content for testing\n")
    yield path
    os.remove(path)

@pytest.fixture
def corrupt_zip():
    # Create a corrupt ZIP file
    fd, path = tempfile.mkstemp(suffix=".zip")
    with os.fdopen(fd, 'wb') as f:
        f.write(b"Not a zip file at all, just garbage data")
    yield path
    os.remove(path)

@pytest.fixture
def empty_file():
    # Create an empty file
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, 'wb') as f:
        pass
    yield path
    os.remove(path)


@pytest.mark.asyncio
async def test_upload_sample_pdf(agent, sample_pdf):
    input_data = IngestionInput(
        file_path=sample_pdf,
        original_filename="test_upload.pdf",
        existing_hashes=[]
    )
    result = await agent.run(input_data)
    
    assert result.filename == "test_upload.pdf"
    assert result.document_type == "PDF"
    assert result.file_size > 0
    assert result.hash is not None


@pytest.mark.asyncio
async def test_duplicate_detection(agent, sample_pdf):
    # First, calculate hash of our sample
    sha256_hash = hashlib.sha256()
    with open(sample_pdf, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()
    
    # Try to upload with the hash in existing_hashes
    input_data = IngestionInput(
        file_path=sample_pdf,
        original_filename="duplicate.pdf",
        existing_hashes=[file_hash]
    )
    
    with pytest.raises(DuplicateFileException):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_corrupt_file_rejected_empty(agent, empty_file):
    input_data = IngestionInput(
        file_path=empty_file,
        original_filename="empty.txt",
        existing_hashes=[]
    )
    
    with pytest.raises(CorruptFileException, match="File is empty or corrupt"):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_corrupt_file_rejected_zip(agent, corrupt_zip):
    input_data = IngestionInput(
        file_path=corrupt_zip,
        original_filename="bad.zip",
        existing_hashes=[]
    )
    
    with pytest.raises(CorruptFileException, match="ZIP file is corrupt"):
        await agent.run(input_data)
