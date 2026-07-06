"""
File Validators
Validates uploaded files for type, extension, and size.
"""

import os


def allowed_file(filename, allowed_extensions):
    """Check if a filename has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


def get_file_extension(filename):
    """Extract the file extension (lowercase, without dot)."""
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def validate_upload(file, allowed_extensions, max_size_bytes):
    """
    Validate an uploaded file.

    Args:
        file: The uploaded file object from Flask request.
        allowed_extensions: Set of allowed file extensions.
        max_size_bytes: Maximum file size in bytes.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not file or file.filename == "":
        return False, "No file selected"

    if not allowed_file(file.filename, allowed_extensions):
        ext = get_file_extension(file.filename)
        return False, (
            f"File type '.{ext}' is not allowed. "
            f"Allowed types: {', '.join(sorted(allowed_extensions))}"
        )

    # Check file size by reading to memory (Flask doesn't expose size directly)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset for later reading

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, (
            f"File too large ({actual_mb:.1f} MB). "
            f"Maximum allowed size is {max_mb:.0f} MB."
        )

    if file_size == 0:
        return False, "File is empty"

    return True, None
