"""
Elasticsearch 客户端管理器

统一创建和管理 Elasticsearch 异步客户端，
主要服务于字段真实取值的全文索引构建和检索
"""

import asyncio
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    """管理 Elasticsearch 客户端的生命周期"""

    def __init__(self, es_config: ESConfig):
        # 保存 ES 配置对象，后面初始化客户端时会从这里读取 host 和 port
        self.es_config = es_config
        # 先把 client 声明出来，真正初始化放到 init() 中进行
        self.client: Optional[AsyncElasticsearch] = None

    def _get_url(self) -> str:
        """拼接 Elasticsearch 服务地址"""
        return f"{self.es_config.scheme}://{self.es_config.host}:{self.es_config.port}"

    def init(self):
        """
        初始化异步 Elasticsearch 客户端
        hosts 之所以是列表，是为了兼容 ES 常见的集群连接方式
        """
        basic_auth = None
        if self.es_config.username:
            basic_auth = (
                self.es_config.username,
                self.es_config.password.get_secret_value(),
            )
        self.client = AsyncElasticsearch(
            hosts=[self._get_url()],
            basic_auth=basic_auth,
            request_timeout=self.es_config.request_timeout,
        )

    async def close(self):
        """关闭客户端连接"""
        await self.client.close()


# 创建一个全局可复用的 ES 客户端管理器对象
es_client_manager = ESClientManager(app_config.es)

if __name__ == "__main__":
    es_client_manager.init()

    async def test():
        """执行一次索引创建、写入与查询，验证 ES 接入链路"""
        client = es_client_manager.client

        try:
            # 创建索引（已存在则跳过，避免重复执行脚本时报 resource_already_exists）
            # 这里同时显式定义了字段结构
            # dynamic=False 表示关闭动态映射，要求写入数据必须符合当前定义
            if not await client.indices.exists(index="my-books"):
                await client.indices.create(
                    index="my-books",
                    mappings={
                        "dynamic": False,
                        "properties": {
                            "name": {"type": "text"},
                            "author": {"type": "text"},
                            "release_date": {"type": "date", "format": "yyyy-MM-dd"},
                            "page_count": {"type": "integer"},
                        },
                    },
                )
            # 插入数据
            # bulk 采用“操作说明 + 数据本体”交替出现的格式
            # 适合一次性写入多条文档
            await client.bulk(
                operations=[
                    {"index": {"_index": "my-books"}},
                    {
                        "name": "Revelation Space",
                        "author": "Alastair Reynolds",
                        "release_date": "2000-03-15",
                        "page_count": 585,
                    },
                    {"index": {"_index": "my-books"}},
                    {
                        "name": "1984",
                        "author": "George Orwell",
                        "release_date": "1985-06-01",
                        "page_count": 328,
                    },
                    {"index": {"_index": "my-books"}},
                    {
                        "name": "Fahrenheit 451",
                        "author": "Ray Bradbury",
                        "release_date": "1953-10-15",
                        "page_count": 227,
                    },
                    {"index": {"_index": "my-books"}},
                    {
                        "name": "Brave New World",
                        "author": "Aldous Huxley",
                        "release_date": "1932-06-01",
                        "page_count": 268,
                    },
                    {"index": {"_index": "my-books"}},
                    {
                        "name": "The Handmaids Tale",
                        "author": "Margaret Atwood",
                        "release_date": "1985-06-01",
                        "page_count": 311,
                    },
                ],
            )

            resp = await client.search(
                index="my-books",
                query={"match": {"name": "brave"}},
            )

            print(resp)
        finally:
            # 成功或异常都关闭连接，避免 aiohttp ClientSession 未关闭告警
            await es_client_manager.close()

    asyncio.run(test())
