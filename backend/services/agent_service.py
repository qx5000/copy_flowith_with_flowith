"""
Agent 服务
集成 LangGraph 和 CrewAI 框架，提供 Agent 执行能力
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from langchain.llms.base import LLM
from langchain.tools.base import BaseTool
from crewai import Agent, Task, Crew
from langgraph import Graph, StateGraph
from langgraph.graph import END

from config import settings
from models import AgentConfig, WorkflowRun

logger = logging.getLogger(__name__)

class AgentService:
    """Agent 服务类"""
    
    def __init__(self):
        self.llm = self._init_llm()
        self.tools = {}
        self.agents = {}
        
    def _init_llm(self):
        """初始化 LLM"""
        try:
            # 这里可以根据配置选择不同的 LLM
            from langchain.llms import Ollama
            return Ollama(
                model=settings.DEFAULT_LLM_MODEL,
                base_url=settings.OLLAMA_BASE_URL
            )
        except Exception as e:
            logger.warning(f"无法连接本地 LLM，使用 OpenAI: {e}")
            from langchain.llms import OpenAI
            return OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def create_crewai_agent(self, config: AgentConfig) -> Agent:
        """创建 CrewAI Agent"""
        tools = await self._load_tools(config.tools)
        
        agent = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=tools,
            llm=self.llm,
            verbose=True,
            memory=config.memory_config.get("enabled", False),
            max_execution_time=config.max_execution_time,
            max_iter=config.max_iterations
        )
        
        return agent
    
    async def create_langgraph_workflow(self, workflow_data: Dict) -> StateGraph:
        """创建 LangGraph 工作流"""
        # 定义工作流状态
        class WorkflowState:
            def __init__(self):
                self.current_step = 0
                self.data = {}
                self.results = []
                self.error = None
        
        def create_state_graph():
            workflow = StateGraph()
            
            # 添加节点
            for node in workflow_data.get("nodes", []):
                if node["type"] == "agent":
                    workflow.add_node(
                        node["id"],
                        self._create_agent_node(node)
                    )
                elif node["type"] == "tool":
                    workflow.add_node(
                        node["id"],
                        self._create_tool_node(node)
                    )
                elif node["type"] == "condition":
                    workflow.add_node(
                        node["id"],
                        self._create_condition_node(node)
                    )
            
            # 添加边（连接）
            for edge in workflow_data.get("edges", []):
                workflow.add_edge(edge["source"], edge["target"])
            
            # 设置入口点
            entry_nodes = [node for node in workflow_data.get("nodes", []) 
                          if node.get("entry", False)]
            if entry_nodes:
                workflow.set_entry_point(entry_nodes[0]["id"])
            
            return workflow
        
        return create_state_graph()
    
    def _create_agent_node(self, node_data: Dict):
        """创建 Agent 节点"""
        async def agent_node(state):
            try:
                agent_config = node_data.get("config", {})
                
                # 创建临时 Agent
                agent = Agent(
                    role=agent_config.get("role", "Assistant"),
                    goal=agent_config.get("goal", "Help with the task"),
                    backstory=agent_config.get("backstory", ""),
                    llm=self.llm,
                    tools=await self._load_tools(agent_config.get("tools", []))
                )
                
                # 执行任务
                task = Task(
                    description=node_data.get("task", ""),
                    agent=agent
                )
                
                result = await asyncio.to_thread(task.execute)
                
                state.data[node_data["id"]] = result
                state.results.append({
                    "node_id": node_data["id"],
                    "type": "agent",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return state
                
            except Exception as e:
                logger.error(f"Agent 节点执行失败: {e}")
                state.error = str(e)
                return state
        
        return agent_node
    
    def _create_tool_node(self, node_data: Dict):
        """创建工具节点"""
        async def tool_node(state):
            try:
                tool_name = node_data.get("tool_name")
                tool_inputs = node_data.get("inputs", {})
                
                # 加载并执行工具
                tool = await self._load_tool(tool_name)
                result = await tool.arun(tool_inputs)
                
                state.data[node_data["id"]] = result
                state.results.append({
                    "node_id": node_data["id"],
                    "type": "tool",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return state
                
            except Exception as e:
                logger.error(f"工具节点执行失败: {e}")
                state.error = str(e)
                return state
        
        return tool_node
    
    def _create_condition_node(self, node_data: Dict):
        """创建条件节点"""
        async def condition_node(state):
            try:
                condition = node_data.get("condition", "")
                
                # 简单条件判断逻辑
                # 这里可以扩展为更复杂的条件判断
                result = eval(condition, {"state": state})
                
                state.data[node_data["id"]] = result
                state.results.append({
                    "node_id": node_data["id"],
                    "type": "condition",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return state
                
            except Exception as e:
                logger.error(f"条件节点执行失败: {e}")
                state.error = str(e)
                return state
        
        return condition_node
    
    async def _load_tools(self, tool_names: List[str]) -> List[BaseTool]:
        """加载工具"""
        tools = []
        for tool_name in tool_names:
            tool = await self._load_tool(tool_name)
            if tool:
                tools.append(tool)
        return tools
    
    async def _load_tool(self, tool_name: str) -> Optional[BaseTool]:
        """加载单个工具"""
        # 这里实现工具加载逻辑
        # 可以从数据库或配置文件中加载工具定义
        
        if tool_name == "search":
            from langchain.tools import DuckDuckGoSearchRun
            return DuckDuckGoSearchRun()
        elif tool_name == "calculator":
            from langchain.tools import Calculator
            return Calculator()
        elif tool_name == "python":
            from langchain.tools import PythonREPLTool
            return PythonREPLTool()
        
        logger.warning(f"未找到工具: {tool_name}")
        return None
    
    async def execute_crew_workflow(self, crew_config: Dict) -> Dict:
        """执行 CrewAI 团队工作流"""
        try:
            # 创建 Agent 列表
            agents = []
            for agent_config in crew_config.get("agents", []):
                agent = await self.create_crewai_agent(agent_config)
                agents.append(agent)
            
            # 创建任务列表
            tasks = []
            for task_config in crew_config.get("tasks", []):
                task = Task(
                    description=task_config["description"],
                    agent=agents[task_config.get("agent_index", 0)]
                )
                tasks.append(task)
            
            # 创建团队
            crew = Crew(
                agents=agents,
                tasks=tasks,
                verbose=True
            )
            
            # 执行工作流
            result = await asyncio.to_thread(crew.kickoff)
            
            return {
                "success": True,
                "result": result,
                "execution_time": None  # 可以添加执行时间统计
            }
            
        except Exception as e:
            logger.error(f"CrewAI 工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_langgraph_workflow(self, workflow_data: Dict) -> Dict:
        """执行 LangGraph 工作流"""
        try:
            # 创建工作流图
            workflow = await self.create_langgraph_workflow(workflow_data)
            
            # 初始化状态
            initial_state = {
                "current_step": 0,
                "data": workflow_data.get("input_data", {}),
                "results": [],
                "error": None
            }
            
            # 编译并执行工作流
            app = workflow.compile()
            final_state = await asyncio.to_thread(app.invoke, initial_state)
            
            return {
                "success": final_state.get("error") is None,
                "result": final_state.get("results", []),
                "error": final_state.get("error"),
                "execution_time": None
            }
            
        except Exception as e:
            logger.error(f"LangGraph 工作流执行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
