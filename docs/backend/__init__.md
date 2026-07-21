# `backend/app/__init__.py`

Package marker — empty. Exists solely so `from app.X import Y` resolves as
a package import (the dockerfile and uvicorn entry point both use
`app.main:app`).

The file intentionally contains no code: adding side-effect imports here
would surprise `uvicorn` workers and complicate test isolation. Keep it
empty.

---

*created by [@dhir0hit](https://github.com/dhir0hit) using [Hermes Agent](https://hermes-agent.nousresearch.com)*
