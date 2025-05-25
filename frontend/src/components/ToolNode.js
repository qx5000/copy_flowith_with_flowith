import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { Wrench, Settings, Play, Pause } from 'lucide-react';
import { useCanvasStore } from '../store/canvasStore';

const ToolNode = ({ id, data, selected }) => {
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
  };
  
  const getToolIcon = (toolName) => {
    // 根据工具类型返回不同图标
    switch (toolName) {
      case 'search':
        return '🔍';
      case 'calculator':
        return '🧮';
      case 'python':
        return '🐍';
      case 'database':
        return '🗃️';
      default:
        return '🔧';
    }
  };
  
  return (
    <div
      className={`
        bg-white rounded-lg border-2 shadow-lg min-w-[200px] transition-all duration-200
        ${selected ? 'border-green-500 shadow-green-200' : 'border-gray-200'}
        ${isRunning ? 'ring-2 ring-blue-400' : ''}
      `}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-3 h-3 bg-green-500 border-2 border-white"
      />
      
      {/* 节点头部 */}
      <div className="flex items-center justify-between p-3 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-green-100 rounded-lg">
            <Wrench className="w-4 h-4 text-green-600" />
          </div>
          <div>
            <div className="font-medium text-gray-900 text-sm">
              {data.config?.tool_name || '工具'}
            </div>
            <div className="text-xs text-gray-500">
              {data.config?.tool_type || 'Function'}
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={toggleExecution}
            className={`p-1.5 rounded transition-colors ${
              isRunning 
                ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                : 'bg-blue-100 text-blue-600 hover:bg-blue-200'
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
        <div className="flex items-center space-x-2 mb-3">
          <span className="text-lg">
            {getToolIcon(data.config?.tool_name)}
          </span>
          <div className="text-sm text-gray-700">
            {data.config?.description || '执行特定功能的工具'}
          </div>
        </div>
        
        {/* 输入参数预览 */}
        {data.config?.inputs && Object.keys(data.config.inputs).length > 0 && (
          <div className="mb-3">
            <div className="text-xs text-gray-500 mb-1">输入参数:</div>
            <div className="bg-gray-50 p-2 rounded text-xs">
              {Object.entries(data.config.inputs).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-gray-600">{key}:</span>
                  <span className="text-gray-800 font-mono">
                    {typeof value === 'string' ? value : JSON.stringify(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* 状态指示器 */}
        <div className="flex items-center justify-between text-xs">
          <div className={`flex items-center space-x-1 ${
            isRunning ? 'text-blue-600' : 'text-gray-500'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isRunning ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
            }`} />
            <span>{isRunning ? '执行中' : '就绪'}</span>
          </div>
          
          <div className="text-gray-400">
            {data.config?.version || 'v1.0'}
          </div>
        </div>
      </div>
      
      {/* 展开配置 */}
      {isExpanded && (
        <div className="border-t border-gray-100 p-3 bg-gray-50">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                工具名称
              </label>
              <input
                type="text"
                value={data.config?.tool_name || ''}
                onChange={(e) => handleConfigChange('tool_name', e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                placeholder="工具标识符..."
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                描述
              </label>
              <textarea
                value={data.config?.description || ''}
                onChange={(e) => handleConfigChange('description', e.target.value)}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                rows="2"
                placeholder="工具功能描述..."
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                输入参数 (JSON)
              </label>
              <textarea
                value={JSON.stringify(data.config?.inputs || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const inputs = JSON.parse(e.target.value);
                    handleConfigChange('inputs', inputs);
                  } catch (err) {
                    // 忽略无效 JSON
                  }
                }}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs font-mono"
                rows="4"
                placeholder='{"param1": "value1"}'
              />
            </div>
            
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                超时时间 (秒)
              </label>
              <input
                type="number"
                value={data.config?.timeout || 30}
                onChange={(e) => handleConfigChange('timeout', parseInt(e.target.value))}
                className="w-full px-2 py-1 border border-gray-300 rounded text-xs"
                min="1"
                max="300"
              />
            </div>
          </div>
        </div>
      )}
      
      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-3 h-3 bg-green-500 border-2 border-white"
      />
    </div>
  );
};

export default ToolNode;
