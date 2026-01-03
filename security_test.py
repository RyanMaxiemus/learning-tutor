#!/usr/bin/env python3
"""
Security validation script for AI Learning Tutor.
Tests the security fixes that have been implemented.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.security import (
    validate_file_content, sanitize_input, generate_secure_filename,
    validate_file_size, SecurityConfig
)

def test_file_validation():
    """Test file content validation"""
    print("Testing file validation...")

    # Test PDF validation
    pdf_content = b'%PDF-1.4\n%some pdf content'
    assert validate_file_content(pdf_content, '.pdf') == True
    print("✓ PDF validation works")

    # Test fake PDF
    fake_pdf = b'<script>alert("xss")</script>'
    assert validate_file_content(fake_pdf, '.pdf') == False
    print("✓ Fake PDF rejected")

    # Test DOCX validation
    docx_content = b'PK\x03\x04\x14\x00\x06\x00'  # ZIP signature
    assert validate_file_content(docx_content, '.docx') == True
    print("✓ DOCX validation works")

    # Test text validation
    text_content = b'This is valid UTF-8 text'
    assert validate_file_content(text_content, '.txt') == True
    print("✓ Text validation works")

    # Test invalid text
    invalid_text = b'\xff\xfe\x00\x00'  # Invalid UTF-8
    assert validate_file_content(invalid_text, '.txt') == False
    print("✓ Invalid text rejected")

def test_input_sanitization():
    """Test input sanitization"""
    print("\nTesting input sanitization...")

    # Test normal input
    clean_input = "Python Programming"
    assert sanitize_input(clean_input) == "Python Programming"
    print("✓ Clean input preserved")

    # Test dangerous characters
    dangerous_input = "Python<script>alert('xss')</script>"
    sanitized = sanitize_input(dangerous_input)
    assert '<' not in sanitized and '>' not in sanitized
    print("✓ Dangerous characters removed")

    # Test length limiting
    long_input = "A" * 1000
    sanitized = sanitize_input(long_input, max_length=100)
    assert len(sanitized) <= 100
    print("✓ Length limiting works")

    # Test SQL injection attempt
    sql_injection = "'; DROP TABLE users; --"
    sanitized = sanitize_input(sql_injection)
    assert "'" not in sanitized and ';' not in sanitized
    print("✓ SQL injection characters removed")

def test_filename_generation():
    """Test secure filename generation"""
    print("\nTesting filename generation...")

    # Test normal filename
    filename = generate_secure_filename("document.pdf")
    assert filename.endswith('.pdf')
    assert len(filename) > 10  # UUID makes it longer
    print("✓ Secure filename generated")

    # Test path traversal attempt
    malicious_filename = "../../etc/passwd"
    secure_filename = generate_secure_filename(malicious_filename)
    assert '../' not in secure_filename
    assert secure_filename != malicious_filename
    print("✓ Path traversal prevented")

    # Test with no extension
    no_ext = generate_secure_filename("document")
    assert len(no_ext) > 10  # Should still generate UUID
    print("✓ No extension handled")

def test_file_size_validation():
    """Test file size validation"""
    print("\nTesting file size validation...")

    # Test normal size
    assert validate_file_size(1024 * 1024) == True  # 1MB
    print("✓ Normal file size accepted")

    # Test oversized file
    assert validate_file_size(200 * 1024 * 1024) == False  # 200MB
    print("✓ Oversized file rejected")

    # Test custom limit
    assert validate_file_size(5 * 1024 * 1024, max_size_mb=1) == False  # 5MB with 1MB limit
    print("✓ Custom size limit works")

def test_security_config():
    """Test security configuration values"""
    print("\nTesting security configuration...")

    # Test that limits are reasonable
    assert SecurityConfig.MAX_FILE_SIZE_MB > 0
    assert SecurityConfig.MAX_FILE_SIZE_MB <= 1000  # Not too large
    print("✓ File size limits reasonable")

    assert SecurityConfig.MAX_LLM_CALLS_PER_MINUTE > 0
    assert SecurityConfig.MAX_LLM_CALLS_PER_MINUTE <= 1000  # Not too high
    print("✓ Rate limits reasonable")

    assert len(SecurityConfig.ALLOWED_FILE_TYPES) > 0
    assert '.pdf' in SecurityConfig.ALLOWED_FILE_TYPES
    print("✓ File types configured")

def main():
    """Run all security tests"""
    print("🔒 Running Security Validation Tests")
    print("=" * 50)

    try:
        test_file_validation()
        test_input_sanitization()
        test_filename_generation()
        test_file_size_validation()
        test_security_config()

        print("\n" + "=" * 50)
        print("🎉 All security tests passed!")
        print("✅ File upload security: PROTECTED")
        print("✅ Input validation: PROTECTED")
        print("✅ Path traversal: PROTECTED")
        print("✅ File size limits: ENFORCED")
        print("✅ Rate limiting: CONFIGURED")

        return True

    except Exception as e:
        print(f"\n❌ Security test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
