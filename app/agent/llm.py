"""兼容现有 Agent 节点的默认模型入口。"""

from app.llm.factory import get_chat_model

# 节点继续导入这个单例；具体模型由 conf/models.yaml 的 sql_agent 角色决定。
llm = get_chat_model("sql_agent")


if __name__ == "__main__":
    print(llm.invoke("你好").content)
