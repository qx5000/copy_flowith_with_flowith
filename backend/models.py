"""
数据模型定义
使用 SQLAlchemy ORM 定义数据库表结构
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    projects = relationship("Project", back_populates="owner")
    knowledge_bases = relationship("KnowledgeBase", back_populates="owner")

class Project(Base):
    """项目模型"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    settings = Column(JSON)  # 项目配置信息
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    owner = relationship("User", back_populates="projects")
    canvases = relationship("Canvas", back_populates="project")
    workflow_runs = relationship("WorkflowRun", back_populates="project")

class Canvas(Base):
    """画布模型"""
    __tablename__ = "canvases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    canvas_data = Column(JSON)  # 存储节点、连接等画布数据
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    project = relationship("Project", back_populates="canvases")
    workflow_runs = relationship("WorkflowRun", back_populates="canvas")

class AgentConfig(Base):
    """Agent 配置模型"""
    __tablename__ = "agent_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)  # CrewAI, LangGraph, etc.
    role = Column(String(100))
    backstory = Column(Text)
    goal = Column(Text)
    tools = Column(JSON)  # 工具列表
    llm_config = Column(JSON)  # LLM 配置
    memory_config = Column(JSON)  # 记忆配置
    max_execution_time = Column(Integer, default=300)
    max_iterations = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Tool(Base):
    """工具模型"""
    __tablename__ = "tools"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    tool_type = Column(String(50), nullable=False)  # function, api, database, etc.
    config = Column(JSON)  # 工具配置
    schema = Column(JSON)  # 工具参数模式
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    collection_name = Column(String(100))  # ChromaDB 集合名称
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    chunk_size = Column(Integer, default=1000)
    chunk_overlap = Column(Integer, default=200)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    owner = relationship("User", back_populates="knowledge_bases")
    sources = relationship("KnowledgeSource", back_populates="knowledge_base")

class KnowledgeSource(Base):
    """知识源模型"""
    __tablename__ = "knowledge_sources"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = Column(String, ForeignKey("knowledge_bases.id"), nullable=False)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # file, url, text
    file_path = Column(String(500))
    url = Column(String(500))
    content = Column(Text)
    metadata = Column(JSON)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关联关系
    knowledge_base = relationship("KnowledgeBase", back_populates="sources")

class WorkflowRun(Base):
    """工作流执行记录模型"""
    __tablename__ = "workflow_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    canvas_id = Column(String, ForeignKey("canvases.id"), nullable=False)
    status = Column(String(50), default="pending")  # pending, running, completed, failed, cancelled
    input_data = Column(JSON)
    output_data = Column(JSON)
    execution_log = Column(JSON)  # 详细执行日志
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time = Column(Float)  # 执行时间（秒）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    project = relationship("Project", back_populates="workflow_runs")
    canvas = relationship("Canvas", back_populates="workflow_runs")
