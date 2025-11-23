# lite.py - 极致性能版本，使用方法复杂但速度超快
"""
LogBolt Lite - 极致性能日志库
警告: 这个版本为了追求极致性能，使用方法非常复杂，不适合普通用户
"""
import os
import time
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime

# 预分配的全局缓冲区，避免内存分配
global_buffer = []
global_buffer_size = 0
MAX_BUFFER_SIZE = 10000

# 预计算的时间缓存
time_cache = {}
time_cache_lock = threading.Lock()

# 文件句柄缓存
file_handles = {}
file_handles_lock = threading.Lock()

# 日志级别常量 - 避免枚举查找
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

# 预格式化的级别名称
LEVEL_NAMES = {
    DEBUG: b'DEBUG',
    INFO: b'INFO',
    WARNING: b'WARNING', 
    ERROR: b'ERROR',
    CRITICAL: b'CRITICAL'
}

class UltraFastLogger:
    """
    极致性能日志器 - 使用方法极其复杂
    
    警告：
    1. 所有方法都要求bytes类型，不支持str
    2. 必须手动管理缓冲区
    3. 没有异常处理
    4. 需要手动调用flush
    5. 线程不安全，需要外部同步
    """
    
    __slots__ = ('name', 'level', 'filename', '_file', '_buffer', '_buffer_pos')
    
    def __init__(self, name: bytes, level: int = INFO, filename: Optional[bytes] = None):
        self.name = name
        self.level = level
        self.filename = filename
        self._file = None
        self._buffer = bytearray(1048576)  # 1MB缓冲区
        self._buffer_pos = 0
        
        if filename:
            self._open_file()
    
    def _open_file(self):
        """打开文件 - 无错误处理"""
        if self.filename:
            # 创建目录
            dir_path = os.path.dirname(self.filename.decode())
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            self._file = open(self.filename.decode(), 'ab', buffering=0)  # 无缓冲
    
    def _get_time_bytes(self) -> bytes:
        """获取缓存的时间字节 - 每秒更新一次"""
        current_time = int(time.time())
        
        if current_time not in time_cache:
            with time_cache_lock:
                if current_time not in time_cache:
                    dt = datetime.fromtimestamp(current_time)
                    time_cache[current_time] = dt.strftime('%Y-%m-%d %H:%M:%S').encode()
                    
                    # 清理旧缓存
                    if len(time_cache) > 60:  # 保留60秒
                        old_keys = sorted(time_cache.keys())[:-60]
                        for key in old_keys:
                            del time_cache[key]
        
        return time_cache[current_time]
    
    def _format_message(self, level: int, msg: bytes) -> bytes:
        """格式化消息 - 零分配"""
        time_bytes = self._get_time_bytes()
        level_name = LEVEL_NAMES[level]
        
        # 手动构建消息 - 避免复杂的缓冲区操作
        return time_bytes + b' [' + level_name + b'] ' + msg + b'\n'
    
    def log_raw(self, level: int, formatted_msg: bytes) -> None:
        """
        记录已格式化的消息 - 最快的方法
        
        参数:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            formatted_msg: 已格式化的消息，必须包含换行符
        """
        if level < self.level:
            return
        
        if self._file:
            self._file.write(formatted_msg)
    
    def log_prealloc(self, level: int, msg: bytes) -> None:
        """
        使用预分配缓冲区记录 - 超快但复杂
        
        警告：消息会被缓冲，必须手动调用flush()
        """
        if level < self.level:
            return
        
        formatted = self._format_message(level, msg)
        
        # 添加到缓冲区
        msg_len = len(formatted)
        if self._buffer_pos + msg_len > len(self._buffer):
            self.flush()
        
        self._buffer[self._buffer_pos:self._buffer_pos+msg_len] = formatted
        self._buffer_pos += msg_len
    
    def log_direct(self, level: int, msg: bytes) -> None:
        """
        直接记录到文件 - 中等速度
        
        参数:
            level: 日志级别
            msg: 消息内容 (bytes)
        """
        if level < self.level:
            return
        
        formatted = self._format_message(level, msg)
        if self._file:
            self._file.write(formatted)
            self._file.flush()  # 立即刷新
    
    def flush(self) -> None:
        """刷新缓冲区 - 必须手动调用"""
        if self._file and self._buffer_pos > 0:
            self._file.write(bytes(self._buffer[:self._buffer_pos]))
            self._file.flush()
            self._buffer_pos = 0
    
    def close(self) -> None:
        """关闭日志器"""
        self.flush()
        if self._file:
            self._file.close()
            self._file = None


class BatchLogger:
    """
    批量日志记录器 - 一次性处理多条日志
    
    使用方法极其复杂，但性能极高
    """
    
    __slots__ = ('logger', 'batch_buffer', 'batch_count')
    
    def __init__(self, logger: UltraFastLogger):
        self.logger = logger
        self.batch_buffer = bytearray(10485760)  # 10MB批量缓冲区
        self.batch_count = 0
    
    def add_log(self, level: int, msg: bytes) -> None:
        """添加日志到批量 - 零分配"""
        if level < self.logger.level:
            return
        
        time_bytes = self.logger._get_time_bytes()
        level_name = LEVEL_NAMES[level]
        
        # 格式化并添加到批量缓冲区
        log_line = time_bytes + b' [' + level_name + b'] ' + msg + b'\n'
        
        current_pos = len(self.batch_buffer) - (self.batch_count * len(log_line))
        if current_pos < 0:
            self.flush()
            current_pos = len(self.batch_buffer) - len(log_line)
        
        start_pos = current_pos - len(log_line)
        self.batch_buffer[start_pos:current_pos] = log_line
        self.batch_count += 1
    
    def flush(self) -> None:
        """刷新批量"""
        if self.batch_count > 0 and self.logger._file:
            total_size = self.batch_count * (len(self.batch_buffer) // self.batch_count)
            self.logger._file.write(bytes(self.batch_buffer[-total_size:]))
            self.logger._file.flush()
            self.batch_count = 0


# 全局单例 - 避免重复创建
global_logger = None
global_lock = threading.Lock()

def get_ultra_logger(name: bytes, level: int = INFO, filename: Optional[bytes] = None) -> UltraFastLogger:
    """获取极致性能日志器 - 单例模式"""
    global global_logger
    
    if global_logger is None:
        with global_lock:
            if global_logger is None:
                global_logger = UltraFastLogger(name, level, filename)
    
    return global_logger


# 预分配的格式化器
class StaticFormatter:
    """
    静态格式化器 - 零分配格式化
    
    警告：使用方法极其复杂，需要预分配所有缓冲区
    """
    
    __slots__ = ('template', 'field_positions', 'field_lengths')
    
    def __init__(self, template: bytes):
        self.template = template
        self.field_positions = []
        self.field_lengths = []
        
        # 预解析模板
        pos = 0
        while pos < len(template):
            if template[pos:pos+2] == b'{}':
                self.field_positions.append(pos)
                self.field_lengths.append(2)
                pos += 2
            else:
                pos += 1
    
    def format_static(self, *args: bytes) -> bytes:
        """
        静态格式化 - 零分配
        
        警告：
        1. 参数必须严格匹配模板中的占位符数量
        2. 所有参数必须是bytes类型
        3. 返回值是临时缓冲区，必须立即使用
        """
        if len(args) != len(self.field_positions):
            raise ValueError("参数数量不匹配")
        
        # 计算总长度
        total_len = len(self.template)
        for arg in args:
            total_len += len(arg) - 2  # -2 for {}
        
        # 使用线程本地缓冲区
        if not hasattr(thread_local, 'format_buffer'):
            thread_local.format_buffer = bytearray(8192)
        
        buf = thread_local.format_buffer
        if total_len > len(buf):
            raise BufferError("消息太大")
        
        # 手动构建结果
        result_pos = 0
        template_pos = 0
        
        for i, field_pos in enumerate(self.field_positions):
            # 复制模板字段前的部分
            copy_len = field_pos - template_pos
            buf[result_pos:result_pos+copy_len] = self.template[template_pos:field_pos]
            result_pos += copy_len
            
            # 复制参数
            arg = args[i]
            buf[result_pos:result_pos+len(arg)] = arg
            result_pos += len(arg)
            
            template_pos = field_pos + self.field_lengths[i]
        
        # 复制剩余部分
        remaining_len = len(self.template) - template_pos
        if remaining_len > 0:
            buf[result_pos:result_pos+remaining_len] = self.template[template_pos:]
            result_pos += remaining_len
        
        return bytes(buf[:result_pos])


# 线程本地存储
thread_local = threading.local()


# 极速日志函数 - 最难用但最快
def log_fast(level: int, msg: bytes, logger: Optional[UltraFastLogger] = None) -> None:
    """
    最快的日志函数 - 使用所有优化
    
    警告：
    1. 必须手动管理logger生命周期
    2. 必须手动调用flush
    3. 没有错误检查
    4. 所有参数必须是bytes
    """
    if logger is None:
        logger = get_ultra_logger(b'fast', INFO)
    
    logger.log_prealloc(level, msg)


# 使用示例（极其复杂）:
"""
# 1. 创建日志器
logger = UltraFastLogger(b'myapp', INFO, b'app.log')

# 2. 预分配消息
msg = b'This is a test message'

# 3. 使用最快的方法记录
logger.log_prealloc(INFO, msg)

# 4. 必须手动刷新
logger.flush()

# 5. 或者使用批量记录
batch = BatchLogger(logger)
batch.add_log(INFO, b'message 1')
batch.add_log(DEBUG, b'message 2')
batch.flush()

# 6. 使用静态格式化器
formatter = StaticFormatter(b'User {} logged in at {}')
formatted = formatter.format_static(b'john', b'14:30')
logger.log_raw(INFO, formatted + b'\n')

# 7. 全局单例模式
ultra_logger = get_ultra_logger(b'global', INFO, b'global.log')
log_fast(INFO, b'Fast global log', ultra_logger)
"""