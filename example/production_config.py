"""
生产环境最佳实践配置
"""
import os
import sys
from logbolt import (
    LogBolt, LogLevel, CompiledFormatter, ConsoleHandler,
    FileHandler, LockFreeFileHandler, SamplingFilter
)

def create_production_logger(name: str = "service"):
    """创建生产级Logger"""
    
    logger = LogBolt(name)
    logger.set_level(LogLevel.INFO)
    
    # 1. 控制台处理器（JSON格式，便于日志收集）
    json_formatter = CompiledFormatter(
        fmt='{{"time":"{asctime}","level":"{levelname}","msg":"{message}","thread":{thread_id}}}',
        datefmt="%Y-%m-%dT%H:%M:%S.%fZ"
    )
    console = ConsoleHandler(LogLevel.INFO, stream=sys.stdout)
    console.set_formatter(json_formatter)
    logger.add_handler(console)
    
    # 2. 文件处理器（异步无锁，极致性能）
    try:
        # 如果安装了atomics库，使用无锁版本
        file_handler = LockFreeFileHandler(
            filename=f"logs/{name}.log",
            level=LogLevel.INFO,
            max_bytes=100 * 1024 * 1024,  # 100MB
            backup_count=10
        )
    except RuntimeError:
        # 回退到标准文件处理器
        file_handler = FileHandler(
            filename=f"logs/{name}.log",
            level=LogLevel.INFO,
            max_bytes=100 * 1024 * 1024,
            backup_count=10
        )
    
    # 结构化格式：时间 | 级别 | 线程ID | 消息 | 上下文
    file_handler.set_formatter(CompiledFormatter(
        fmt="{asctime} | {levelname:8} | T-{thread_id:5} | {message} | {context}",
        datefmt="%Y-%m-%d %H:%M:%S.%f"
    ))
    logger.add_handler(file_handler)
    
    # 3. 错误日志分离
    error_handler = FileHandler(
        filename=f"logs/{name}_error.log",
        level=LogLevel.ERROR,
        max_bytes=50 * 1024 * 1024,
        backup_count=5
    )
    error_handler.set_formatter(CompiledFormatter(
        fmt="{asctime} | {levelname} | {message} | {exc_info}",
        datefmt="%Y-%m-%d %H:%M:%S.%f"
    ))
    logger.add_handler(error_handler)
    
    # 4. 添加采样过滤器（防止日志风暴）
    logger.add_filter(SamplingFilter(rate=1000))  # 每1000条采样1条
    
    return logger

# 使用示例
if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    
    logger = create_production_logger("payment-service")
    
    # MDC上下文：自动附加追踪ID
    with logger.context(trace_id="trc-123456", user_id=789):
        logger.info("支付请求处理", amount=99.99, currency="CNY")
        
        # Fluent API：链式绑定
        logger.bind(order_id="ORD-2024001").info("订单创建成功")
        
        try:
            raise ValueError("支付金额异常")
        except Exception as e:
            logger.error("支付处理失败", exc_info=str(e), amount=999999.99)
    
    logger.close()