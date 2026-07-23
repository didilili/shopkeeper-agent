"""SQL 修正节点的重试计数测试。"""

import asyncio

import app.agent.nodes.correct_sql as correct_sql_module


class FakeChain:
    async def ainvoke(self, values):
        return "SELECT 1"


class FakeRuntime:
    def __init__(self):
        self.events: list[dict] = []
        self.stream_writer = self.events.append


def test_correct_sql_increments_attempt_counter(monkeypatch) -> None:
    monkeypatch.setattr(
        correct_sql_module, "build_prompt_chain", lambda name: FakeChain()
    )
    state = {
        "table_infos": [],
        "metric_infos": [],
        "date_info": {},
        "db_info": {},
        "query": "查询订单数",
        "sql": "SELECT missing_column",
        "error": "unknown column",
        "correction_attempts": 1,
    }
    runtime = FakeRuntime()

    result = asyncio.run(correct_sql_module.correct_sql(state, runtime))

    assert result == {"sql": "SELECT 1", "correction_attempts": 2}
    assert runtime.events[-1]["status"] == "success"
