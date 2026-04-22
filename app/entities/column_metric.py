from dataclasses import dataclass


@dataclass
class ColumnMetric:
    column_id: str
    metric_id: str
