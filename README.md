# LogBolt 🚀

一个高自定义、高速、简洁的日志IO库

[![PyPI version](https://badge.fury.io/py/LogBolt.svg)](https://badge.fury.io/py/LogBolt)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 特性 ✨

- **高性能**: 专为速度优化的日志处理
- **高自定义**: 灵活的格式化和处理选项
- **简洁API**: 简单易用的接口设计
- **线程安全**: 多线程环境下的安全操作
- **自动轮转**: 支持日志文件自动轮转
- **多处理器**: 控制台、文件等多种输出方式

## 快速开始 🚀

### 安装

```bash
pip install LogBolt
```

### 基本用法

```python
from logbolt import LogBolt, LogLevel

# 创建日志器
logger = LogBolt("MyApp")

# 添加控制台处理器
from logbolt.core import ConsoleHandler
console_handler = ConsoleHandler(LogLevel.INFO)
logger.add_handler(console_handler)

# 添加文件处理器
from logbolt.core import FileHandler  
file_handler = FileHandler("app.log", LogLevel.DEBUG)
logger.add_handler(file_handler)

# 记录日志
logger.info("应用启动成功")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 快速配置

```python
from logbolt import quick_setup

# 快速设置控制台和文件日志
logger = quick_setup("app.log", LogLevel.INFO)

logger.info("快速配置完成！")
```

### 自定义格式

```python
from logbolt import LogBolt, LogFormatter
from logbolt.core import ConsoleHandler

# 创建自定义格式化器
formatter = LogFormatter(
    fmt="{asctime} | {levelname:8} | {message}",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 创建处理器并设置格式
handler = ConsoleHandler(LogLevel.DEBUG)
handler.set_formatter(formatter)

# 创建日志器并添加处理器
logger = LogBolt("CustomApp")
logger.add_handler(handler)

logger.info("自定义格式日志")
```

## 高级用法 🔧

### 日志级别

```python
from logbolt import LogLevel

logger.set_level(LogLevel.DEBUG)  # 设置全局日志级别
```

### 文件轮转

```python
from logbolt.core import FileHandler

# 配置日志文件轮转 (10MB, 保留5个备份)
handler = FileHandler(
    filename="app.log",
    level=LogLevel.INFO,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5
)
```

### 多处理器配置

```python
from logbolt import LogBolt
from logbolt.core import ConsoleHandler, FileHandler

logger = LogBolt("MultiHandler")

# 控制台处理器 - INFO级别
console_handler = ConsoleHandler(LogLevel.INFO)
logger.add_handler(console_handler)

# 错误日志文件 - ERROR级别
error_handler = FileHandler("errors.log", LogLevel.ERROR)
logger.add_handler(error_handler)

# 调试日志文件 - DEBUG级别  
debug_handler = FileHandler("debug.log", LogLevel.DEBUG)
logger.add_handler(debug_handler)
```

## API文档 📚

### LogBolt类

- `__init__(name: str = "LogBolt")` - 创建日志器实例
- `set_level(level: LogLevel)` - 设置日志级别
- `add_handler(handler: LogHandler)` - 添加处理器
- `remove_handler(handler: LogHandler)` - 移除处理器
- `debug(msg: str, **kwargs)` - 记录调试信息
- `info(msg: str, **kwargs)` - 记录信息
- `warning(msg: str, **kwargs)` - 记录警告
- `error(msg: str, **kwargs)` - 记录错误
- `critical(msg: str, **kwargs)` - 记录严重错误
- `close()` - 关闭所有处理器

### 日志级别

- `LogLevel.DEBUG` - 调试信息 (10)
- `LogLevel.INFO` - 信息 (20) 
- `LogLevel.WARNING` - 警告 (30)
- `LogLevel.ERROR` - 错误 (40)
- `LogLevel.CRITICAL` - 严重错误 (50)

### 处理器

- `ConsoleHandler(level=LogLevel.INFO, stream=None)` - 控制台输出
- `FileHandler(filename, level=LogLevel.INFO, max_bytes=10MB, backup_count=5)` - 文件输出

## 性能特点 ⚡

- **异步安全**: 线程安全的日志操作
- **内存优化**: 高效的内存使用
- **快速格式化**: 优化的日志格式化
- **智能轮转**: 高效的日志文件轮转

## 贡献 🤝

欢迎提交 Issue 和 Pull Request！

## 许可证 📄

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 作者 👨‍💻

- **dhjs0000** - 3110197220@qq.com

## 链接 🔗

- **GitHub仓库**: https://github.com/dhjs0000/logbolt
- **PyPI页面**: https://pypi.org/project/LogBolt/

---

**享受高速日志记录的乐趣！** 🎉