"""本地环境变量加载入口。"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parents[2]


@lru_cache(maxsize=1)
def load_local_environment() -> None:
    """加载被 Git 忽略的本地 .env，不覆盖系统环境变量。"""

    load_dotenv(PROJECT_ROOT / ".env", override=False)
