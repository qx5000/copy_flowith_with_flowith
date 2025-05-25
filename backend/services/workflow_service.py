"""
工作流服务
管理工作流的解析、执行和状态跟踪
"""

import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from models import WorkflowRun, Canvas
from .agent_service import AgentService
from database import SessionLocal

logger = logging.getLogger(__name__)

class WorkflowService:
    """工作流服务类"""
    
    def __init__(self):
        self.agent_service = AgentService()
        self.active_workflows = {}  # 活跃的工作流实例
    
    async def execute_workflow(self, workflow_data: Dict) -> Dict:
        """执行工作流"""
        workflow_id = workflow_data.get("workflow_id")
        canvas_id = workflow_data.get("canvas_id")
        
        logger.info(f"开始执行工作流: {workflow_id}")
        
        # 创建工作流执行记录
        db = SessionLocal()
        try:
            workflow_run = WorkflowRun(
                project_id=workflow_data.get("project_id"),
                canvas_id=canvas_id,
                input_data=workflow_data,
                status="running",
                started_at=datetime.now()
            )
            db.add(workflow_run)
            db.commit()
            db.refresh(workflow_run)
            
            # 解析画布数据
            canvas = db.query(Canvas).filter(Canvas.id == canvas_id).first()
            if not canvas:
                raise ValueError("画布不存在")
            
            canvas_data = canvas.canvas_data
            
            # 根据工作流类型执行
            workflow_type = self._determine_workflow_type(canvas_data)
            
            if workflow_type == "crewai":
                result = await self._execute_crewai_workflow(canvas_data, workflow_run.id, db)
            elif workflow_type == "langgraph":
                result = await self._execute_langgraph_workflow(canvas_data, workflow_run.id, db)
            else:
                result = await self._execute_simple_workflow(canvas_data, workflow_run.id, db)
            
            # 更新执行记录
            workflow_run.status = "completed" if result["success"] else "failed"
            workflow_run.output_data = result
            workflow_run.completed_at = datetime.now()
            workflow_run.execution_time = (
                workflow_run.completed_at - workflow_run.started_at
            ).total_seconds()
            
            if not result["success"]:
                workflow_run.error_message = result.get("error", "未知错误")
            
            db.commit()
            
            logger.info(f"工作流执行完成: {workflow_id}, 状态: {workflow_run.status}")
            
            return {
                "workflow_id": workflow_id,
                "run_id": workflow_run.id,
                "status": workflow_run.status,
                "result": result,
                "execution_time": workflow_run.execution_time
            }
            
        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            
            # 更新失败状态
            if 'workflow_run' in locals():
                workflow_run.status = "failed"
                workflow_run.error_message = str(e)
                workflow_run.completed_at = datetime.now()
                db.commit()
            
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e)
            }
        
        finally:
            db.close()
    
    def _determine_workflow_type(self, canvas_data: Dict) -> str:
        """判断工作流类型"""
        nodes = canvas_data.get("nodes", [])
        
        # 检查是否包含多个 Agent（CrewAI 特征）
        agent_nodes = [node for node in nodes if node.get("type") == "agent"]
        if len(agent_nodes) > 1:
            return "crewai"
        
        # 检查是否包含复杂的条件分支（LangGraph 特征）
        condition_nodes = [node for node in nodes if node.get("type") == "condition"]
        if condition_nodes:
            return "langgraph"
        
        return "simple"
    
    async def _execute_crewai_workflow(self, canvas_data: Dict, run_id: str, db: Session) -> Dict:
        """执行 CrewAI 工作流"""
        try:
            # 转换画布数据为 CrewAI 配置
            crew_config = self._convert_to_crewai_config(canvas_data)
            
            # 使用 Agent 服务执行
            result = await self.agent_service.execute_crew_workflow(crew_config)
            
            # 更新执行日志
            self._update_execution_log(run_id, {
                "type": "crewai",
                "crew_config": crew_config,
                "result": result
            }, db)
            
            return result
            
        except Exception as e:
            logger.error(f"CrewAI 工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_langgraph_workflow(self, canvas_data: Dict, run_id: str, db: Session) -> Dict:
        """执行 LangGraph 工作流"""
        try:
            # 使用 Agent 服务执行
            result = await self.agent_service.execute_langgraph_workflow(canvas_data)
            
            # 更新执行日志
            self._update_execution_log(run_id, {
                "type": "langgraph",
                "canvas_data": canvas_data,
                "result": result
            }, db)
            
            return result
            
        except Exception as e:
            logger.error(f"LangGraph 工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_simple_workflow(self, canvas_data: Dict, run_id: str, db: Session) -> Dict:
        """执行简单工作流"""
        try:
            nodes = canvas_data.get("nodes", [])
            edges = canvas_data.get("edges", [])
            
            # 按顺序执行节点
            execution_results = []
            
            for node in nodes:
                node_result = await self._execute_node(node)
                execution_results.append({
                    "node_id": node["id"],
                    "node_type": node.get("type"),
                    "result": node_result,
                    "timestamp": datetime.now().isoformat()
                })
            
            # 更新执行日志
            self._update_execution_log(run_id, {
                "type": "simple",
                "execution_results": execution_results
            }, db)
            
            return {
                "success": True,
                "result": execution_results
            }
            
        except Exception as e:
            logger.error(f"简单工作流执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_node(self, node: Dict) -> Dict:
        """执行单个节点"""
        node_type = node.get("type")
        
        if node_type == "agent":
            return await self._execute_agent_node(node)
        elif node_type == "tool":
            return await self._execute_tool_node(node)
        elif node_type == "input":
            return {"type": "input", "data": node.get("data", {})}
        elif node_type == "output":
            return {"type": "output", "data": node.get("data", {})}
        else:
            return {"type": "unknown", "error": f"未知节点类型: {node_type}"}
    
    async def _execute_agent_node(self, node: Dict) -> Dict:
        """执行 Agent 节点"""
        try:
            agent_config = node.get("data", {}).get("config", {})
            task = node.get("data", {}).get("task", "")
            
            # 简化的 Agent 执行逻辑
            # 实际应该调用 AgentService
            result = f"Agent '{agent_config.get('name', 'Unknown')}' 执行任务: {task}"
            
            return {
                "type": "agent",
                "agent_name": agent_config.get("name"),
                "task": task,
                "result": result,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "agent",
                "error": str(e),
                "success": False
            }
    
    async def _execute_tool_node(self, node: Dict) -> Dict:
        """执行工具节点"""
        try:
            tool_name = node.get("data", {}).get("tool_name", "")
            inputs = node.get("data", {}).get("inputs", {})
            
            # 简化的工具执行逻辑
            result = f"工具 '{tool_name}' 执行完成，输入: {inputs}"
            
            return {
                "type": "tool",
                "tool_name": tool_name,
                "inputs": inputs,
                "result": result,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "tool",
                "error": str(e),
                "success": False
            }
    
    def _convert_to_crewai_config(self, canvas_data: Dict) -> Dict:
        """将画布数据转换为 CrewAI 配置"""
        nodes = canvas_data.get("nodes", [])
        edges = canvas_data.get("edges", [])
        
        agents = []
        tasks = []
        
        for node in nodes:
            if node.get("type") == "agent":
                agent_data = node.get("data", {})
                agents.append({
                    "role": agent_data.get("role", "Assistant"),
                    "goal": agent_data.get("goal", ""),
                    "backstory": agent_data.get("backstory", ""),
                    "tools": agent_data.get("tools", [])
                })
            elif node.get("type") == "task":
                task_data = node.get("data", {})
                tasks.append({
                    "description": task_data.get("description", ""),
                    "agent_index": task_data.get("agent_index", 0)
                })
        
        return {
            "agents": agents,
            "tasks": tasks
        }
    
    def _update_execution_log(self, run_id: str, log_data: Dict, db: Session):
        """更新执行日志"""
        try:
            workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if workflow_run:
                if workflow_run.execution_log:
                    execution_log = workflow_run.execution_log
                else:
                    execution_log = []
                
                execution_log.append(log_data)
                workflow_run.execution_log = execution_log
                db.commit()
                
        except Exception as e:
            logger.error(f"更新执行日志失败: {e}")
    
    async def get_workflow_status(self, run_id: str) -> Dict:
        """获取工作流执行状态"""
        db = SessionLocal()
        try:
            workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if not workflow_run:
                return {"error": "工作流记录不存在"}
            
            return {
                "run_id": workflow_run.id,
                "status": workflow_run.status,
                "started_at": workflow_run.started_at,
                "completed_at": workflow_run.completed_at,
                "execution_time": workflow_run.execution_time,
                "error_message": workflow_run.error_message,
                "execution_log": workflow_run.execution_log or []
            }
            
        finally:
            db.close()
    
    async def cancel_workflow(self, run_id: str) -> Dict:
        """取消工作流执行"""
        db = SessionLocal()
        try:
            workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if not workflow_run:
                return {"error": "工作流记录不存在"}
            
            if workflow_run.status in ["completed", "failed", "cancelled"]:
                return {"error": "工作流已结束，无法取消"}
            
            workflow_run.status = "cancelled"
            workflow_run.completed_at = datetime.now()
            db.commit()
            
            # 如果工作流正在运行，尝试停止
            if run_id in self.active_workflows:
                # 实际项目中需要实现工作流中断逻辑
                del self.active_workflows[run_id]
            
            return {"message": "工作流已取消"}
            
        finally:
            db.close()
