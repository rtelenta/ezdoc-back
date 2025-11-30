import base64
import tempfile
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any
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

    Args:
        base64_content: Base64 encoded DOCX file content
        data: JSON data to replace placeholders in template

    Returns:
        PDF file content as bytes

    Raises:
        Exception: If processing fails
    """
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Generate unique filenames
        file_id = str(uuid.uuid4())
        template_docx = temp_path / f"template_{file_id}.docx"
        output_docx = temp_path / f"processed_{file_id}.docx"
        output_pdf = temp_path / f"final_{file_id}.pdf"

        try:
            # Decode base64 content and save as DOCX file
            docx_content = base64.b64decode(base64_content)
            with open(template_docx, "wb") as f:
                f.write(docx_content)

            # Process DOCX with provided data
            process_docx_file(str(template_docx), data, str(output_docx))

            # Convert to PDF
            convert_docx_to_pdf(str(output_docx), str(output_pdf))

            # Read PDF content into memory
            with open(output_pdf, "rb") as pdf_file:
                return pdf_file.read()

        except Exception as e:
            raise Exception(f"Document processing failed: {str(e)}")


def process_docx_file(docx_path: str, data: Dict[str, Any], output_docx_path: str):
    """Process DOCX file and replace placeholders with data using docxtpl."""

    # Load template
    template = DocxTemplate(docx_path)

    # Set up Jinja2 environment to handle missing values gracefully
    env = Environment(undefined=MissingValueUndefined)
    template.environment = env

    try:
        # Render template with data
        template.render(data)
    except Exception as e:
        print(f"⚠️  Warning during template processing: {e}")
        print("📝 Continuing with available data...")

    # Save processed document
    template.save(output_docx_path)


def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    """Convert DOCX to PDF using LibreOffice."""

    try:
        # Check if LibreOffice is available
        result = subprocess.run(
            ["libreoffice", "--version"], capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            raise FileNotFoundError("LibreOffice not found")

        # Convert using LibreOffice
        output_dir = Path(pdf_path).parent
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
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
            "LibreOffice is not installed! "
            "Install it with: sudo apt install libreoffice --no-install-recommends"
        )
    except subprocess.CalledProcessError as e:
        raise Exception(f"LibreOffice conversion failed: {e}")
    except subprocess.TimeoutExpired:
        raise Exception("LibreOffice conversion timed out")
