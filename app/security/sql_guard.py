"""Agent 生成 SQL 在进入数据库前必须通过的保守安全策略。"""

import re
from dataclasses import dataclass


class SQLSafetyError(ValueError):
    """SQL 违反只读查询安全策略。"""


def _mask_quoted_content(sql: str) -> str:
    """屏蔽字符串和引用标识符内容，只保留待审计的 SQL 结构。"""

    masked = list(sql)
    index = 0
    while index < len(sql):
        quote = sql[index]
        if quote not in {"'", '"', "`"}:
            index += 1
            continue

        index += 1
        while index < len(sql):
            char = sql[index]
            masked[index] = " "
            if char == "\\" and index + 1 < len(sql):
                index += 1
                masked[index] = " "
            elif char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    index += 1
                    masked[index] = " "
                else:
                    break
            index += 1
        else:
            raise SQLSafetyError("SQL 包含未闭合的引用内容")
        index += 1
    return "".join(masked)


@dataclass(frozen=True)
class SQLGuard:
    """执行边界使用的单语句只读 SQL 守卫。"""

    max_sql_length: int

    _blocked_operations = re.compile(
        r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
        r"REPLACE|MERGE|CALL|EXECUTE|PREPARE|HANDLER|LOAD)\b",
        re.IGNORECASE,
    )
    _blocked_functions = re.compile(
        r"\b(SLEEP|BENCHMARK|GET_LOCK|RELEASE_LOCK|LOAD_FILE)\s*\(",
        re.IGNORECASE,
    )
    _blocked_clauses = re.compile(
        r"\bINTO\s+(OUTFILE|DUMPFILE)\b|\bFOR\s+UPDATE\b|"
        r"\bLOCK\s+IN\s+SHARE\s+MODE\b",
        re.IGNORECASE,
    )
    _system_schemas = re.compile(
        r"\b(INFORMATION_SCHEMA|PERFORMANCE_SCHEMA|MYSQL|SYS)\s*\.",
        re.IGNORECASE,
    )

    def validate(self, raw_sql: str) -> str:
        """规范化并验证 SQL，返回可交给数据库的只读单语句。"""

        sql = raw_sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1].rstrip()
        if not sql:
            raise SQLSafetyError("SQL 不能为空")
        if len(sql) > self.max_sql_length:
            raise SQLSafetyError(
                f"SQL 长度超过限制：{len(sql)} > {self.max_sql_length}"
            )

        structural_sql = _mask_quoted_content(sql)
        if re.search(r"(--|#|/\*)", structural_sql):
            raise SQLSafetyError("SQL 不允许包含注释")
        if ";" in structural_sql:
            raise SQLSafetyError("只允许执行一条 SQL")
        if not re.match(r"^\s*(SELECT|WITH)\b", structural_sql, re.IGNORECASE):
            raise SQLSafetyError("SQL 必须以 SELECT 或 WITH 开头")
        if self._blocked_operations.search(structural_sql):
            raise SQLSafetyError("SQL 包含写入、DDL 或动态执行操作")
        if self._blocked_functions.search(structural_sql):
            raise SQLSafetyError("SQL 包含禁止的高风险函数")
        if self._blocked_clauses.search(structural_sql):
            raise SQLSafetyError("SQL 包含文件写入或锁定操作")
        if self._system_schemas.search(structural_sql):
            raise SQLSafetyError("SQL 不允许访问系统 Schema")
        return sql
