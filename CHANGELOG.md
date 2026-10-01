# CHANGELOG

<!-- version list -->

## v2.0.0 (2026-10-01)

### Bug Fixes

- **security**: Drop Python 3.9 support to resolve Dependabot alerts
  ([#11](https://github.com/lv10/amazonapi/pull/11),
  [`6062b38`](https://github.com/lv10/amazonapi/commit/6062b3897f65a3ad4fd91626b7942ee951899811))

### Chores

- Update uv.lock with latest dependency versions ([#10](https://github.com/lv10/amazonapi/pull/10),
  [`d925670`](https://github.com/lv10/amazonapi/commit/d925670fbd81bb91892df8cafd1b78da44b25d38))

### Documentation

- Add Buy Me a Coffee donation and sponsor links ([#9](https://github.com/lv10/amazonapi/pull/9),
  [`c30a4c5`](https://github.com/lv10/amazonapi/commit/c30a4c5fb5e5824e0e2e79aaf00cb151bafe9ed6))

### Breaking Changes

- **security**: Python 3.9 is no longer supported. Projects that need to stay on Python 3.9 should
  pin to AmazonAPIWrapper==1.0.1, the last release that supported it.


## v1.0.1 (2026-08-24)

### Bug Fixes

- **security**: Harden credential handling, concurrency, validation, and retry backoff
  ([`7eb826c`](https://github.com/lv10/amazonapi/commit/7eb826cb1c9991901786b27abefcbc22852c098d))


## v1.0.0 (2026-08-23)

- Initial Release

## 1.0.0 (2026-08-23)

### Features

- Modernize to v1.0.0 (Amazon Creators API, PA-API 5.0, UV, Async/Sync, Pytest)
