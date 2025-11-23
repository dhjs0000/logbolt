# LogBolt API 文档  
**高性能、异步、零拷贝 Python 日志库 —— 为高吞吐、低延迟系统而生**  
*最后更新：2025年11月23日*

---

## 📦 概述

`LogBolt` 是一个专为高性能场景设计的轻量级日志库。核心特性包括：

- ✅ **异步批处理写入**：日志记录非阻塞，后台线程批量刷盘  
- ✅ **零动态分配热点路径**：关键路径使用 `__slots__` + 预编译格式化器  
- ✅ **多处理器支持**：控制台、轮转文件、无锁文件（需 `atomics`）  
- ✅ **上下文绑定（MDC）**：支持线程安全的动态字段注入  
- ✅ **Fluent API**：链式调用与上下文克隆  
- ✅ **过滤链**：支持采样防洪、自定义过滤逻辑  
- ✅ **线程/进程安全**：默认处理器均加锁保护，支持无锁模式  

> 📌 兼容 Python 3.8+  
> 🔌 依赖：`atomics`（可选，用于 `LockFreeFileHandler` 和原子采样）

---

## 🚀 快速开始

```python
from core import quick_setup, LogLevel

# 快速配置：控制台 + 轮转文件（100MB/10份）
logger = quick_setup("app.log", level=LogLevel.DEBUG)

logger.info("系统启动", module="main", version="1.0.0")
# ➜ 2025-11-23 14:23:45 [INFO] [12345] 系统启动

with logger.context(user_id="U123", request_id="R456"):
    logger.debug("查询数据库", sql="SELECT * FROM users")
    # ➜ 2025-11-23 14:23:45.123456 [DEBUG] [12345] 查询数据库
```

---

## 🏗️ 核心类与接口

### `LogLevel` — 日志级别枚举
```python
class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
```

> ⚠️ 支持数值比较：`record['level'] >= handler.level`

---

### `LogBolt` — 主日志类

#### 构造
```python
logger = LogBolt(name="my_app")
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 日志器名称，默认 `"LogBolt"` |

#### 核心方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `set_level(level)` | `level: LogLevel` | 设置最低记录级别 |
| `add_handler(handler)` | `handler: LogHandler` | 添加处理器 |
| `remove_handler(handler)` | `handler: LogHandler` | 移除处理器 |
| `add_filter(filter)` | `filter: Filter` | 添加过滤器（实现 `filter(record) -> bool`） |
| `context(**ctx)` | `→ ContextManager` | **MDC 上下文管理器**（线程局部变量风格） |
| `bind(**ctx)` | `→ LogBolt` | 创建**上下文绑定副本**（Fluent API） |
| `debug/info/warning/error/critical(msg, **kwargs)` | `msg: str, **extra_fields` | 日志记录方法；`kwargs` 将合并进日志记录 |
| `close()` | — | **优雅关闭**：等待异步队列清空 + 关闭所有处理器 |

#### 示例：Fluent API 与上下文继承
```python
base = LogBolt("api")
base.add_handler(ConsoleHandler())

req_logger = base.bind(service="user-api", version="2.1")
with req_logger.context(request_id="req-789"):
    req_logger.info("处理请求", method="POST", path="/login")
    # ➜ {..., "service": "user-api", "version": "2.1", "request_id": "req-789", ...}
```

> ✅ `bind()` 创建浅拷贝，不影响原 logger；`context()` 是 runtime only，不污染全局

---

### `LogFormatter` & `CompiledFormatter` — 格式化器

#### `LogFormatter`（基础）
```python
fmt = LogFormatter(
    fmt="{asctime} - {name} - {levelname} - {message}",
    datefmt="%Y-%m-%d %H:%M:%S"
)
```

#### `CompiledFormatter`（**推荐**：高性能预编译）
- ✅ 解析模板为闭包函数，避免运行时 `str.format()` 开销
- ✅ 支持字段：`asctime`, `levelname`, `message`, `name`, `thread_id`, `process_id`, + 任意 `record[key]`

```python
fmt = CompiledFormatter(
    "{asctime} [{levelname}] {name}@{thread_id} | {message}",
    datefmt="%m-%d %H:%M:%S.%f"
)
handler.set_formatter(fmt)
```

> 💡 若模板含未注册字段（如 `{user_id}`），会自动回退到 `record.get('user_id', '')`

---

### `Filter` 协议 & 内置过滤器

#### 协议定义
```python
class Filter(Protocol):
    def filter(self, record: Dict[str, Any]) -> bool: ...
```

#### `SamplingFilter` — 采样防洪
```python
# 每 100 条日志采样 1 条（DEBUG/INFO 级别适用）
sampler = SamplingFilter(rate=100)
logger.add_filter(sampler)
```
- ✅ 线程安全：使用 `atomics`（若可用）或普通计数器  
- ✅ 保证全局采样率，非 per-thread

> 🛑 **注意**：过滤发生在 `logger._log()` 内，在异步派发**之前**，避免无用序列化

---

## 🖨️ 处理器（Handlers）

所有处理器继承 `LogHandler`，支持：
```python
handler.level = LogLevel.WARNING  # 设置处理器最低级别
handler.set_formatter(my_formatter)
```

### `ConsoleHandler`
```python
ConsoleHandler(
    level=LogLevel.INFO,
    stream=sys.stdout  # 可设为 sys.stderr
)
```
- 🔒 线程安全（`threading.Lock`）  
- ✅ 批量写入优化：`_emit_batch()` 支持多行拼接后单次写入

---

### `FileHandler` — 轮转文件处理器（**默认推荐**）
```python
FileHandler(
    filename="app.log",
    level=LogLevel.DEBUG,
    max_bytes=100 * 1024 * 1024,  # 100MB
    backup_count=10               # 最多保留 10 个备份
)
```
- ✅ 自动创建目录（`os.makedirs(..., exist_ok=True)`）  
- ✅ 轮转策略：`app.log` → `app.log.1` → `app.log.2` …  
- 🔒 线程安全（单 `Lock` 保护文件 I/O）  
- 💾 缓冲写入（`buffering=8192`） + 每次 `flush()`  
- 🧹 `close()` 安全关闭文件

---

### `LockFreeFileHandler` — 无锁文件处理器（**高性能场景**）
```python
LockFreeFileHandler(
    filename="high_perf.log",
    max_bytes=500 * 1024 * 1024,
    backup_count=5
)
```
- ⚠️ **依赖 `pip install atomics`**  
- 🚀 使用 `atomics.atomic` 计数器避免锁竞争  
- 🧵 轮转操作提交至单线程 `ThreadPoolExecutor`，避免主线程阻塞  
- 🔒 **仍保留 `_lock` 保护 `file.write()`**（因 CPython `write()` 非原子，多线程交错会导致行断裂）

> 📊 适用场景：单进程、极高 QPS 日志输出（>100K logs/sec）

---

## 🔄 异步调度器（`AsyncDispatcher`）

- 🧵 单例后台线程，批量处理日志（最大 0.1s 或 500 条触发 flush）
- 📦 队列容量 10,000，满时丢弃新日志（**fail-fast 优于阻塞**）
- ✅ `LogBolt._log()` 调用 `.dispatch()` → 非阻塞入队
- ✅ 支持 `logger.close()` 优雅关闭（等待最多 5 秒）

> 🧠 设计哲学：**日志不应拖慢业务逻辑** —— 丢日志比卡主线程可接受

---

## 📝 日志记录格式（Record Schema）

每条日志为 `Dict[str, Any]`，必含字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Logger 名称 |
| `level` | `int` | `LogLevel` 值（10~50） |
| `message` | `str` | 用户消息 |
| `timestamp` | `int` | 纳秒时间戳（`time.time_ns()`） |
| `thread_id` | `int` | `threading.get_ident()` |
| `process_id` | `int` | `os.getpid()` |

+ 用户传入的 `**kwargs`（如 `user_id="U123"`）  
+ `context()` 或 `bind()` 注入的上下文字段

---

## 🛠️ 工具函数

| 函数 | 签名 | 说明 |
|------|------|------|
| `get_logger(name="LogBolt")` | `→ LogBolt` | 获取新实例（非单例！） |
| `quick_setup(log_file=None, level=INFO)` | `→ LogBolt` | **快速配置**：控制台 + 可选文件处理器 |

> ✅ `quick_setup()` 返回的 logger 已预配置：  
> - 控制台：`{asctime} [{levelname}] {message}`  
> - 文件：`{asctime} [{levelname}] [{thread_id}] {message}`（含微秒）

---

## 🧪 性能提示

| 场景 | 建议 |
|------|------|
| 高频 DEBUG 日志 | + `SamplingFilter(rate=100)` 防刷屏 |
| 关键 ERROR 日志 | 单独加 `FileHandler` 保证持久化 |
| 多服务部署 | 用 `bind(service="auth")` 区分来源 |
| 极限性能 | `LockFreeFileHandler` + `CompiledFormatter` + 异步 batch=500 |
| 避免阻塞 | 永远不要在 logger 回调中做网络/DB 操作 |

---

## 🧹 关闭与清理

```python
logger = quick_setup("app.log")
# ... 使用中 ...

# 退出前调用（如 atexit 或 main() 结尾）：
logger.close()
```
1. 通知 `AsyncDispatcher` 停止并清空队列（≤5s）  
2. 依次调用各 `handler.close()`  
3. `FileHandler` 关闭文件句柄，确保数据落盘  

> ✅ 未调用 `close()` 可能导致最后几条日志丢失（依赖 GC 关闭文件）

---

## 📜 许可证

MIT License — 免费用于商业项目。

---

> 🌟 **LogBolt — 日志如闪电，可靠如磐石**  
> 源码即文档，简洁即力量。  
> — Designed for engineers who care about latency.