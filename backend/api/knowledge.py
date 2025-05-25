"""
知识库管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os
import shutil
from typing import List

from database import get_db
from models import KnowledgeBase, KnowledgeSource, User
from .auth import get_current_user
from services.knowledge_service import KnowledgeService
from config import settings

router = APIRouter()

@router.post("/bases")
async def create_knowledge_base(
    kb_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建知识库"""
    knowledge_service = KnowledgeService()
    
    new_kb = KnowledgeBase(
        name=kb_data["name"],
        description=kb_data.get("description", ""),
        owner_id=current_user.id,
        collection_name=f"kb_{current_user.id}_{kb_data['name'].lower().replace(' ', '_')}",
        embedding_model=kb_data.get("embedding_model", "all-MiniLM-L6-v2"),
        chunk_size=kb_data.get("chunk_size", 1000),
        chunk_overlap=kb_data.get("chunk_overlap", 200)
    )
    
    db.add(new_kb)
    db.commit()
    db.refresh(new_kb)
    
    # 在 ChromaDB 中创建集合
    await knowledge_service.create_collection(new_kb.collection_name)
    
    return {
        "id": new_kb.id,
        "name": new_kb.name,
        "collection_name": new_kb.collection_name,
        "created_at": new_kb.created_at
    }

@router.get("/bases")
async def get_knowledge_bases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的知识库列表"""
    knowledge_bases = db.query(KnowledgeBase).filter(
        KnowledgeBase.owner_id == current_user.id,
        KnowledgeBase.is_active == True
    ).all()
    
    return [
        {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "collection_name": kb.collection_name,
            "embedding_model": kb.embedding_model,
            "source_count": len(kb.sources),
            "created_at": kb.created_at,
            "updated_at": kb.updated_at
        }
        for kb in knowledge_bases
    ]

@router.get("/bases/{kb_id}")
async def get_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取知识库详情"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == current_user.id
    ).first()
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "collection_name": kb.collection_name,
        "embedding_model": kb.embedding_model,
        "chunk_size": kb.chunk_size,
        "chunk_overlap": kb.chunk_overlap,
        "sources": [
            {
                "id": source.id,
                "name": source.name,
                "source_type": source.source_type,
                "processing_status": source.processing_status,
                "chunk_count": source.chunk_count,
                "created_at": source.created_at
            }
            for source in kb.sources
        ],
        "created_at": kb.created_at,
        "updated_at": kb.updated_at
    }

@router.post("/bases/{kb_id}/sources/upload")
async def upload_file_source(
    kb_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件到知识库"""
    # 验证知识库权限
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == current_user.id
    ).first()
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    # 保存文件
    file_path = os.path.join(settings.UPLOAD_DIR, f"{kb_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 创建知识源记录
    new_source = KnowledgeSource(
        knowledge_base_id=kb_id,
        name=file.filename,
        source_type="file",
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        processing_status="pending"
    )
    
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    # 异步处理文件（这里简化为同步处理）
    knowledge_service = KnowledgeService()
    try:
        await knowledge_service.process_file_source(new_source.id, db)
    except Exception as e:
        new_source.processing_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")
    
    return {
        "id": new_source.id,
        "name": new_source.name,
        "file_path": new_source.file_path,
        "processing_status": new_source.processing_status
    }

@router.post("/bases/{kb_id}/search")
async def search_knowledge(
    kb_id: str,
    search_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """在知识库中搜索"""
    # 验证知识库权限
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == current_user.id
    ).first()
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    knowledge_service = KnowledgeService()
    results = await knowledge_service.search(
        collection_name=kb.collection_name,
        query=search_data["query"],
        n_results=search_data.get("n_results", 5)
    )
    
    return {
        "query": search_data["query"],
        "results": results
    }

@router.delete("/bases/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除知识库"""
    kb = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.owner_id == current_user.id
    ).first()
    
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 软删除
    kb.is_active = False
    db.commit()
    
    # 删除 ChromaDB 集合
    knowledge_service = KnowledgeService()
    await knowledge_service.delete_collection(kb.collection_name)
    
    return {"message": "知识库删除成功"}
