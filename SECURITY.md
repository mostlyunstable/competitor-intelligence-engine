# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

To report a security issue, please email the maintainers directly or use GitHub's private vulnerability reporting feature.

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Any suggested mitigations

You can expect an acknowledgment within 48 hours and a resolution timeline within 7 business days for critical issues.

## Security Best Practices for Deployment

- **Never commit `.env` files** — use environment variables or a secrets manager
- **Rotate API keys** after any accidental exposure
- **Use strong database passwords** — change all defaults before production deployment
- **Enable HTTPS** — never run the API over plain HTTP in production
- **Restrict API access** — keep the `X-API-Key` secret and rotate regularly
- **Limit crawl rate** — respect `robots.txt` and configure `RATE_LIMIT_PER_SECOND` appropriately

## Dependency Security

Dependencies are pinned with upper bounds in `pyproject.toml`. Run `pip audit` regularly to check for known vulnerabilities in the dependency chain.
