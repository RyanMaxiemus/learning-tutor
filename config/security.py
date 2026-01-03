"""
Security configuration and utilities for the AI Learning Tutor application.
Centralizes security settings and provides security-related functions.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration settings"""

    # File upload limits
    MAX_FILE_SIZE_MB = 100
    MAX_TEXT_SIZE_MB = 10
    MAX_CHUNKS_PER_DOCUMENT = 1000

    # Rate limiting
    MAX_LLM_CALLS_PER_MINUTE = 30
    MAX_PROMPT_LENGTH = 5000

    # Input validation
    MAX_SUBJECT_LENGTH = 100
    MAX_TOPIC_LENGTH = 100
    MAX_USERNAME_LENGTH = 50

    # Allowed file types and their magic bytes
    ALLOWED_FILE_TYPES = {
        '.pdf': [b'%PDF'],
        '.docx': [b'PK'],  # ZIP signature for DOCX
        '.doc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE signature
        '.txt': []  # Text files validated by UTF-8 decoding
    }

    # Dangerous characters to remove from user input
    DANGEROUS_CHARS_PATTERN = r'[<>"\';\\]'

def validate_file_content(file_content: bytes, file_extension: str) -> bool:
    """
    Validate file content by checking magic bytes/signatures.
    This prevents malicious files with fake extensions.

    Args:
        file_content: Raw file bytes
        file_extension: File extension (e.g., '.pdf')

    Returns:
        True if file is valid, False otherwise
    """
    if file_extension not in SecurityConfig.ALLOWED_FILE_TYPES:
        logger.warning(f"Unsupported file extension: {file_extension}")
        return False

    magic_bytes = SecurityConfig.ALLOWED_FILE_TYPES[file_extension]

    # Special handling for text files
    if file_extension == '.txt':
        try:
            file_content.decode('utf-8')
            return True
        except UnicodeDecodeError:
            logger.warning("Invalid UTF-8 content in text file")
            return False

    # Check magic bytes for binary files
    for magic in magic_bytes:
        if file_content.startswith(magic):
            return True

    logger.warning(f"Invalid magic bytes for {file_extension}")
    return False

def sanitize_input(text: str, max_length: int = 200) -> str:
    """
    Sanitize user input to prevent injection attacks and ensure data integrity.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove potentially dangerous characters
    text = re.sub(SecurityConfig.DANGEROUS_CHARS_PATTERN, '', text)

    # Limit length
    text = text[:max_length]

    # Strip whitespace
    text = text.strip()

    return text

def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure filename to prevent path traversal and conflicts.

    Args:
        original_filename: Original filename from user

    Returns:
        Secure filename with random component
    """
    import uuid

    # Extract safe filename and extension
    safe_filename = os.path.basename(original_filename)
    file_extension = Path(safe_filename).suffix.lower()

    # Generate random filename
    random_filename = f"{uuid.uuid4()}{file_extension}"

    return random_filename

def secure_file_deletion(file_path: Path) -> bool:
    """
    Securely delete a file by overwriting it before deletion.

    Args:
        file_path: Path to file to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        if not file_path.exists():
            return True

        # Overwrite file with zeros
        with open(file_path, 'r+b') as f:
            length = f.seek(0, 2)  # Get file size
            f.seek(0)
            f.write(b'\x00' * length)  # Overwrite with zeros
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Now delete the file
        file_path.unlink()

        logger.info(f"Securely deleted file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error securely deleting file {file_path}: {e}")
        return False

def validate_file_size(file_size: int, max_size_mb: int = None) -> bool:
    """
    Validate file size against limits.

    Args:
        file_size: Size in bytes
        max_size_mb: Maximum size in MB (defaults to config value)

    Returns:
        True if within limits, False otherwise
    """
    if max_size_mb is None:
        max_size_mb = SecurityConfig.MAX_FILE_SIZE_MB

    max_size_bytes = max_size_mb * 1024 * 1024

    if file_size > max_size_bytes:
        logger.warning(f"File too large: {file_size} bytes (max: {max_size_bytes})")
        return False

    return True

def hash_file(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file for duplicate detection.

    Args:
        file_path: Path to file

    Returns:
        Hex string of file hash
    """
    sha256_hash = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {e}")
        return ""

def log_security_event(event_type: str, details: Dict, user_id: str = "unknown"):
    """
    Log security-related events for monitoring and forensics.

    Args:
        event_type: Type of security event
        details: Event details
        user_id: User identifier
    """
    logger.warning(f"SECURITY EVENT [{event_type}] User: {user_id} Details: {details}")

# Security event types
class SecurityEvents:
    FILE_UPLOAD = "FILE_UPLOAD"
    FILE_VALIDATION_FAILED = "FILE_VALIDATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_INPUT = "INVALID_INPUT"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
