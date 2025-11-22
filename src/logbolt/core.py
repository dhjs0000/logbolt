# core.py
"""
LogBolt核心模块 - 高性能日志库
"""
import os
import sys
import time
import threading
import contextlib
import multiprocessing
import queue
from enum import IntEnum
from typing import Optional, Dict, Any, List, Union, Protocol, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 尝试导入原子操作库，失败则使用锁回退
try:
    import atomics
    _HAS_ATOMICS = True
except ImportError:
    _HAS_ATOMICS = False


class LogLevel(IntEnum):
    """日志级别枚举"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormatter:
    """基础日志格式化器"""
    
    __slots__ = ('fmt', 'datefmt', '_style')
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        self.fmt = fmt or "{asctime} - {levelname} - {message}"
        self.datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        self._style = "{"
    
    def format(self, record: Dict[str, Any]) -> str:
        """将日志记录格式化为字符串"""
        record = record.copy()
        record['asctime'] = datetime.fromtimestamp(record['timestamp'] / 1e9).strftime(self.datefmt)
        record['levelname'] = LogLevel(record['level']).name
        return self.fmt.format(**record)


class CompiledFormatter(LogFormatter):
    """预编译高性能格式化器"""
    
    __slots__ = ('_format_func',)
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        self.datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
        self._format_func = self._compile(fmt or "{asctime} - {levelname} - {message}")
    
    def _compile(self, fmt: str) -> Callable[[Dict[str, Any]], str]:
        """编译格式化函数"""
        # 将{field}转换为record['field']
        code = fmt.replace('{', '{record[').replace('}', ']}')
        
        # 特殊字段处理
        replacements = {
            '{record[asctime]}': 'datetime.fromtimestamp(record["timestamp"]//1e9).strftime(self.datefmt)',
            '{record[levelname]}': 'LogLevel(record["level"]).name'
        }
        
        for old, new in replacements.items():
            code = code.replace(old, f'{{{new}}}')
        
        return eval(f"lambda record: f'''{code}'''", 
                   {'self': self, 'datetime': datetime, 'LogLevel': LogLevel})
    
    def format(self, record: Dict[str, Any]) -> str:
        return self._format_func(record)


class Filter(Protocol):
    """过滤器协议"""
    def filter(self, record: Dict[str, Any]) -> bool: ...


class SamplingFilter:
    """采样过滤器 - 防止日志风暴"""
    
    __slots__ = ('rate', '_counter')
    
    def __init__(self, rate: int = 100):
        self.rate = rate
        if _HAS_ATOMICS:
            self._counter = atomics.atomic(width=4, atype=atomics.UINT)
        else:
            self._counter = 0
    
    def filter(self, record: Dict[str, Any]) -> bool:
        if _HAS_ATOMICS:
            return self._counter.fetch_add(1) % self.rate == 0
        else:
            self._counter += 1
            return self._counter % self.rate == 0


class LogHandler:
    """基础日志处理器"""
    
    __slots__ = ('level', 'formatter')
    
    def __init__(self, level: LogLevel = LogLevel.INFO):
        self.level = level
        self.formatter = CompiledFormatter()
    
    def set_formatter(self, formatter: Union[LogFormatter, CompiledFormatter]):
        """设置自定义格式化器"""
        self.formatter = formatter
    
    def handle(self, record: Dict[str, Any]) -> None:
        """当日志级别足够时处理日志记录"""
        if record['level'] >= self.level:
            self.emit(record)
    
    def emit(self, record: Dict[str, Any]) -> None:
        """发送日志记录 - 由子类实现"""
        raise NotImplementedError


class ConsoleHandler(LogHandler):
    """控制台输出处理器 - 线程安全"""
    
    __slots__ = ('stream', '_lock')
    
    def __init__(self, level: LogLevel = LogLevel.INFO, stream=None):
        super().__init__(level)
        self.stream = stream or sys.stdout
        self._lock = threading.Lock()
    
    def emit(self, record: Dict[str, Any]) -> None:
        """发送日志记录到控制台"""
        try:
            msg = self.formatter.format(record)
            with self._lock:
                self.stream.write(msg + '\n')
                self.stream.flush()
        except Exception as e:
            print(f"ConsoleHandler写入失败: {e}", file=sys.stderr)


class FileHandler(LogHandler):
    """高性能文件日志处理器 - 支持轮转"""
    
    __slots__ = ('filename', 'max_bytes', 'backup_count', '_file', '_lock')
    
    def __init__(self, filename: str, level: LogLevel = LogLevel.INFO,
                 max_bytes: int = 10*1024*1024, backup_count: int = 5):
        super().__init__(level)
        self.filename = filename
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._file = None
        self._lock = threading.Lock()
        self._open_file()
    
    def _open_file(self):
        """打开日志文件"""
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            self._file = open(self.filename, 'a', encoding='utf-8', buffering=8192)
        except IOError as e:
            print(f"无法打开日志文件 {self.filename}: {e}", file=sys.stderr)
    
    def _should_rollover(self) -> bool:
        """检查文件是否需要轮转"""
        if self._file is None:
            return False
        try:
            self._file.flush()
            return os.fstat(self._file.fileno()).st_size >= self.max_bytes
        except (OSError, IOError):
            return False
    
    def _do_rollover(self):
        """执行日志文件轮转"""
        with self._lock:
            if self._file:
                self._file.close()
            
            if self.backup_count > 0:
                for i in range(self.backup_count - 1, 0, -1):
                    sfn = f"{self.filename}.{i}"
                    dfn = f"{self.filename}.{i + 1}"
                    if os.path.exists(sfn):
                        if os.path.exists(dfn):
                            os.remove(dfn)
                        os.rename(sfn, dfn)
                
                dfn = f"{self.filename}.1"
                if os.path.exists(dfn):
                    os.remove(dfn)
                if os.path.exists(self.filename):
                    os.rename(self.filename, dfn)
            
            self._open_file()
    
    def emit(self, record: Dict[str, Any]) -> None:
        """发送日志记录到文件"""
        try:
            if self._should_rollover():
                self._do_rollover()
            
            msg = self.formatter.format(record) + '\n'
            with self._lock:
                if self._file:
                    self._file.write(msg)
        except Exception as e:
            print(f"FileHandler写入失败: {e}", file=sys.stderr)
    
    def _emit_batch(self, messages: List[str]):
        """批量写入优化"""
        data = '\n'.join(messages) + '\n'
        try:
            if self._should_rollover():
                self._do_rollover()
            
            with self._lock:
                if self._file:
                    self._file.write(data)
        except Exception as e:
            print(f"FileHandler批量写入失败: {e}", file=sys.stderr)
    
    def close(self):
        """关闭文件处理器"""
        with self._lock:
            if self._file:
                self._file.close()
                self._file = None


class LockFreeFileHandler(FileHandler):
    """无锁文件处理器 - 需要atomics库支持"""
    
    __slots__ = ('_size_counter', '_executor')
    
    def __init__(self, *args, **kwargs):
        if not _HAS_ATOMICS:
            raise RuntimeError("LockFreeFileHandler需要atomics库: pip install atomics")
        super().__init__(*args, **kwargs)
        self._size_counter = atomics.atomic(width=8, atype=atomics.INT, 
                                           value=os.path.getsize(self.filename))
        self._executor = ThreadPoolExecutor(max_workers=1)
    
    def emit(self, record: Dict[str, Any]) -> None:
        """无锁写入（简化版）"""
        msg = self.formatter.format(record) + '\n'
        data = msg.encode('utf-8')
        size = len(data)
        
        current_size = self._size_counter.fetch_add(size)
        if current_size + size > self.max_bytes:
            self._executor.submit(self._do_rollover)
        
        # 这里简化实现，实际可用mmap实现真正的无锁
        with self._lock:
            if self._file:
                self._file.write(msg)
    
    def close(self):
        super().close()
        self._executor.shutdown(wait=True)


class AsyncDispatcher:
    """无锁异步调度器 - 核心性能组件"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.queue = multiprocessing.Queue(maxsize=10000)
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._process_logs, daemon=True)
        self._worker.start()
        self._initialized = True
    
    def _process_logs(self):
        """后台线程批量处理日志"""
        batch = []
        last_flush = time.perf_counter()
        
        while not self._stop_event.is_set():
            try:
                record = self.queue.get(timeout=0.01)
                batch.append(record)
                
                if (len(batch) >= 500 or 
                    time.perf_counter() - last_flush > 0.1):
                    self._flush_batch(batch)
                    batch.clear()
                    last_flush = time.perf_counter()
            except queue.Empty:
                if batch:
                    self._flush_batch(batch)
                    batch.clear()
                    last_flush = time.perf_counter()
    
    def _flush_batch(self, batch: List[Dict[str, Any]]):
        """批量写入"""
        handler_batches: Dict[LogHandler, List[str]] = {}
        
        for record in batch:
            handlers = record.pop('_handlers', [])
            for handler in handlers:
                if handler.level > record['level']:
                    continue
                msg = handler.formatter.format(record)
                handler_batches.setdefault(handler, []).append(msg)
        
        for handler, messages in handler_batches.items():
            if hasattr(handler, '_emit_batch'):
                handler._emit_batch(messages)
            else:
                for msg in messages:
                    handler.emit({'message': msg})
    
    def dispatch(self, record: Dict[str, Any], handlers: List[LogHandler]):
        """非阻塞派遣日志"""
        try:
            record['_handlers'] = handlers
            self.queue.put_nowait(record)
        except queue.Full:
            # 队列满时丢弃（高性能模式）
            pass
    
    def shutdown(self):
        self._stop_event.set()
        self._worker.join(timeout=5)


class LogBolt:
    """主日志类 - 高性能日志记录"""
    
    __slots__ = ('name', 'level', 'handlers', '_context', '_filter_chain', '_filters')
    
    def __init__(self, name: str = "LogBolt"):
        self.name = name
        self.level = LogLevel.INFO
        self.handlers: List[LogHandler] = []
        self._context: Dict[str, Any] = {}
        self._filters: List[Filter] = []
        self._filter_chain: Callable = lambda r: r
    
    def set_level(self, level: LogLevel):
        """设置全局日志级别"""
        self.level = level
    
    def add_handler(self, handler: LogHandler):
        """添加日志处理器"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler):
        """移除日志处理器"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    def add_filter(self, filter: Filter):
        """添加过滤器"""
        self._filters.append(filter)
        self._rebuild_filter_chain()
    
    def _rebuild_filter_chain(self):
        """构建优化的过滤器执行链"""
        chain = lambda r: r
        for f in reversed(self._filters):
            chain = lambda r, f=f, prev=chain: prev(r) if f.filter(r) else None
        self._filter_chain = chain
    
    @contextlib.contextmanager
    def context(self, **ctx):
        """MDC上下文管理器"""
        old_context = self._context.copy()
        self._context.update(ctx)
        try:
            yield
        finally:
            self._context = old_context
    
    def bind(self, **ctx) -> 'LogBolt':
        """返回绑定新上下文的Logger（Fluent API）"""
        new_logger = LogBolt(self.name)
        new_logger.level = self.level
        new_logger.handlers = self.handlers[:]
        new_logger._filters = self._filters[:]
        new_logger._filter_chain = self._filter_chain
        new_logger._context = {**self._context, **ctx}
        return new_logger
    
    def _build_record(self, level: LogLevel, msg: str, kwargs: Dict) -> Dict:
        """构建日志记录（最小化分配）"""
        record = {
            'name': self.name,
            'level': level,
            'message': msg,
            'timestamp': time.time_ns(),
            'thread_id': threading.get_ident(),
            'process_id': os.getpid(),
        }
        if self._context:
            record.update(self._context)
        if kwargs:
            record.update(kwargs)
        return record
    
    def _log(self, level: LogLevel, msg: str, **kwargs) -> None:
        """内部日志方法 - 快速路径"""
        if level < self.level:
            return
        
        record = self._build_record(level, msg, kwargs)
        
        # 应用过滤器链
        if self._filter_chain(record) is None:
            return
        
        # 异步派遣
        dispatcher = AsyncDispatcher()
        dispatcher.dispatch(record, self.handlers)
    
    def debug(self, msg: str, **kwargs):
        self._log(LogLevel.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log(LogLevel.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(LogLevel.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(LogLevel.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        self._log(LogLevel.CRITICAL, msg, **kwargs)
    
    def close(self):
        """关闭所有处理器"""
        for handler in self.handlers:
            if hasattr(handler, 'close'):
                handler.close()
        # 关闭调度器
        AsyncDispatcher().shutdown()


def get_logger(name: str = "LogBolt") -> LogBolt:
    """获取日志实例"""
    return LogBolt(name)


def quick_setup(log_file: Optional[str] = None, level: LogLevel = LogLevel.INFO) -> LogBolt:
    """快速设置日志器，包含控制台和可选的文件输出"""
    logger = LogBolt("LogBolt")
    logger.set_level(level)
    
    # 高性能控制台处理器
    console_handler = ConsoleHandler(level)
    console_handler.set_formatter(CompiledFormatter(
        "{asctime} [{levelname}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.add_handler(console_handler)
    
    # 高性能文件处理器
    if log_file:
        file_handler = FileHandler(
            log_file, 
            level,
            max_bytes=100*1024*1024,
            backup_count=10
        )
        file_handler.set_formatter(CompiledFormatter(
            "{asctime} [{levelname}] [{thread_id}] {message}",
            datefmt="%Y-%m-%d %H:%M:%S.%f"
        ))
        logger.add_handler(file_handler)
    
    return logger