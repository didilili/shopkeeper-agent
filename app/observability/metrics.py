"""低基数 Prometheus 指标定义。"""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

HTTP_REQUESTS = Counter(
    "shopkeeper_http_requests_total",
    "HTTP requests grouped by stable route and status class.",
    ("method", "route", "status_class"),
)
HTTP_DURATION = Histogram(
    "shopkeeper_http_response_duration_seconds",
    "Time until the HTTP response object is created.",
    ("method", "route"),
)
QUERY_STREAMS = Counter(
    "shopkeeper_query_streams_total",
    "Completed SSE query streams.",
    ("outcome", "error_category"),
)
QUERY_STREAM_DURATION = Histogram(
    "shopkeeper_query_stream_duration_seconds",
    "Full SSE query stream lifetime.",
    ("outcome",),
)
AGENT_NODES = Counter(
    "shopkeeper_agent_nodes_total",
    "Agent node executions.",
    ("node", "outcome", "error_category"),
)
AGENT_NODE_DURATION = Histogram(
    "shopkeeper_agent_node_duration_seconds",
    "Agent node execution duration.",
    ("node", "outcome"),
)
EXTERNAL_OPERATIONS = Counter(
    "shopkeeper_external_operations_total",
    "External dependency operations.",
    ("service", "operation", "outcome", "error_category"),
)
EXTERNAL_OPERATION_DURATION = Histogram(
    "shopkeeper_external_operation_duration_seconds",
    "External dependency operation duration.",
    ("service", "operation", "outcome"),
)
DEPENDENCY_UP = Gauge(
    "shopkeeper_dependency_up",
    "Whether the latest dependency probe succeeded.",
    ("dependency",),
)
ACCESS_REJECTIONS = Counter(
    "shopkeeper_access_rejections_total",
    "Rejected API access attempts.",
    ("reason",),
)
SQL_RESULT_ROWS = Histogram(
    "shopkeeper_sql_result_rows",
    "Rows returned by accepted SQL queries.",
)
SQL_CORRECTIONS = Counter(
    "shopkeeper_sql_corrections_total",
    "SQL correction outcomes.",
    ("outcome",),
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
