# example/basic.py - 最终版
import sys
sys.path.insert(0, 'src')

import os
import time
from logbolt import LogBolt, LogLevel, ConsoleHandler, FileHandler, CompiledFormatter

# 确保目录存在
os.makedirs("logs", exist_ok=True)

# 创建logger
logger = LogBolt("myapp")
logger.set_level(LogLevel.DEBUG)

# 控制台处理器
console = ConsoleHandler(LogLevel.DEBUG)
console.set_formatter(CompiledFormatter(
    fmt="{asctime} [{levelname}] {message}",
    datefmt="%H:%M:%S"
))
logger.add_handler(console)

# 文件处理器（关键：级别设置为DEBUG）
file_handler = FileHandler(
    filename="logs/app.log",
    level=LogLevel.DEBUG,  # 必须与logger级别一致或更低
    max_bytes=1024*1024,
    backup_count=3
)
file_handler.set_formatter(CompiledFormatter(
    fmt="{asctime} | {levelname:8} | {message}",
    datefmt="%Y-%m-%d %H:%M:%S.%f"
))
logger.add_handler(file_handler)

# 记录日志
logger.debug("调试信息", user_id=1001)
logger.info("用户登录", username="admin")
logger.warning("磁盘使用率超过85%", usage="87%")
logger.error("数据库连接失败", host="192.168.1.100")
logger.critical("系统崩溃", error_code=500)

# **关键：必须等待异步完成 + 关闭logger**
print("等待日志写入完成...")
time.sleep(1.0)  # 等待1秒确保所有日志写入
logger.close()   # 关闭会强制刷新

# 验证文件
print(f"\n验证文件内容:")
if os.path.exists("logs/app.log"):
    print(f"文件大小: {os.path.getsize('logs/app.log')} bytes")
    print("文件内容:")
    with open("logs/app.log", "r") as f:
        print(f.read())
else:
    print("❌ 文件不存在！")