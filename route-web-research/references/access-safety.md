# Access Safety

This skill can operate powerful fetchers and browsers. Its failure mode is not just technical; it can produce legal, account, or data-governance problems.

## Hard Stops

Stop or ask before:

- Logging in with user credentials.
- Solving, bypassing, or outsourcing CAPTCHA.
- Bypassing paywalls, explicit access denials, IP bans, or account limits.
- Ignoring robots.txt or clear ToS restrictions for broad crawling.
- Collecting private personal data, direct contact/payment identifiers, or sensitive account data.
- Using stealth/fingerprint tools against a site whose access policy is explicit.
- Running high-volume crawls without a rate, scope, and persistence plan.

## Allowed Uses

- Public pages where normal browser access is allowed.
- Diagnosing a public fetch failure and recording exact HTTP/TLS/browser behavior.
- Using `curl_cffi` or WSL `curl_chrome*` to reproduce browser TLS fingerprints for public resources.
- Browser automation for inspection, screenshots, or user-approved session workflows.
- Respectful crawling with rate limits, user-agent strategy, robots posture, retries, and dedupe.

## Evidence Discipline

- Record access status and tool path for every source.
- Preserve failure messages. They are evidence about route choice.
- Mark access-limited sources as `access_restricted`, not as missing or disproven.
- Treat extracted Markdown as a representation. For high-stakes claims, compare with the rendered page, original PDF, or source file.
