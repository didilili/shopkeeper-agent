"""
请求上下文模块

用于保存和传递一次请求或一次脚本执行过程中的上下文变量，
当前先维护 request_id，后续日志模块会从这里读取 request_id 并注入到每条日志中
"""

from contextvars import ContextVar

# 使用 ContextVar 而不是普通全局变量
# 是为了让并发协程之间的 request_id 互不干扰
request_id_ctx_var = ContextVar("request_id", default="1")
