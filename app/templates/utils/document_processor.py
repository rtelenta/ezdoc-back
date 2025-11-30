import base64
import os
import tempfile
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any
from io import BytesIO
from docxtpl import DocxTemplate
from jinja2 import Environment, DebugUndefined


class MissingValueUndefined(DebugUndefined):
    """Custom undefined handler that shows missing field names."""

    def __str__(self):
        return f"[MISSING: {self._undefined_name}]"

    def __repr__(self):
        return f"[MISSING: {self._undefined_name}]"


def process_docx_from_base64(base64_content: str, data: Dict[str, Any]) -> bytes:
    """
    Process DOCX template from base64 content with JSON data and return PDF bytes.
    Uses LibreOffice for PDF conversion (Lambda compatible).

    Args:
        base64_content: Base64 encoded DOCX file content
        data: JSON data to replace placeholders in template

    Returns:
        PDF file content as bytes

    Raises:
        Exception: If processing fails
    """
    try:
        # Decode base64 content directly to bytes
        docx_content = base64.b64decode(base64_content)

        # Process DOCX in memory using BytesIO
        processed_docx_bytes = process_docx_in_memory(docx_content, data)

        # Convert to PDF using LibreOffice (works in Lambda with layer)
        return convert_docx_to_pdf_with_libreoffice(processed_docx_bytes)

    except Exception as e:
        raise Exception(f"Document processing failed: {str(e)}")


def convert_docx_to_pdf_with_libreoffice(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX to PDF using LibreOffice with minimal temp files.

    Args:
        docx_bytes: Processed DOCX content as bytes

    Returns:
        PDF content as bytes
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        file_id = str(uuid.uuid4())

        # Write processed DOCX to temp file (required for LibreOffice)
        temp_docx = temp_path / f"processed_{file_id}.docx"
        with open(temp_docx, "wb") as f:
            f.write(docx_bytes)

        # Convert to PDF
        output_pdf = temp_path / f"final_{file_id}.pdf"
        convert_docx_to_pdf(str(temp_docx), str(output_pdf))

        # Read PDF content into memory
        with open(output_pdf, "rb") as pdf_file:
            return pdf_file.read()


def get_libreoffice_path() -> str:
    """
    Get LibreOffice executable path (Lambda layer compatible).

    Returns:
        Path to LibreOffice executable
    """
    # Check for Lambda layer path first
    lambda_path = "/opt/libreoffice/program/soffice.bin"
    if os.path.exists(lambda_path):
        return lambda_path

    # Fallback to system installation
    return "libreoffice"


def process_docx_in_memory(docx_bytes: bytes, data: Dict[str, Any]) -> bytes:
    """
    Process DOCX template in memory without creating temporary files.

    Args:
        docx_bytes: DOCX file content as bytes
        data: JSON data to replace placeholders in template

    Returns:
        Processed DOCX content as bytes
    """
    # Create BytesIO objects for in-memory processing
    input_stream = BytesIO(docx_bytes)
    output_stream = BytesIO()

    # Load template from memory
    template = DocxTemplate(input_stream)

    # Set up Jinja2 environment to handle missing values gracefully
    env = Environment(undefined=MissingValueUndefined)
    template.environment = env

    try:
        # Render template with data
        template.render(data)
    except Exception as e:
        print(f"⚠️  Warning during template processing: {e}")
        print("📝 Continuing with available data...")

    # Save processed document to memory
    template.save(output_stream)

    # Return the processed bytes
    return output_stream.getvalue()


def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    """Convert DOCX to PDF using LibreOffice (Lambda compatible)."""

    try:
        # Get LibreOffice path (Lambda layer or system)
        libreoffice_cmd = get_libreoffice_path()

        # Check if LibreOffice is available
        result = subprocess.run(
            [libreoffice_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10,  # Increased for Lambda cold starts
        )

        if result.returncode != 0:
            raise FileNotFoundError(f"LibreOffice not found at {libreoffice_cmd}")

        # Convert using LibreOffice with Lambda-optimized arguments
        output_dir = Path(pdf_path).parent
        result = subprocess.run(
            [
                libreoffice_cmd,
                "--headless",
                "--invisible",
                "--nodefault",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout for Lambda
        )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, "libreoffice")

        # LibreOffice creates PDF with same base name
        generated_pdf = output_dir / (Path(docx_path).stem + ".pdf")

        # Check if LibreOffice actually created the PDF
        if not generated_pdf.exists():
            raise FileNotFoundError(
                f"LibreOffice failed to create PDF: {generated_pdf}"
            )

        # Rename if necessary
        if str(generated_pdf) != pdf_path:
            generated_pdf.rename(pdf_path)

        # Final verification
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"Final PDF not found at: {pdf_path}")

    except FileNotFoundError:
        raise Exception(
            "LibreOffice not found! "
            "For Lambda: Add LibreOffice layer. "
            "For local: Install with 'sudo apt install libreoffice --no-install-recommends'"
        )
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e}")
    except subprocess.TimeoutExpired:
        raise Exception("LibreOffice conversion timed out")
