import React, { useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

import AgentNode from './AgentNode';
import ToolNode from './ToolNode';
import { useCanvasStore } from '../store/canvasStore';
import { useDebouncedCallback } from '../hooks/useDebouncedCallback';

// 自定义节点类型
const nodeTypes = {
  agent: AgentNode,
  tool: ToolNode,
};

const Canvas = ({ canvasId, readonly = false }) => {
  const reactFlowWrapper = useRef(null);
  const { project } = useReactFlow();
  
  const {
    nodes,
    edges,
    setNodes,
    setEdges,
    saveCanvas,
    loadCanvas,
    addNode,
    deleteNode,
    updateNodeData,
  } = useCanvasStore();
  
  const [localNodes, setLocalNodes, onNodesChange] = useNodesState(nodes);
  const [localEdges, setLocalEdges, onEdgesChange] = useEdgesState(edges);
  
  // 防抖保存
  const debouncedSave = useDebouncedCallback(async (nodes, edges) => {
    if (!readonly && canvasId) {
      await saveCanvas(canvasId, { nodes, edges });
    }
  }, 1000);
  
  // 同步本地状态与全局状态
  useEffect(() => {
    setLocalNodes(nodes);
  }, [nodes, setLocalNodes]);
  
  useEffect(() => {
    setLocalEdges(edges);
  }, [edges, setLocalEdges]);
  
  // 节点和边变化时自动保存
  useEffect(() => {
    setNodes(localNodes);
    setEdges(localEdges);
    debouncedSave(localNodes, localEdges);
  }, [localNodes, localEdges, setNodes, setEdges, debouncedSave]);
  
  // 加载画布数据
  useEffect(() => {
    if (canvasId) {
      loadCanvas(canvasId);
    }
  }, [canvasId, loadCanvas]);
  
  // 连接处理
  const onConnect = useCallback(
    (params) => {
      if (!readonly) {
        setLocalEdges((eds) => addEdge(params, eds));
      }
    },
    [readonly, setLocalEdges]
  );
  
  // 拖拽添加节点
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);
  
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      
      if (readonly) return;
      
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');
      
      if (typeof type === 'undefined' || !type) {
        return;
      }
      
      const position = project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });
      
      const newNode = {
        id: `${type}_${Date.now()}`,
        type,
        position,
        data: {
          label: `${type} 节点`,
          config: getDefaultNodeConfig(type),
        },
      };
      
      addNode(newNode);
    },
    [project, readonly, addNode]
  );
  
  // 获取默认节点配置
  const getDefaultNodeConfig = (type) => {
    switch (type) {
      case 'agent':
        return {
          role: '助手',
          goal: '帮助用户完成任务',
          backstory: '一个有用的AI助手',
          tools: [],
          llm_config: {
            model: 'gpt-3.5-turbo',
            temperature: 0.7,
          },
        };
      case 'tool':
        return {
          tool_name: 'search',
          inputs: {},
        };
      default:
        return {};
    }
  };
  
  // 节点选择处理
  const onNodeClick = useCallback((event, node) => {
    console.log('节点被点击:', node);
  }, []);
  
  // 删除选中元素
  const onKeyDown = useCallback(
    (event) => {
      if (event.key === 'Delete' && !readonly) {
        const selectedNodes = localNodes.filter((node) => node.selected);
        const selectedEdges = localEdges.filter((edge) => edge.selected);
        
        selectedNodes.forEach((node) => deleteNode(node.id));
        setLocalEdges((edges) => 
          edges.filter((edge) => !selectedEdges.find((se) => se.id === edge.id))
        );
      }
    },
    [localNodes, localEdges, readonly, deleteNode, setLocalEdges]
  );
  
  useEffect(() => {
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [onKeyDown]);
  
  return (
    <div className="w-full h-full bg-gray-50" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={localNodes}
        edges={localEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        nodesDraggable={!readonly}
        nodesConnectable={!readonly}
        elementsSelectable={!readonly}
        edgesFocusable={!readonly}
        className="bg-gray-50"
      >
        <Background color="#e5e7eb" />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            switch (node.type) {
              case 'agent':
                return '#3b82f6';
              case 'tool':
                return '#10b981';
              default:
                return '#6b7280';
            }
          }}
          className="bg-white border border-gray-200 rounded-lg"
        />
      </ReactFlow>
    </div>
  );
};

export default Canvas;
