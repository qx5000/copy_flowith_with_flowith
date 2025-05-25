"""
Agent 管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import AgentConfig, Tool, User
from .auth import get_current_user

router = APIRouter()

@router.post("/configs")
async def create_agent_config(
    agent_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建 Agent 配置"""
    new_agent = AgentConfig(
        name=agent_data["name"],
        agent_type=agent_data["agent_type"],
        role=agent_data.get("role", ""),
        backstory=agent_data.get("backstory", ""),
        goal=agent_data.get("goal", ""),
        tools=agent_data.get("tools", []),
        llm_config=agent_data.get("llm_config", {}),
        memory_config=agent_data.get("memory_config", {}),
        max_execution_time=agent_data.get("max_execution_time", 300),
        max_iterations=agent_data.get("max_iterations", 10)
    )
    
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    
    return {
        "id": new_agent.id,
        "name": new_agent.name,
        "agent_type": new_agent.agent_type,
        "created_at": new_agent.created_at
    }

@router.get("/configs")
async def get_agent_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Agent 配置列表"""
    agents = db.query(AgentConfig).filter(
        AgentConfig.is_active == True
    ).all()
    
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "role": agent.role,
            "goal": agent.goal,
            "created_at": agent.created_at
        }
        for agent in agents
    ]

@router.get("/configs/{agent_id}")
async def get_agent_config(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 Agent 配置详情"""
    agent = db.query(AgentConfig).filter(
        AgentConfig.id == agent_id,
        AgentConfig.is_active == True
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 配置不存在")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "role": agent.role,
        "backstory": agent.backstory,
        "goal": agent.goal,
        "tools": agent.tools,
        "llm_config": agent.llm_config,
        "memory_config": agent.memory_config,
        "max_execution_time": agent.max_execution_time,
        "max_iterations": agent.max_iterations,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at
    }

@router.put("/configs/{agent_id}")
async def update_agent_config(
    agent_id: str,
    agent_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新 Agent 配置"""
    agent = db.query(AgentConfig).filter(
        AgentConfig.id == agent_id,
        AgentConfig.is_active == True
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 配置不存在")
    
    # 更新字段
    for field in ["name", "role", "backstory", "goal", "tools", "llm_config", 
                  "memory_config", "max_execution_time", "max_iterations"]:
        if field in agent_data:
            setattr(agent, field, agent_data[field])
    
    db.commit()
    db.refresh(agent)
    
    return {"message": "Agent 配置更新成功"}

@router.get("/tools")
async def get_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取可用工具列表"""
    tools = db.query(Tool).filter(Tool.is_active == True).all()
    
    return [
        {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "tool_type": tool.tool_type,
            "schema": tool.schema
        }
        for tool in tools
    ]

@router.post("/tools")
async def create_tool(
    tool_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建工具"""
    new_tool = Tool(
        name=tool_data["name"],
        description=tool_data.get("description", ""),
        tool_type=tool_data["tool_type"],
        config=tool_data.get("config", {}),
        schema=tool_data.get("schema", {})
    )
    
    db.add(new_tool)
    db.commit()
    db.refresh(new_tool)
    
    return {
        "id": new_tool.id,
        "name": new_tool.name,
        "tool_type": new_tool.tool_type,
        "created_at": new_tool.created_at
    }
