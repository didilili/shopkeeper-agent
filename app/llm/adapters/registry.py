"""受控发现和注册本地协议适配器。"""

from importlib import import_module
from pkgutil import iter_modules

from app.llm.adapters.base import ChatModelAdapter
from app.llm.errors import AdapterNotFoundError, LLMConfigurationError

_ADAPTERS: dict[str, ChatModelAdapter] = {}
_DISCOVERED = False


def register_adapter(
    adapter_type: type[ChatModelAdapter],
) -> type[ChatModelAdapter]:
    adapter = adapter_type()
    if not adapter.name:
        raise LLMConfigurationError("适配器名称不能为空")
    if adapter.name in _ADAPTERS:
        raise LLMConfigurationError(f"重复注册适配器：{adapter.name}")
    _ADAPTERS[adapter.name] = adapter
    return adapter_type


def discover_adapters() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return

    package = import_module("app.llm.adapters")
    for module in iter_modules(package.__path__):
        if module.name not in {"base", "registry"}:
            import_module(f"{package.__name__}.{module.name}")
    _DISCOVERED = True


def get_adapter(name: str) -> ChatModelAdapter:
    discover_adapters()
    adapter = _ADAPTERS.get(name)
    if adapter is None:
        available = ", ".join(sorted(_ADAPTERS))
        raise AdapterNotFoundError(f"未注册适配器 {name!r}；可选适配器：{available}")
    return adapter
