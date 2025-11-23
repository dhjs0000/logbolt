#!/usr/bin/env python3
"""
LogBolt Lite 使用示例
展示如何正确使用这个极致性能但极其复杂的日志库
"""

import sys
import os
import time
import threading

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from logbolt.lite import (
    UltraFastLogger, BatchLogger, StaticFormatter,
    get_ultra_logger, log_fast, DEBUG, INFO, WARNING, ERROR
)

def basic_usage():
    """基本用法 - 但已经很复杂了"""
    print("=== 基本用法 (已经很复杂) ===")
    
    # 警告：所有参数必须是bytes类型，不是str！
    logger = UltraFastLogger(b'myapp', INFO, b'lite_basic.log')
    
    # 消息必须是bytes
    logger.log_prealloc(INFO, b'This is an info message')
    logger.log_prealloc(WARNING, b'This is a warning message')
    logger.log_prealloc(ERROR, b'This is an error message')
    
    # 必须手动flush！不会自动刷新！
    logger.flush()
    
    # 必须手动关闭！
    logger.close()
    
    print("✓ 基本用法完成")

def advanced_usage():
    """高级用法 - 极其复杂"""
    print("\n=== 高级用法 (极其复杂) ===")
    
    logger = UltraFastLogger(b'advanced', INFO, b'lite_advanced.log')
    
    # 方法1: 预分配缓冲 (最快但最复杂)
    print("方法1: 预分配缓冲")
    for i in range(10):
        # 必须手动编码所有字符串为bytes
        msg = f"Preallocated message {i}".encode()
        logger.log_prealloc(INFO, msg)
    
    logger.flush()
    
    # 方法2: 直接写入 (中等速度)
    print("方法2: 直接写入")
    for i in range(10):
        msg = f"Direct write message {i}".encode()
        logger.log_direct(INFO, msg)  # 会自动flush
    
    # 方法3: 原始日志 (需要预格式化)
    print("方法3: 原始日志")
    timestamp = b"2024-01-01 12:00:00"
    for i in range(10):
        # 必须手动格式化整个消息
        msg = f"Raw message {i}".encode()
        formatted = timestamp + b" [INFO] " + msg + b"\n"
        logger.log_raw(INFO, formatted)
    
    logger.close()
    print("✓ 高级用法完成")

def batch_usage():
    """批量用法 - 最高性能"""
    print("\n=== 批量用法 (最高性能) ===")
    
    logger = UltraFastLogger(b'batch', INFO, b'lite_batch.log')
    batch = BatchLogger(logger)
    
    # 批量添加日志 - 零分配
    for i in range(100):
        msg = f"Batch message {i}".encode()
        batch.add_log(INFO, msg)
    
    # 一次性flush所有日志
    batch.flush()
    logger.close()
    
    print("✓ 批量用法完成")

def static_formatter_usage():
    """静态格式化器用法"""
    print("\n=== 静态格式化器用法 (零分配) ===")
    
    logger = UltraFastLogger(b'formatter', INFO, b'lite_formatter.log')
    
    # 创建静态格式化器
    formatter = StaticFormatter(b'User {} logged in at {}')
    
    # 预格式化消息
    users = [b'alice', b'bob', b'charlie']
    times = [b'14:30', b'15:45', b'16:20']
    
    for user, timestamp in zip(users, times):
        formatted = formatter.format_static(user, timestamp)
        logger.log_raw(INFO, formatted + b'\n')
    
    logger.close()
    print("✓ 静态格式化器用法完成")

def global_logger_usage():
    """全局单例用法"""
    print("\n=== 全局单例用法 ===")
    
    # 获取全局单例
    logger = get_ultra_logger(b'global', INFO, b'lite_global.log')
    
    # 使用全局快速日志函数
    log_fast(INFO, b'Global fast log message 1')
    log_fast(WARNING, b'Global fast log message 2')
    
    # 必须手动flush全局logger
    logger.flush()
    logger.close()
    
    print("✓ 全局单例用法完成")

def thread_safety_warning():
    """线程安全警告演示"""
    print("\n=== 线程安全警告 ===")
    print("警告：UltraFastLogger不是线程安全的！")
    print("如果多线程使用，必须外部同步！")
    
    logger = UltraFastLogger(b'thread', INFO, b'lite_thread.log')
    lock = threading.Lock()
    
    def worker(worker_id):
        # 必须手动同步！
        with lock:
            msg = f"Thread {worker_id} message".encode()
            logger.log_prealloc(INFO, msg)
            logger.flush()  # 注意：在锁内flush
    
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    logger.close()
    print("✓ 线程安全演示完成")

def performance_comparison():
    """性能对比"""
    print("\n=== 性能对比 ===")
    
    # 测试不同方法的速度
    logger = UltraFastLogger(b'perf', INFO, b'lite_perf.log')
    
    # 方法1: 预分配
    start = time.perf_counter()
    for i in range(1000):
        logger.log_prealloc(INFO, b'message')
    logger.flush()
    prealloc_time = time.perf_counter() - start
    
    # 方法2: 直接写入
    start = time.perf_counter()
    for i in range(1000):
        logger.log_direct(INFO, b'message')
    direct_time = time.perf_counter() - start
    
    # 方法3: 原始日志
    formatted = b"2024-01-01 12:00:00 [INFO] message\n"
    start = time.perf_counter()
    for i in range(1000):
        logger.log_raw(INFO, formatted)
    raw_time = time.perf_counter() - start
    
    logger.close()
    
    print(f"预分配方法: {prealloc_time*1000:.2f}ms")
    print(f"直接写入:  {direct_time*1000:.2f}ms")
    print(f"原始日志:  {raw_time*1000:.2f}ms")
    print(f"最快方法比最慢方法快 {min(prealloc_time, direct_time, raw_time)/max(prealloc_time, direct_time, raw_time):.1f}x")

def common_pitfalls():
    """常见陷阱"""
    print("\n=== 常见陷阱和警告 ===")
    
    print("1. 类型错误 - 必须用bytes，不能用str")
    print("   ❌ logger.log_prealloc(INFO, 'string message')")
    print("   ✅ logger.log_prealloc(INFO, b'bytes message')")
    
    print("\n2. 忘记flush - 日志会丢失")
    print("   ❌ logger.log_prealloc(INFO, b'msg')  # 忘记flush")
    print("   ✅ logger.log_prealloc(INFO, b'msg'); logger.flush()")
    
    print("\n3. 线程不安全")
    print("   ❌ 多线程直接使用同一个logger")
    print("   ✅ 多线程使用锁同步或每个线程一个logger")
    
    print("\n4. 忘记close - 文件句柄泄漏")
    print("   ❌ 创建logger后不close")
    print("   ✅ logger.close()")
    
    print("\n5. 缓冲区溢出")
    print("   ❌ 写入超过缓冲区大小的消息")
    print("   ✅ 定期flush，避免积累太多消息")

def main():
    """主函数"""
    print("LogBolt Lite 使用示例")
    print("警告：这个库极其复杂，不适合心脏不好的人！")
    print("=" * 60)
    
    try:
        basic_usage()
        advanced_usage()
        batch_usage()
        static_formatter_usage()
        global_logger_usage()
        thread_safety_warning()
        performance_comparison()
        common_pitfalls()
        
        print("\n" + "=" * 60)
        print("所有示例完成！")
        print("记住：速度是有代价的 - 复杂性！")
        
    finally:
        # 清理日志文件
        log_files = [
            'lite_basic.log', 'lite_advanced.log', 'lite_batch.log',
            'lite_formatter.log', 'lite_global.log', 'lite_thread.log',
            'lite_perf.log'
        ]
        for file in log_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except:
                pass

if __name__ == "__main__":
    main()