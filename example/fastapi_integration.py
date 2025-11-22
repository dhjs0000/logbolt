"""
FastAPI集成示例：全局请求日志追踪
"""
from fastapi import FastAPI, Request
from logbolt import LogBolt, LogLevel, LogFormatter
import uuid

# 创建全局Logger
logger = LogBolt("api-server")
logger.set_level(LogLevel.INFO)

file_handler = logger.add_handler(
    logger.add_handler(FileHandler("logs/api.log", level=LogLevel.INFO))
)

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """全局请求日志中间件"""
    request_id = str(uuid.uuid4())
    
    # MDC上下文自动附加request_id
    with logger.context(request_id=request_id, path=request.url.path):
        logger.info("Request started", method=request.method)
        
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(duration, 2)
        )
    
    return response

@app.get("/")
async def root():
    logger.bind(user_agent="test-client").info("访问首页")
    return {"message": "Hello LogBolt"}

@app.on_event("shutdown")
def shutdown_event():
    logger.close()