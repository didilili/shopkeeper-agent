"""测试进程统一使用隔离配置。"""

import os

os.environ.setdefault("APP_ENV", "test")
