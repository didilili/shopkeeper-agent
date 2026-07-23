"""Meta MySQL 全量同步契约测试。"""

import asyncio

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository


class FakeSession:
    def __init__(self) -> None:
        self.executed = []
        self.added_batches = []

    async def execute(self, statement):
        self.executed.append(statement)

    def add_all(self, models) -> None:
        self.added_batches.append(models)


def test_replace_table_metadata_deletes_old_rows_before_inserting() -> None:
    session = FakeSession()
    repository = MetaMySQLRepository(session)
    tables = [TableInfo("fact_order", "fact_order", "fact", "订单事实表")]
    columns = [
        ColumnInfo(
            "fact_order.amount",
            "amount",
            "float",
            "measure",
            [10.0],
            "订单金额",
            ["销售额"],
            "fact_order",
        )
    ]

    asyncio.run(repository.replace_table_metadata(tables, columns))

    assert [statement.table.name for statement in session.executed] == [
        "column_info",
        "table_info",
    ]
    assert [[model.id for model in batch] for batch in session.added_batches] == [
        ["fact_order"],
        ["fact_order.amount"],
    ]


def test_replace_metric_metadata_deletes_old_rows_before_inserting() -> None:
    session = FakeSession()
    repository = MetaMySQLRepository(session)
    metrics = [
        MetricInfo(
            "GMV",
            "GMV",
            "成交总额",
            ["fact_order.amount"],
            ["销售额"],
        )
    ]
    relations = [ColumnMetric("fact_order.amount", "GMV")]

    asyncio.run(repository.replace_metric_metadata(metrics, relations))

    assert [statement.table.name for statement in session.executed] == [
        "column_metric",
        "metric_info",
    ]
    assert [
        [
            (
                getattr(model, "column_id", None),
                getattr(model, "metric_id", None),
            )
            for model in batch
        ]
        for batch in session.added_batches
    ] == [[(None, None)], [("fact_order.amount", "GMV")]]
