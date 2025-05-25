"""
画布管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Canvas, Project, User
from .auth import get_current_user

router = APIRouter()

@router.post("/")
async def create_canvas(
    canvas_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建画布"""
    # 验证项目权限
    project = db.query(Project).filter(
        Project.id == canvas_data["project_id"],
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权限")
    
    new_canvas = Canvas(
        project_id=canvas_data["project_id"],
        name=canvas_data["name"],
        description=canvas_data.get("description", ""),
        canvas_data=canvas_data.get("canvas_data", {"nodes": [], "edges": []})
    )
    
    db.add(new_canvas)
    db.commit()
    db.refresh(new_canvas)
    
    return {
        "id": new_canvas.id,
        "name": new_canvas.name,
        "description": new_canvas.description,
        "created_at": new_canvas.created_at
    }

@router.get("/project/{project_id}")
async def get_project_canvases(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目下的画布列表"""
    # 验证项目权限
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在或无权限")
    
    canvases = db.query(Canvas).filter(
        Canvas.project_id == project_id,
        Canvas.is_active == True
    ).all()
    
    return [
        {
            "id": canvas.id,
            "name": canvas.name,
            "description": canvas.description,
            "version": canvas.version,
            "created_at": canvas.created_at,
            "updated_at": canvas.updated_at
        }
        for canvas in canvases
    ]

@router.get("/{canvas_id}")
async def get_canvas(
    canvas_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取画布详情"""
    canvas = db.query(Canvas).join(Project).filter(
        Canvas.id == canvas_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在或无权限")
    
    return {
        "id": canvas.id,
        "project_id": canvas.project_id,
        "name": canvas.name,
        "description": canvas.description,
        "canvas_data": canvas.canvas_data,
        "version": canvas.version,
        "created_at": canvas.created_at,
        "updated_at": canvas.updated_at
    }

@router.put("/{canvas_id}")
async def update_canvas(
    canvas_id: str,
    canvas_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新画布"""
    canvas = db.query(Canvas).join(Project).filter(
        Canvas.id == canvas_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在或无权限")
    
    # 更新画布数据
    if "name" in canvas_data:
        canvas.name = canvas_data["name"]
    if "description" in canvas_data:
        canvas.description = canvas_data["description"]
    if "canvas_data" in canvas_data:
        canvas.canvas_data = canvas_data["canvas_data"]
        canvas.version += 1  # 增加版本号
    
    db.commit()
    db.refresh(canvas)
    
    return {
        "message": "画布更新成功",
        "version": canvas.version
    }

@router.post("/{canvas_id}/save")
async def save_canvas_data(
    canvas_id: str,
    canvas_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存画布数据"""
    canvas = db.query(Canvas).join(Project).filter(
        Canvas.id == canvas_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在或无权限")
    
    # 保存画布数据
    canvas.canvas_data = canvas_data
    canvas.version += 1
    
    db.commit()
    
    return {
        "message": "画布保存成功",
        "version": canvas.version,
        "saved_at": canvas.updated_at
    }

@router.delete("/{canvas_id}")
async def delete_canvas(
    canvas_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除画布（软删除）"""
    canvas = db.query(Canvas).join(Project).filter(
        Canvas.id == canvas_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not canvas:
        raise HTTPException(status_code=404, detail="画布不存在或无权限")
    
    canvas.is_active = False
    db.commit()
    
    return {"message": "画布删除成功"}
