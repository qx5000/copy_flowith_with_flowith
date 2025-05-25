"""
知识库服务
处理知识库的创建、文档处理、向量化、检索等功能
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings
import PyPDF2
import docx2txt
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from config import settings
from models import KnowledgeSource

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识库服务类"""
    
    def __init__(self):
        # 初始化 ChromaDB 客户端
        self.chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=Settings(
                chroma_server_cors_allow_origins=["*"]
            )
        )
        
        # 初始化嵌入模型
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info("知识库服务初始化完成")
    
    async def create_collection(self, collection_name: str) -> bool:
        """创建 ChromaDB 集合"""
        try:
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": f"Knowledge base collection: {collection_name}"}
            )
            logger.info(f"创建集合成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """删除 ChromaDB 集合"""
        try:
            self.chroma_client.delete_collection(name=collection_name)
            logger.info(f"删除集合成功: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False
    
    async def process_file_source(self, source_id: str, db: Session):
        """处理文件源"""
        source = db.query(KnowledgeSource).filter(KnowledgeSource.id == source_id).first()
        if not source:
            raise ValueError("知识源不存在")
        
        try:
            # 更新处理状态
            source.processing_status = "processing"
            db.commit()
            
            # 提取文档文本
            text_content = await self._extract_text_from_file(source.file_path)
            
            if not text_content:
                raise ValueError("无法提取文档内容")
            
            # 分块处理
            chunks = self._split_text_into_chunks(
                text_content,
                chunk_size=source.knowledge_base.chunk_size,
                overlap=source.knowledge_base.chunk_overlap
            )
            
            # 向量化并存储到 ChromaDB
            await self._store_chunks_to_chromadb(
                chunks,
                source,
                source.knowledge_base.collection_name
            )
            
            # 更新处理状态
            source.processing_status = "completed"
            source.chunk_count = len(chunks)
            db.commit()
            
            logger.info(f"文件处理完成: {source.name}, 生成 {len(chunks)} 个块")
            
        except Exception as e:
            logger.error(f"文件处理失败: {e}")
            source.processing_status = "failed"
            db.commit()
            raise
    
    async def _extract_text_from_file(self, file_path: str) -> str:
        """从文件中提取文本"""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return await self._extract_text_from_pdf(file_path)
            elif file_ext == '.docx':
                return await self._extract_text_from_docx(file_path)
            elif file_ext in ['.txt', '.md']:
                return await self._extract_text_from_txt(file_path)
            else:
                raise ValueError(f"不支持的文件类型: {file_ext}")
                
        except Exception as e:
            logger.error(f"文本提取失败: {e}")
            raise
    
    async def _extract_text_from_pdf(self, file_path: str) -> str:
        """从 PDF 文件中提取文本"""
        def extract():
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        
        return await asyncio.to_thread(extract)
    
    async def _extract_text_from_docx(self, file_path: str) -> str:
        """从 DOCX 文件中提取文本"""
        def extract():
            return docx2txt.process(file_path)
        
        return await asyncio.to_thread(extract)
    
    async def _extract_text_from_txt(self, file_path: str) -> str:
        """从文本文件中提取文本"""
        def extract():
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        
        return await asyncio.to_thread(extract)
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """将文本分割为块"""
        chunks = []
        text_length = len(text)
        
        start = 0
        chunk_id = 0
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # 寻找最近的句号或换行符作为结束点
            if end < text_length:
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                
                if last_period > start + chunk_size * 0.8:
                    end = last_period + 1
                elif last_newline > start + chunk_size * 0.8:
                    end = last_newline + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "start_index": start,
                    "end_index": end,
                    "length": len(chunk_text)
                })
                chunk_id += 1
            
            # 计算下一个块的开始位置（考虑重叠）
            start = max(start + 1, end - overlap)
        
        return chunks
    
    async def _store_chunks_to_chromadb(self, chunks: List[Dict], source: KnowledgeSource, collection_name: str):
        """将文档块存储到 ChromaDB"""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # 准备数据
            documents = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "source_id": source.id,
                    "source_name": source.name,
                    "chunk_id": chunk["id"],
                    "start_index": chunk["start_index"],
                    "end_index": chunk["end_index"],
                    "length": chunk["length"]
                }
                for chunk in chunks
            ]
            ids = [f"{source.id}_{chunk['id']}" for chunk in chunks]
            
            # 生成嵌入向量
            embeddings = await self._generate_embeddings(documents)
            
            # 批量添加到集合
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"成功存储 {len(chunks)} 个文档块到集合 {collection_name}")
            
        except Exception as e:
            logger.error(f"存储文档块失败: {e}")
            raise
    
    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        def encode():
            return self.embedding_model.encode(texts).tolist()
        
        return await asyncio.to_thread(encode)
    
    async def search(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict]:
        """在知识库中搜索"""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # 生成查询向量
            query_embedding = await self._generate_embeddings([query])
            
            # 执行搜索
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化搜索结果
            search_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )):
                search_results.append({
                    "rank": i + 1,
                    "document": doc,
                    "metadata": metadata,
                    "similarity": 1 - distance,  # 转换为相似度分数
                    "source_name": metadata.get("source_name", ""),
                    "chunk_id": metadata.get("chunk_id", "")
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    
    async def get_context_for_query(self, collection_name: str, query: str, max_tokens: int = 2000) -> str:
        """为查询获取上下文，用于 RAG"""
        search_results = await self.search(collection_name, query, n_results=10)
        
        context_parts = []
        token_count = 0
        
        for result in search_results:
            document = result["document"]
            # 简单的 token 计算（实际应该使用 tokenizer）
            doc_tokens = len(document.split())
            
            if token_count + doc_tokens > max_tokens:
                break
            
            context_parts.append(document)
            token_count += doc_tokens
        
        return "\n\n".join(context_parts)
    
    async def add_text_source(self, collection_name: str, text: str, metadata: Dict) -> bool:
        """添加文本源到知识库"""
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            
            # 分块处理
            chunks = self._split_text_into_chunks(text)
            
            # 生成 ID 和元数据
            base_id = metadata.get("source_id", "unknown")
            documents = [chunk["text"] for chunk in chunks]
            ids = [f"{base_id}_{chunk['id']}" for chunk in chunks]
            metadatas = [
                {**metadata, **{"chunk_id": chunk["id"]}}
                for chunk in chunks
            ]
            
            # 生成嵌入向量
            embeddings = await self._generate_embeddings(documents)
            
            # 添加到集合
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            return True
            
        except Exception as e:
            logger.error(f"添加文本源失败: {e}")
            return False
