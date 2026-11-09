# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes: security fixes are released as 1.x patch versions |
| 0.1.x | No: upgrade to 1.x |

Fixes are made on the latest 1.x release. Unreleased development code receives
fixes before release.

## Reporting a vulnerability

Please do not report security vulnerabilities in public issues.

Report them privately through
[GitHub security advisories](https://github.com/smuniharish/xstructured/security/advisories/new),
or by email to samamuniharish@gmail.com. Include a clear description, the
affected versions, reproduction steps, the potential impact, and any suggested
mitigation. Do not include credentials or sensitive production data.

You will receive an acknowledgement within five working days. Once a fix is
available, it is released and the advisory is published with credit to the
reporter, unless you prefer to remain anonymous. Please do not publish details
until a fix or mitigation is available.

## Handling model output

xstructured treats every model response as untrusted input. It bounds input,
envelope, payload, and nesting sizes, rejects duplicate keys, `NaN`,
`Infinity`, and overflowing numbers, and never puts model output in exception
messages. Deployers are responsible for:

- keeping the default limits, or lowering them, for the inputs they accept;
- logging `ParseError` messages rather than `ParseError.text` when output may
  hold personal data;
- treating a validated value as data, never as code or a command;
- keeping API keys out of source control and out of telemetry attributes.

For guidance on using xstructured safely, see the
[security documentation](https://xstructured.readthedocs.io/en/latest/security/).
