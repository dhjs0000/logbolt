"""
LogBolt vs 标准logging 性能对比测试
"""
import time
import logging
import threading
from logbolt import LogBolt, LogLevel, quick_setup

# 测试配置
THREADS = 16
LOGS_PER_THREAD = 10000

def benchmark_logbolt():
    """测试LogBolt性能"""
    logger = quick_setup("logs/benchmark.log", LogLevel.INFO)
    
    def worker(tid):
        for i in range(LOGS_PER_THREAD):
            logger.info(f"Log message {i}", thread_id=tid)
    
    start = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    logger.close()
    return time.perf_counter() - start

def benchmark_std_logging():
    """测试标准logging性能"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler("logs/std_logging.log")]
    )
    logger = logging.getLogger()
    
    def worker(tid):
        for i in range(LOGS_PER_THREAD):
            logger.info(f"Log message {i}")
    
    start = time.perf_counter()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    return time.perf_counter() - start

if __name__ == "__main__":
    print("=== LogBolt性能测试 ===")
    duration = benchmark_logbolt()
    total_logs = THREADS * LOGS_PER_THREAD
    print(f"LogBolt: {total_logs}条日志, {duration:.2f}秒, {total_logs/duration:.0f}条/秒")
    
    print("\n=== 标准logging性能测试 ===")
    duration = benchmark_std_logging()
    print(f"标准logging: {total_logs}条日志, {duration:.2f}秒, {total_logs/duration:.0f}条/秒")
    
    # 清理
    import shutil
    shutil.rmtree("logs", ignore_errors=True)