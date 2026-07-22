"""
Prompt 模板加载工具

按名称从项目根目录的 prompts 目录读取 .prompt 文件
业务节点只需要传入逻辑名称，不需要关心提示词文件的具体路径
"""

from app.prompt.registry import get_prompt_definition, load_template


def load_prompt(name: str) -> str:
    """兼容旧调用方式；新代码应使用 Prompt 工厂。"""

    definition = get_prompt_definition(name)
    return load_template(definition.user_template)
