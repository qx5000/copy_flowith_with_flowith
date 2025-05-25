import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { Bot, Settings, Play, Pause } from 'lucide-react';
import { useCanvasStore } from '../store/canvasStore';

const AgentNode = ({ id, data, selected }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const { updateNodeData } = useCanvasStore();
  
  const handleConfigChange = (field, value) => {
    const newData = {
      ...data,
      config: {
        ...data.config,
        [field]: value,
      },
    };
    updateNodeData(id, newData);
  };
  
  const toggleExecution = () => {
    setIsRunning(!isRunning);
    // 这里可以添加实际的 Agent 执行逻辑
  };
  
  return (
    <div
      className={`
        bg-white rounded-lg border-2 shadow-lg min-w-[250px] transition-all duration-200
        ${selected ? 'border-blue-500 shadow-blue-200' : 'border-gray-200'}
        ${isRunning ? 'ring-2 ring-green-400' : ''}
      `}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />
      
      {/* 节点头部 */}
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-blue-100 rounded-lg">
            <Bot className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <div className="font-medium text-gray-900 text-sm">
              {data.config?.role || 'AI Agent'}
            </div>
            <div className="text-xs text-gray-500">
              {data.config?.agent_type || 'CrewAI'}
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={toggleExecution}
            className={`p-1.5 rounded transition-colors ${
              isRunning 
                ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                : 'bg-green-100 text-green-600 hover:bg-green-200'
            }`}
          >
            {isRunning ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
          </button>
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          >
            <Settings className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      {/* 节点内容 */}
      <div className="p-3">
        <div className="text-sm text-gray-700 mb-2">
          <strong>目标:</strong> {data.config?.goal || '完成分配的任务'}
        </div>
        
        {data.config?.backstory && (
          <div className="text-xs text-gray-500 mb-3">
            {data.config.backstory}
          </div>
        )}
        
        {/* 工具列表 */}
        {data.config?.tools && data.config.tools.length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-gray-500 mb-1">工具:</div>
            <div className="flex flex-wrap gap-1">
              {data.config.tools.map((tool, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {/* 状态指示器 */}
        <div className="flex items-center justify-between text-xs">
          <div className={`flex items-center space-x-1 ${
            isRunning ? 'text-green-600' : 'text-gray-500'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-300'
            }`} />
            <span>{isRunning ? '运行中' : '待机'}</span>
          </div>
          
          <div className="text-gray-400">
            {data.config?.llm_config?.model || 'gpt-3.5-turbo'}
          </div>
        </div>
      </div>
      
      {/* 展开配置 */}
      {isExpanded && (
        <div className="border-t border-gray-100 p-3 bg-gray-50">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                角色
              </label>
              <input
                type="text"
                value={data.config?.role || ''}
                onChange={(e) => handleConfigChange('role', e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                placeholder="定义 Agent 角色..."
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                目标
              </label>
              <textarea
                value={data.config?.goal || ''}
                onChange={(e) => handleConfigChange('goal', e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                rows="2"
                placeholder="设定具体目标..."
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                背景故事
              </label>
              <textarea
                value={data.config?.backstory || ''}
                onChange={(e) => handleConfigChange('backstory', e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                rows="2"
                placeholder="描述 Agent 背景..."
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                温度设置
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={data.config?.llm_config?.temperature || 0.7}
                onChange={(e) => handleConfigChange('llm_config', {
                  ...data.config?.llm_config,
                  temperature: parseFloat(e.target.value)
                })}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>精确</span>
                <span>{data.config?.llm_config?.temperature || 0.7}</span>
                <span>创意</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />
    </div>
  );
};

export default AgentNode;
