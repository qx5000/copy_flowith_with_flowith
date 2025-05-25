"""
AI Agent 平台后端主入口文件
基于 FastAPI 构建的 RESTful API 服务
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base
from api import auth, projects, canvas, agents, knowledge
from services.workflow_service import WorkflowService
from services.websocket_manager import ConnectionManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# WebSocket 连接管理器
manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在启动 AI Agent 平台...")
    
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 初始化工作流服务
    workflow_service = WorkflowService()
    app.state.workflow_service = workflow_service
    
    logger.info("AI Agent 平台启动完成")
    yield
    
    # 关闭时执行
    logger.info("正在关闭 AI Agent 平台...")

# 创建 FastAPI 应用实例
app = FastAPI(
    title="AI Agent 本地部署平台",
    description="基于 LangGraph 和 CrewAI 的本地化 AI Agent 系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册 API 路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["项目管理"])
app.include_router(canvas.router, prefix="/api/v1/canvas", tags=["画布管理"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agent管理"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库管理"])

@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "AI Agent 平台运行正常",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "ai-agent-platform",
        "version": "1.0.0"
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 连接端点，用于实时通信"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            logger.info(f"收到客户端 {client_id} 消息: {data}")
            
            # 广播消息到所有连接的客户端
            await manager.broadcast(f"客户端 {client_id}: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"客户端 {client_id} 已断开连接")

@app.post("/api/v1/workflow/execute")
async def execute_workflow(workflow_data: dict):
    """执行工作流"""
    try:
        workflow_service = app.state.workflow_service
        result = await workflow_service.execute_workflow(workflow_data)
        
        # 通过 WebSocket 推送执行结果
        await manager.broadcast({
            "type": "workflow_result",
            "data": result
        })
        
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"工作流执行失败: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
