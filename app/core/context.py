from contextvars import ContextVar

request_id_ctx_var = ContextVar("request_id", default="1")
