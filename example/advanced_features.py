"""
高级功能展示：MDC、Fluent API、自定义过滤器
"""
from logbolt import (
    LogBolt, LogLevel, CompiledFormatter, ConsoleHandler, Filter
)
from typing import Dict, Any

# 自定义过滤器：按关键字过滤
class KeywordFilter(Filter):
    def __init__(self, keywords: list):
        self.keywords = keywords
    
    def filter(self, record: Dict[str, Any]) -> bool:
        msg = record.get('message', '').lower()
        return not any(kw in msg for kw in self.keywords)

# 创建Logger
logger = LogBolt("advanced")
logger.set_level(LogLevel.DEBUG)

# 添加带颜色的控制台输出
console = ConsoleHandler(LogLevel.DEBUG)
formatter = CompiledFormatter(
    fmt="\033[92m{asctime}\033[0m \033[94m[{levelname:^8}]\033[0m \033[95m[T{thread_id}]\033[0m {message}",
    datefmt="%H:%M:%S.%f"
)
console.set_formatter(formatter)
logger.add_handler(console)

# 添加过滤器（屏蔽敏感词）
logger.add_filter(KeywordFilter(['password', 'secret']))

# 1. MDC（Mapped Diagnostic Context）上下文管理器
with logger.context(user_id=12345, request_id="req-abc"):
    logger.info("用户操作", action="login")
    logger.debug("查询数据库", sql="SELECT * FROM users")  # 会被KeywordFilter屏蔽
    
    # 2. Fluent API：链式调用
    logger.bind(
        service="order",
        region="cn-north-1"
    ).info(
        "订单处理",
        order_id="ORD-789",
        items=["item1", "item2"]
    )

# 3. 动态日志级别调整
print("\n--- 动态调整日志级别 ---")
logger.set_level(LogLevel.WARNING)
logger.info("这条不会显示")
logger.warning("警告信息会显示")

# 4. 结构化日志输出
print("\n--- 结构化日志 ---")
class JsonFormatter(CompiledFormatter):
    def format(self, record: Dict[str, Any]) -> str:
        import json
        data = {
            "timestamp": record['timestamp'],
            "level": LogLevel(record['level']).name,
            "message": record['message'],
            **{k: v for k, v in record.items() if k not in 
               ['timestamp', 'level', 'message', '_handlers']}
        }
        return json.dumps(data, ensure_ascii=False)

console.set_formatter(JsonFormatter())
logger.set_level(LogLevel.INFO)
logger.info("结构化日志", meta={"key": "value"}, tags=["tag1", "tag2"])

logger.close()