"""
LogBolt基础使用示例
"""
from logbolt import LogBolt, LogLevel, ConsoleHandler, FileHandler, CompiledFormatter

# 方式1：手动装配Logger
logger = LogBolt("myapp")
logger.set_level(LogLevel.DEBUG)

# 添加控制台输出（带颜色）
console = ConsoleHandler(LogLevel.DEBUG)
console.set_formatter(CompiledFormatter(
    fmt="\033[92m{asctime}\033[0m \033[93m[{levelname}]\033[0m {message}",
    datefmt="%H:%M:%S"
))
logger.add_handler(console)

# 添加文件输出（自动轮转）
file_handler = FileHandler(
    filename="logs/app.log",
    level=LogLevel.INFO,
    max_bytes=1024*1024,  # 1MB
    backup_count=3
)
file_handler.set_formatter(CompiledFormatter(
    fmt="{asctime} | {levelname:8} | {thread_id:5} | {message}",
    datefmt="%Y-%m-%d %H:%M:%S.%f"
))
logger.add_handler(file_handler)

# 记录日志
logger.debug("调试信息", user_id=1001)
logger.info("用户登录", username="admin")
logger.warning("磁盘使用率超过85%", usage="87%")
logger.error("数据库连接失败", host="192.168.1.100")
logger.critical("系统崩溃", error_code=500)

# 关闭日志（释放资源）
logger.close()