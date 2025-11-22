# __init__.py
"""
LogBolt - 一个高自定义、高速、简洁的日志IO库

A highly customizable, high-performance, and concise logging IO library.
"""

__version__ = "0.1.0"
__author__ = "dhjs0000"
__email__ = "3110197220@qq.com"
__description__ = "一个高自定义、高速、简洁的日志IO库"

from .core import (
    LogBolt, 
    LogLevel, 
    LogFormatter,
    CompiledFormatter,
    LogHandler,
    FileHandler,
    LockFreeFileHandler,
    ConsoleHandler,
    Filter,
    SamplingFilter,
    quick_setup
)

__all__ = [
    "LogBolt",
    "LogLevel", 
    "LogFormatter",
    "CompiledFormatter",
    "LogHandler",
    "FileHandler",
    "LockFreeFileHandler",
    "ConsoleHandler",
    "Filter",
    "SamplingFilter",
    "quick_setup"
]