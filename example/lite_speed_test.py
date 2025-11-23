#!/usr/bin/env python3
"""
LogBolt Lite 性能测试
对比标准版本和Lite版本的性能差异
"""

import time
import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from logbolt import LogBolt, LogLevel, CompiledFormatter, FileHandler
from logbolt.lite import UltraFastLogger, BatchLogger, log_fast, DEBUG, INFO

def test_standard_logger():
    """测试标准logger性能"""
    print("=== 测试标准LogBolt性能 ===")
    
    logger = LogBolt('standard')
    logger.set_level(LogLevel.INFO)
    
    # 添加文件处理器
    file_handler = FileHandler('test_standard.log', LogLevel.INFO)
    file_handler.set_formatter(CompiledFormatter("{asctime} [{levelname}] {message}"))
    logger.add_handler(file_handler)
    
    # 预热
    for i in range(1000):
        logger.info(f"预热消息 {i}")
    
    # 正式测试
    start_time = time.perf_counter()
    message_count = 100000
    
    for i in range(message_count):
        logger.info(f"这是测试消息 {i}")
    
    logger.close()
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    rate = message_count / duration
    
    print(f"标准版本: {message_count} 条消息")
    print(f"耗时: {duration:.3f} 秒")
    print(f"速度: {rate:.0f} 条/秒")
    
    return rate

def test_lite_logger():
    """测试Lite logger性能"""
    print("\n=== 测试LogBolt Lite性能 ===")
    
    # 创建Lite logger
    logger = UltraFastLogger(b'lite', INFO, b'test_lite.log')
    
    # 预热
    for i in range(1000):
        logger.log_prealloc(INFO, f"预热消息 {i}".encode())
    logger.flush()
    
    # 正式测试
    start_time = time.perf_counter()
    message_count = 100000
    
    for i in range(message_count):
        logger.log_prealloc(INFO, f"这是测试消息 {i}".encode())
    
    logger.flush()
    logger.close()
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    rate = message_count / duration
    
    print(f"Lite版本: {message_count} 条消息")
    print(f"耗时: {duration:.3f} 秒")
    print(f"速度: {rate:.0f} 条/秒")
    
    return rate

def test_batch_logger():
    """测试批量logger性能"""
    print("\n=== 测试Batch Logger性能 ===")
    
    logger = UltraFastLogger(b'batch', INFO, b'test_batch.log')
    batch = BatchLogger(logger)
    
    # 正式测试
    start_time = time.perf_counter()
    message_count = 100000
    
    for i in range(message_count):
        batch.add_log(INFO, f"这是测试消息 {i}".encode())
    
    batch.flush()
    logger.close()
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    rate = message_count / duration
    
    print(f"Batch版本: {message_count} 条消息")
    print(f"耗时: {duration:.3f} 秒")
    print(f"速度: {rate:.0f} 条/秒")
    
    return rate

def test_raw_logger():
    """测试原始日志记录"""
    print("\n=== 测试原始日志性能 ===")
    
    logger = UltraFastLogger(b'raw', INFO, b'test_raw.log')
    
    # 预格式化消息
    messages = []
    for i in range(100000):
        timestamp = f"2024-01-01 12:00:00"
        msg = f"这是测试消息 {i}".encode()
        formatted = f"{timestamp} [INFO] ".encode() + msg + b'\n'
        messages.append(formatted)
    
    # 正式测试
    start_time = time.perf_counter()
    message_count = len(messages)
    
    for msg in messages:
        logger.log_raw(INFO, msg)
    
    logger.close()
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    rate = message_count / duration
    
    print(f"原始版本: {message_count} 条消息")
    print(f"耗时: {duration:.3f} 秒")
    print(f"速度: {rate:.0f} 条/秒")
    
    return rate

def cleanup():
    """清理测试文件"""
    test_files = ['test_standard.log', 'test_lite.log', 'test_batch.log', 'test_raw.log']
    for file in test_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except:
            pass

def main():
    """主测试函数"""
    print("LogBolt 性能对比测试")
    print("=" * 50)
    
    # 清理旧文件
    cleanup()
    
    try:
        # 运行各项测试
        standard_rate = test_standard_logger()
        lite_rate = test_lite_logger()
        batch_rate = test_batch_logger()
        raw_rate = test_raw_logger()
        
        # 显示对比结果
        print("\n" + "=" * 50)
        print("性能对比结果:")
        print(f"标准版本:     {standard_rate:>10,.0f} 条/秒")
        print(f"Lite版本:     {lite_rate:>10,.0f} 条/秒 ({lite_rate/standard_rate:.1f}x)")
        print(f"Batch版本:    {batch_rate:>10,.0f} 条/秒 ({batch_rate/standard_rate:.1f}x)")
        print(f"原始版本:     {raw_rate:>10,.0f} 条/秒 ({raw_rate/standard_rate:.1f}x)")
        
        fastest = max(lite_rate, batch_rate, raw_rate)
        print(f"\n最快版本比标准版本快 {fastest/standard_rate:.1f} 倍!")
        
    finally:
        cleanup()

if __name__ == "__main__":
    main()