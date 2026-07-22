"""根据注册表构建统一的 ChatPrompt 和 LCEL 调用链。"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.llm.factory import get_chat_model
from app.prompt.output_parsers import get_output_parser
from app.prompt.registry import get_prompt_definition, load_template


def build_chat_prompt(name: str) -> ChatPromptTemplate:
    definition = get_prompt_definition(name)
    return ChatPromptTemplate.from_messages(
        [
            ("system", load_template(definition.system_template)),
            ("human", load_template(definition.user_template)),
        ]
    )


def build_prompt_chain(name: str, *, model: BaseChatModel | None = None) -> Runnable:
    definition = get_prompt_definition(name)
    selected_model = model or get_chat_model(definition.model_profile)
    return (
        build_chat_prompt(name)
        | selected_model
        | get_output_parser(definition.output_type)
    )
