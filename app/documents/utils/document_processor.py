import base64
import os
import tempfile
import subprocess
import uuid
import logging
import tarfile
import brotli
from pathlib import Path
from typing import Dict, Any
from io import BytesIO
from docxtpl import DocxTemplate
from jinja2 import Environment, DebugUndefined

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        logger.info("Starting document processing")
        logger.info(
            f"Input base64 size: {len(base64_content)} chars, data keys: {list(data.keys())}"
        )

        # Decode base64 content directly to bytes
        docx_content = base64.b64decode(base64_content)
        logger.info(f"Decoded base64 to DOCX, size: {len(docx_content)} bytes")

        # Process DOCX in memory using BytesIO
        processed_docx_bytes = process_docx_in_memory(docx_content, data)
        logger.info(
            f"Processed DOCX with data, size: {len(processed_docx_bytes)} bytes"
        )

        # Convert to PDF using LibreOffice (works in Lambda with layer)
        logger.info("Starting LibreOffice PDF conversion...")
        pdf_content = convert_docx_to_pdf_with_libreoffice(processed_docx_bytes)
        logger.info(f"Successfully converted to PDF, size: {len(pdf_content)} bytes")

        return pdf_content

    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}", exc_info=True)
        raise Exception(f"Document processing failed: {str(e)}")


def convert_docx_to_pdf_with_libreoffice(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX to PDF using LibreOffice with minimal temp files.

    Args:
        docx_bytes: Processed DOCX content as bytes

    Returns:
        PDF content as bytes
    """
    logger.info(f"Starting DOCX to PDF conversion, input size: {len(docx_bytes)} bytes")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        file_id = str(uuid.uuid4())

        # Write processed DOCX to temp file (required for LibreOffice)
        temp_docx = temp_path / f"processed_{file_id}.docx"
        with open(temp_docx, "wb") as f:
            f.write(docx_bytes)
        logger.info(f"Wrote DOCX to temp file: {temp_docx}")

        # Convert to PDF
        output_pdf = temp_path / f"final_{file_id}.pdf"
        logger.info(f"Calling LibreOffice converter...")
        convert_docx_to_pdf(str(temp_docx), str(output_pdf))
        logger.info(f"LibreOffice conversion completed")

        # Read PDF content into memory
        with open(output_pdf, "rb") as pdf_file:
            pdf_content = pdf_file.read()
            logger.info(f"Read PDF from disk, size: {len(pdf_content)} bytes")
            return pdf_content


def get_libreoffice_path() -> str:
    """
    Get LibreOffice executable path (Lambda layer compatible).
    Handles extraction of brotli-compressed LibreOffice from Lambda layer.

    Returns:
        Path to LibreOffice executable
    """
    # Check for already extracted LibreOffice in /tmp (Lambda warm start)
    # The tar extracts to /tmp/instdir/ not /tmp/lo/instdir/
    common_paths = [
        "/tmp/instdir/program/soffice.bin",
        "/tmp/lo/instdir/program/soffice.bin",
        "/tmp/opt/libreoffice/program/soffice.bin",
    ]

    for extracted_path in common_paths:
        if os.path.exists(extracted_path):
            logger.info(f"Using previously extracted LibreOffice at: {extracted_path}")
            return extracted_path

    # Check if brotli-compressed LibreOffice layer exists
    brotli_archive = "/opt/lo.tar.br"
    if os.path.exists(brotli_archive):
        # Check if instdir already exists from previous extraction
        if os.path.exists("/tmp/instdir"):
            logger.info("LibreOffice already extracted to /tmp/instdir, reusing...")
            # Search for the binary
            for root, dirs, files in os.walk("/tmp/instdir"):
                if "soffice.bin" in files:
                    found_path = os.path.join(root, "soffice.bin")
                    logger.info(f"Found soffice.bin at: {found_path}")
                    return found_path
                if "soffice" in files:
                    found_path = os.path.join(root, "soffice")
                    logger.info(f"Found soffice at: {found_path}")
                    return found_path

        logger.info(f"Found brotli-compressed LibreOffice layer, extracting...")
        try:
            # Get archive size for logging
            archive_size = os.path.getsize(brotli_archive)
            logger.info(f"Brotli archive size: {archive_size / 1024 / 1024:.2f} MB")

            # Decompress brotli to tar (memory intensive - requires 2GB+ Lambda memory)
            logger.info(
                "Decompressing brotli archive (this requires significant memory)..."
            )
            with open(brotli_archive, "rb") as br_file:
                compressed_data = br_file.read()
                logger.info(
                    f"Read brotli archive: {len(compressed_data) / 1024 / 1024:.2f} MB"
                )

            decompressed_data = brotli.decompress(compressed_data)
            logger.info(
                f"Decompressed to tar: {len(decompressed_data) / 1024 / 1024:.2f} MB"
            )

            # Clear compressed data to free memory
            del compressed_data

            # Extract tar to /tmp
            logger.info("Extracting tar archive to /tmp...")
            tar_stream = BytesIO(decompressed_data)
            with tarfile.open(fileobj=tar_stream, mode="r") as tar:
                tar.extractall("/tmp")
                logger.info(f"Extracted LibreOffice to /tmp")

            # Clear decompressed data to free memory
            del decompressed_data
            del tar_stream

            # Search for the binary in the extracted location
            logger.info("Searching for LibreOffice binary in /tmp/instdir...")
            if os.path.exists("/tmp/instdir"):
                # Check common locations first
                common_binary_paths = [
                    "/tmp/instdir/program/soffice.bin",
                    "/tmp/instdir/program/soffice",
                ]

                for binary_path in common_binary_paths:
                    if os.path.exists(binary_path):
                        logger.info(f"Found LibreOffice binary at: {binary_path}")
                        return binary_path

                # If not in common locations, search recursively
                logger.info("Searching recursively in /tmp/instdir...")
                for root, dirs, files in os.walk("/tmp/instdir"):
                    if "soffice.bin" in files:
                        found_path = os.path.join(root, "soffice.bin")
                        logger.info(f"Found soffice.bin at: {found_path}")
                        return found_path
                    if "soffice" in files and "soffice.bin" not in files:
                        found_path = os.path.join(root, "soffice")
                        logger.info(f"Found soffice at: {found_path}")
                        return found_path

                logger.error("Could not find soffice.bin or soffice in /tmp/instdir")
            else:
                logger.error("Extraction completed but /tmp/instdir not found")
                logger.info(f"Contents of /tmp: {os.listdir('/tmp')}")
        except MemoryError as e:
            logger.error(
                f"Out of memory during LibreOffice extraction. "
                f"Lambda needs at least 2048MB memory for this layer. "
                f"Current archive size: {archive_size / 1024 / 1024:.2f} MB",
                exc_info=True,
            )
            raise Exception(
                "Lambda out of memory during LibreOffice extraction. "
                "Increase Lambda memory to at least 2048MB (2GB)"
            ) from e
        except Exception as e:
            logger.error(f"Failed to extract LibreOffice layer: {e}", exc_info=True)
            raise

    # Check for Lambda layer paths (pre-extracted layers)
    lambda_paths = [
        "/opt/bin/soffice",  # Pre-extracted layer
        "/opt/lo/bin/soffice",  # Alternative layer location
        "/opt/libreoffice/program/soffice.bin",  # Standard layer location
        "/opt/libreoffice7.6/program/soffice.bin",  # Versioned layer
    ]

    for lambda_path in lambda_paths:
        if os.path.exists(lambda_path):
            logger.info(f"Found LibreOffice Lambda layer at: {lambda_path}")
            return lambda_path

    # If no Lambda paths found, log what's in /opt
    if os.path.exists("/opt"):
        logger.info(
            f"Lambda layer paths checked but not found. Contents of /opt: {os.listdir('/opt')}"
        )

    # Fallback to system installation
    logger.info("Using system LibreOffice installation")
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


def setup_fontconfig_for_lambda():
    """Create minimal fontconfig configuration for Lambda environment."""
    fontconfig_dir = "/tmp/.config/fontconfig"
    fontconfig_file = os.path.join(fontconfig_dir, "fonts.conf")

    # Skip if already created
    if os.path.exists(fontconfig_file):
        return

    try:
        os.makedirs(fontconfig_dir, exist_ok=True)

        # Minimal fontconfig that won't complain
        fontconfig_content = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- Disable warnings -->
  <match target="pattern">
    <edit name="family" mode="append_last">
      <string>sans-serif</string>
    </edit>
  </match>
</fontconfig>
"""
        with open(fontconfig_file, "w") as f:
            f.write(fontconfig_content)

        logger.info(f"Created fontconfig at: {fontconfig_file}")
    except Exception as e:
        logger.warning(f"Could not create fontconfig: {e}")


def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    """Convert DOCX to PDF using LibreOffice (Lambda compatible)."""

    try:
        logger.info(f"Converting DOCX to PDF: {docx_path} -> {pdf_path}")

        # Get LibreOffice path (Lambda layer or system)
        libreoffice_cmd = get_libreoffice_path()
        logger.info(f"Using LibreOffice at: {libreoffice_cmd}")

        # Detect if running in AWS Lambda
        is_lambda = os.environ.get("AWS_EXECUTION_ENV") is not None or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        
        # Set up environment variables
        env = os.environ.copy()
        
        if is_lambda:
            logger.info("Running in AWS Lambda environment, applying Lambda-specific settings")
            # Set up fontconfig for Lambda (prevents fontconfig warnings)
            setup_fontconfig_for_lambda()
            
            # Lambda-specific environment variables
            env.update(
                {
                    "HOME": "/tmp",  # LibreOffice needs writable home directory
                    "SAL_USE_VCLPLUGIN": "svp",  # Use server VCL plugin (no X11)
                    "LANG": "C.UTF-8",  # Fix locale issues
                    "LC_ALL": "C.UTF-8",
                    "FONTCONFIG_PATH": "/tmp/.config/fontconfig",  # Use our custom fontconfig
                }
            )
        else:
            logger.info("Running in local environment, using default settings")

        # Check if LibreOffice is available
        logger.info("Checking LibreOffice version...")
        result = subprocess.run(
            [libreoffice_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=10,  # Increased for Lambda cold starts
            env=env,
        )

        if result.returncode != 0:
            logger.error(f"LibreOffice version check failed: {result.stderr}")
            raise FileNotFoundError(f"LibreOffice not found at {libreoffice_cmd}")

        logger.info(f"LibreOffice version: {result.stdout.strip()}")

        # Convert using LibreOffice with Lambda-optimized arguments
        output_dir = Path(pdf_path).parent
        logger.info(f"Starting LibreOffice conversion subprocess...")
        result = subprocess.run(
            [
                libreoffice_cmd,
                "--headless",
                "--invisible",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                "--nologo",
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
            env=env,
        )

        logger.info(
            f"LibreOffice subprocess completed with exit code: {result.returncode}"
        )
        if result.stdout:
            logger.info(f"LibreOffice stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"LibreOffice stderr: {result.stderr}")

        if result.returncode != 0:
            logger.error(
                f"LibreOffice conversion failed with exit code: {result.returncode}"
            )
            raise subprocess.CalledProcessError(result.returncode, "libreoffice")

        # LibreOffice creates PDF with same base name
        generated_pdf = output_dir / (Path(docx_path).stem + ".pdf")
        logger.info(f"Checking for generated PDF at: {generated_pdf}")

        # Check if LibreOffice actually created the PDF
        if not generated_pdf.exists():
            logger.error(
                f"LibreOffice failed to create PDF at expected location: {generated_pdf}"
            )
            raise FileNotFoundError(
                f"LibreOffice failed to create PDF: {generated_pdf}"
            )

        # Rename if necessary
        if str(generated_pdf) != pdf_path:
            logger.info(f"Renaming PDF: {generated_pdf} -> {pdf_path}")
            generated_pdf.rename(pdf_path)

        # Final verification
        if not Path(pdf_path).exists():
            logger.error(f"Final PDF not found at: {pdf_path}")
            raise FileNotFoundError(f"Final PDF not found at: {pdf_path}")

        pdf_size = Path(pdf_path).stat().st_size
        logger.info(f"PDF conversion successful, file size: {pdf_size} bytes")

    except FileNotFoundError as e:
        logger.error(f"FileNotFoundError: {str(e)}")
        raise Exception(
            "LibreOffice not found! "
            "For Lambda: Add LibreOffice layer. "
            "For local: Install with 'sudo apt install libreoffice --no-install-recommends'"
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"LibreOffice subprocess failed: {str(e)}")
        raise Exception(f"LibreOffice conversion failed: {e}")
    except subprocess.TimeoutExpired as e:
        logger.error(f"LibreOffice subprocess timed out after {e.timeout} seconds")
        raise Exception("LibreOffice conversion timed out")
