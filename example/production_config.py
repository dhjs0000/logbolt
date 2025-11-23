# example/production_config.py - 修复版
"""
生产环境最佳实践配置
"""
import os
import sys
import time  # 必须导入
from logbolt import (
    LogBolt, LogLevel, CompiledFormatter, ConsoleHandler,
    FileHandler, SamplingFilter  # 暂时移除 LockFreeFileHandler
)

def create_production_logger(name: str = "service"):
    """创建生产级Logger"""
    
    logger = LogBolt(name)
    logger.set_level(LogLevel.DEBUG)  # 调低级别以便测试
    
    # 1. 控制台处理器（JSON格式）
    json_formatter = CompiledFormatter(
        fmt='{{"time":"{asctime}","level":"{levelname}","msg":"{message}","thread":{thread_id}}}',
        datefmt="%Y-%m-%dT%H:%M:%S.%fZ"
    )
    console = ConsoleHandler(LogLevel.DEBUG, stream=sys.stdout)
    console.set_formatter(json_formatter)
    logger.add_handler(console)
    
    # 2. 标准文件处理器（100MB轮转）- 使用基础版
    file_handler = FileHandler(
        filename=f"logs/{name}.log",
        level=LogLevel.DEBUG,  # 测试时设为DEBUG
        max_bytes=100 * 1024 * 1024,  # 100MB
        backup_count=10
    )
    file_handler.set_formatter(CompiledFormatter(
        fmt="{asctime} | {levelname:8} | T-{thread_id:5} | {message}",
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
        fmt="{asctime} | {levelname} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S.%f"
    ))
    logger.add_handler(error_handler)
    
    # 4. 采样过滤器（生产环境启用，测试时注释掉）
    logger.add_filter(SamplingFilter(rate=1000))  # 暂时注释！
    
    return logger

# 使用示例
if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    
    logger = create_production_logger("payment-service")
    
    # 写入多条日志确保有内容
    logger.debug("调试：初始化配置")
    logger.info("服务启动", version="1.0.0")
    
    # MDC上下文
    with logger.context(trace_id="trc-123456", user_id=789):
        logger.info("支付请求处理", amount=99.99, currency="CNY")
        logger.bind(order_id="ORD-2024001").info("订单创建成功")
        
        try:
            raise ValueError("支付金额异常")
        except Exception as e:
            logger.error("支付处理失败", exc_info=str(e), amount=999999.99)
    
    # 关键：必须等待异步写入完成
    print("\n等待日志写入完成...")
    time.sleep(2.0)  # 等待2秒
    
    # 关键：必须关闭logger以强制刷新
    logger.close()
    
    # 验证文件
    print("\n=== 验证日志文件 ===")
    for filename in ["logs/payment-service.log", "logs/payment-service_error.log"]:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename}: {size} bytes")
            if size > 0:
                try:
                    # 关键：指定 UTF-8 编码
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"内容预览:\n{content}")
                except Exception as e:
                    print(f"读取文件失败: {e}")
            else:
                print("文件为空")
        else:
            print(f"❌ {filename}: 文件不存在")