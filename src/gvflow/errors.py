from __future__ import annotations


class GvflowError(RuntimeError):
    def __init__(self, code: str, message: str = "", *, detail: object = None):
        super().__init__(message or code)
        self.code = code
        self.detail = detail

    def as_dict(self) -> dict:
        return {"ok": False, "error_code": self.code, "message": str(self), "detail": self.detail}


class ConfigError(GvflowError):
    pass


class ProviderError(GvflowError):
    pass


class ContractError(GvflowError):
    pass
