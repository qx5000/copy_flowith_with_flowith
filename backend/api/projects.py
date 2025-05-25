"""
项目管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, User
from .auth import get_current_user

router = APIRouter()

@router.post("/")
async def create_project(
    project_data: dict, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新项目"""
    new_project = Project(
        name=project_data["name"],
        description=project_data.get("description", ""),
        owner_id=current_user.id,
        settings=project_data.get("settings", {})
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return {
        "id": new_project.id,
        "name": new_project.name,
        "description": new_project.description,
        "created_at": new_project.created_at
    }

@router.get("/")
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户项目列表"""
    projects = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.is_active == True
    ).all()
    
    return [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
        for project in projects
    ]

@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "settings": project.settings,
        "created_at": project.created_at,
        "updated_at": project.updated_at
    }

@router.put("/{project_id}")
async def update_project(
    project_id: str,
    project_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新项目"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project.name = project_data.get("name", project.name)
    project.description = project_data.get("description", project.description)
    project.settings = project_data.get("settings", project.settings)
    
    db.commit()
    db.refresh(project)
    
    return {"message": "项目更新成功"}

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除项目（软删除）"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    project.is_active = False
    db.commit()
    
    return {"message": "项目删除成功"}
