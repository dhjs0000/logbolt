#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LogBolt vs Others: Rigorous Performance Benchmark — FIXED
- Fixes: logbook AttributeError on microsecond//1000
- Fixes: ConsoleHandler format error on thread_id (str vs int)
- Safe fallback for missing libraries
"""

import sys
import os
import time
import threading
import tempfile
from contextlib import redirect_stderr, redirect_stdout

# ---------------------------
# Config
# ---------------------------
LOG_COUNT = 100_000
THREAD_COUNT = 16
WARMUP_ROUNDS = 1
MEASURE_ROUNDS = 3

# Cross-platform null device
NULL_FILE = "nul" if os.name == "nt" else "/dev/null"

# Suppress noisy imports
with open(os.devnull, "w") as devnull:
    _stdout, _stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = devnull, devnull
    try:
        import logging
        import logzero
        import logbook
        import structlog
        from structlog.stdlib import LoggerFactory
        from structlog.dev import ConsoleRenderer
    except ImportError:
        pass
    try:
        import loguru
    except ImportError:
        pass
    try:
        import logbolt
    except ImportError:
        pass
    sys.stdout, sys.stderr = _stdout, _stderr


# ---------------------------
# Utils
# ---------------------------
def run_benchmark(name: str, setup_func, log_func, teardown_func=None):
    for _ in range(WARMUP_ROUNDS):
        logger = setup_func()
        for i in range(int(LOG_COUNT * 0.1)):
            log_func(logger, f"msg-{i}", {"id": i, "tag": "bench"})
        if teardown_func:
            teardown_func(logger)

    durations = []
    for _ in range(MEASURE_ROUNDS):
        start = time.perf_counter()
        logger = setup_func()
        for i in range(LOG_COUNT):
            log_func(logger, f"msg-{i}", {"id": i, "tag": "bench"})
        end = time.perf_counter()
        durations.append(end - start)
        if teardown_func:
            teardown_func(logger)

    avg_sec = sum(durations) / len(durations)
    throughput = LOG_COUNT / avg_sec
    return avg_sec, throughput


def run_multithreaded(name: str, setup_func, log_func, teardown_func=None):
    def worker(logger, start_idx, count):
        for i in range(start_idx, start_idx + count):
            log_func(logger, f"msg-{i}", {"id": i, "tag": "bench", "thread": threading.get_ident() % 1000})

    for _ in range(WARMUP_ROUNDS):
        logger = setup_func()
        threads = []
        per_thread = int(LOG_COUNT * 0.1 // THREAD_COUNT)
        for t in range(THREAD_COUNT):
            th = threading.Thread(target=worker, args=(logger, t * per_thread, per_thread))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()
        if teardown_func:
            teardown_func(logger)

    durations = []
    for _ in range(MEASURE_ROUNDS):
        logger = setup_func()
        start = time.perf_counter()
        threads = []
        per_thread = LOG_COUNT // THREAD_COUNT
        for t in range(THREAD_COUNT):
            th = threading.Thread(target=worker, args=(logger, t * per_thread, per_thread))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()
        end = time.perf_counter()
        durations.append(end - start)
        if teardown_func:
            teardown_func(logger)

    avg_sec = sum(durations) / len(durations)
    throughput = LOG_COUNT / avg_sec
    return avg_sec, throughput


def safe_run(name, setup, log_fn, teardown=None, mt=False):
    try:
        if mt:
            sec, rate = run_multithreaded(name, setup, log_fn, teardown)
        else:
            sec, rate = run_benchmark(name, setup, log_fn, teardown)
        return {"name": name, "time_sec": sec, "throughput": rate}
    except Exception as e:
        print(f"[SKIP] {name}: {e.__class__.__name__}: {e}", file=sys.stderr)
        return None


# ---------------------------
# Loggers — FIXED
# ---------------------------

# --- 1. logging ---
def setup_std_logging():
    logger = logging.getLogger("std_bench")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler(open(NULL_FILE, "w"))
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger

def log_std(logger, msg, extra):
    logger.info(f"{msg} id={extra['id']} tag={extra['tag']}")


# --- 2. logzero ---
def setup_logzero():
    return logzero.setup_logger(
        name="logzero_bench",
        logfile=NULL_FILE,
        level=logzero.logging.INFO,
        formatter=logzero.LogFormatter(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ),
        disableStdLogging=True
    )

def log_logzero(logger, msg, extra):
    logger.info(f"{msg} id={extra['id']} tag={extra['tag']}")


# --- 3. logbook — FIXED ---
def setup_logbook():
    # ✅ FIX: Inject msecs as extra field
    def add_msecs(record):
        record.extra["msecs"] = record.time.microsecond // 1000

    logbook.set_datetime_format("local")
    handler = logbook.FileHandler(NULL_FILE, level=logbook.INFO, mode="w")
    processor = logbook.Processor(add_msecs)

    processor.push_application()
    handler.push_application()

    # Use {record.extra[msecs]:03d} instead of illegal .microsecond//1000
    handler.format_string = (
        "{record.time:%Y-%m-%d %H:%M:%S}.{record.extra[msecs]:03d} | "
        "{record.level_name:<8} | {record.message}"
    )
    return (handler, processor)

def log_logbook(_, msg, extra):
    logbook.info(f"{msg} id={extra['id']} tag={extra['tag']}")

def teardown_logbook(obj):
    handler, processor = obj
    handler.pop_application()
    processor.pop_application()
    handler.close()


# --- 4. structlog ---
def setup_structlog():
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=False),
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger("structlog_bench")
    handler = logging.StreamHandler(open(NULL_FILE, "w"))
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False)
    ))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return logger

def log_structlog(logger, msg, extra):
    logger.info(msg, **extra)


# --- 5. loguru ---
def setup_loguru():
    loguru.logger.remove()
    loguru.logger.add(
        NULL_FILE,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
        enqueue=False,
        colorize=False,
        serialize=False
    )
    return loguru.logger

def log_loguru(logger, msg, extra):
    logger.opt(depth=0).info(f"{msg} id={extra['id']} tag={extra['tag']}")


# --- 6. logbolt — FIXED thread_id format ---
def setup_logbolt():
    logger = logbolt.LogBolt("bench")
    logger.set_level(logbolt.LogLevel.INFO)

    # ✅ FIX: Use {thread_id} instead of {thread_id:d} to avoid str/int mismatch
    handler = logbolt.ConsoleHandler(logbolt.LogLevel.INFO, stream=open(NULL_FILE, "w"))
    handler.set_formatter(logbolt.CompiledFormatter(
        fmt="{asctime}.{msecs:03d} | {levelname:<8} | T{thread_id:>6} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.add_handler(handler)
    return logger

def log_logbolt(logger, msg, extra):
    # LogBolt auto-injects asctime/msecs/thread_id
    logger.info(f"{msg} id={extra['id']} tag={extra['tag']}")


# ---------------------------
# Benchmark
# ---------------------------
def main():
    print(f"=== Log Library Benchmark (FIXED) ===")
    print(f"Logs: {LOG_COUNT:,} | Threads: {THREAD_COUNT} | Null output: {NULL_FILE}")
    print()

    results_single = []
    results_multi = []

    cases = [
        ("logging", setup_std_logging, log_std, None),
        ("logzero", setup_logzero, log_logzero, None),
        ("logbook", setup_logbook, log_logbook, teardown_logbook),
        ("structlog", setup_structlog, log_structlog, None),
        ("loguru", setup_loguru, log_loguru, None),
        ("logbolt", setup_logbolt, log_logbolt, None),
    ]

    print("[1/2] Single-threaded...")
    for name, setup, log_fn, teardown in cases:
        res = safe_run(name, setup, log_fn, teardown, mt=False)
        if res:
            results_single.append(res)
            print(f"✅ {name:10} | {res['time_sec']:.3f}s | {res['throughput']:,.0f} logs/s")

    print("\n[2/2] Multi-threaded...")
    for name, setup, log_fn, teardown in cases:
        res = safe_run(name, setup, log_fn, teardown, mt=True)
        if res:
            results_multi.append(res)
            print(f"✅ {name:10} | {res['time_sec']:.3f}s | {res['throughput']:,.0f} logs/s")

    # Output Markdown tables
    def make_md_table(results, ref="logging"):
        try:
            ref_rate = next(r["throughput"] for r in results if r["name"] == ref)
        except StopIteration:
            ref_rate = 1.0
        lines = [
            "| Library | Time (s) | Throughput (logs/s) | vs `" + ref + "` |",
            "|---------|----------|----------------------|-----------|"
        ]
        for r in sorted(results, key=lambda x: -x["throughput"]):
            ratio = r["throughput"] / ref_rate
            lines.append(f"| `{r['name']}` | {r['time_sec']:.3f} | {r['throughput']:,.0f} | {ratio:.2f}x |")
        return "\n".join(lines)

    print("\n" + "="*60)
    print("📊 SINGLE-THREADED")
    print(make_md_table(results_single))

    print("\n" + "="*60)
    print("📊 MULTI-THREADED (16T)")
    print(make_md_table(results_multi))

    # Save raw
    import json
    with open("benchmark_results.json", "w") as f:
        json.dump({
            "config": {"log_count": LOG_COUNT, "thread_count": THREAD_COUNT},
            "single": results_single,
            "multi": results_multi
        }, f, indent=2)
    print("\n✅ Results saved to `benchmark_results.json`")


if __name__ == "__main__":
    main()