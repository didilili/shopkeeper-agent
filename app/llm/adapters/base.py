"""协议适配器接口。"""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.schemas import ResolvedModel


class ChatModelAdapter(ABC):
    name: str

    @abstractmethod
    def build(self, config: ResolvedModel) -> BaseChatModel:
        raise NotImplementedError
