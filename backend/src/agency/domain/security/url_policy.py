"""URL security policy and SSRF defense validator.

Provides strict validation of client-provided links and outbound fetch targets,
blocking loopback, RFC 1918 private ranges, cloud metadata endpoints,
link-local addresses, and unsupported protocols.
"""

import ipaddress
import socket
from urllib.parse import urlparse

# Restricted domain names and suffixes
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_SUFFIXES = (
    ".local",
    ".internal",
    ".localhost",
    ".arpa",
    ".localdomain",
)

ALLOWED_SCHEMES = {"http", "https"}


class SSRFSecurityError(ValueError):
    """Raised when a URL violates SSRF safety constraints."""


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if IP is private, loopback, link-local, multicast, or reserved."""
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_safe_url(url: str, resolve_dns: bool = False) -> str:
    """Validate that a URL does not target internal, private, or metadata services.

    Args:
        url: Full URL string.
        resolve_dns: If True, resolves hostname and validates resolved IP addresses.

    Returns:
        str: Validated URL string.

    Raises:
        SSRFSecurityError: If URL points to internal, private, or prohibited targets.
    """
    if not url or not isinstance(url, str):
        raise SSRFSecurityError("URL must be a non-empty string.")

    cleaned_url = url.strip()
    try:
        parsed = urlparse(cleaned_url)
    except Exception as exc:
        raise SSRFSecurityError(f"Malformed URL: {exc}") from exc

    # 1. Scheme validation
    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFSecurityError(
            f"Disallowed URL scheme '{parsed.scheme}'. Only http and https allowed."
        )

    # 2. Hostname validation
    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError("URL must include a valid hostname.")

    hostname_lower = hostname.lower()

    # Disallow userinfo (e.g. http://user:pass@evil.com)
    if parsed.username or parsed.password:
        raise SSRFSecurityError("URLs containing user authentication are prohibited.")

    # Blocked known domains / suffixes
    if hostname_lower in BLOCKED_HOSTNAMES:
        raise SSRFSecurityError(
            f"Access to internal hostname '{hostname}' is blocked (SSRF guard)."
        )

    if any(hostname_lower.endswith(suffix) for suffix in BLOCKED_SUFFIXES):
        raise SSRFSecurityError(
            f"Access to internal domain suffix in '{hostname}' is blocked."
        )

    # 3. IP address evaluation (IPv4 and IPv6)
    # Strip brackets if IPv6 literal (e.g. [::1])
    ip_candidate = hostname_lower.strip("[]")
    ip = None
    try:
        ip = ipaddress.ip_address(ip_candidate)
    except ValueError:
        pass

    if ip is not None and is_ip_blocked(ip):
        raise SSRFSecurityError(
            f"Access to private or non-routable IP '{ip}' is blocked (SSRF guard)."
        )

    # 4. Optional DNS resolution check (rebinding protection)
    if resolve_dns:
        try:
            # Resolve all A / AAAA records
            addr_info = socket.getaddrinfo(
                hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
            )
            for item in addr_info:
                sockaddr = item[4]
                resolved_ip_str = sockaddr[0]
                resolved_ip = ipaddress.ip_address(resolved_ip_str)
                if is_ip_blocked(resolved_ip):
                    raise SSRFSecurityError(
                        f"Hostname '{hostname}' resolves to blocked IP '{resolved_ip}'."
                    )
        except socket.gaierror as exc:
            raise SSRFSecurityError(
                f"Failed to resolve hostname '{hostname}': {exc}"
            ) from exc

    return cleaned_url
