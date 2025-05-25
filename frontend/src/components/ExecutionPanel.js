import React, { useState, useEffect } from 'react';
import { Play, Pause, Square, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

const ExecutionPanel = ({ canvasId, canvasData }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionHistory, setExecutionHistory] = useState([]);
  const [currentExecution, setCurrentExecution] = useState(null);
  const [executionLogs, setExecutionLogs] = useState([]);
  
  // 加载执行历史
  useEffect(() => {
    if (canvasId) {
      loadExecutionHistory();
    }
  }, [canvasId]);
  
  // WebSocket 连接用于实时日志
  useEffect(() => {
    if (currentExecution) {
      const ws = new WebSocket(`ws://localhost:8000/ws/execution_${currentExecution.run_id}`);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'log') {
          setExecutionLogs(logs => [...logs, data]);
        } else if (data.type === 'status_update') {
          setCurrentExecution(exec => ({
            ...exec,
            status: data.status
          }));
          
          if (data.status === 'completed' || data.status === 'failed') {
            setIsExecuting(false);
            loadExecutionHistory();
          }
        }
      };
      
      return () => ws.close();
    }
  }, [currentExecution]);
  
  const loadExecutionHistory = async () => {
    try {
      const response = await api.get(`/workflow/runs?canvas_id=${canvasId}`);
      setExecutionHistory(response.data);
    } catch (error) {
      console.error('Error loading execution history:', error);
    }
  };
  
  const startExecution = async () => {
    if (!canvasData || !canvasData.nodes || canvasData.nodes.length === 0) {
      toast.error('画布为空，无法执行');
      return;
    }
    
    setIsExecuting(true);
    setExecutionLogs([]);
    
    try {
      const response = await api.post('/workflow/execute', {
        canvas_id: canvasId,
        canvas_data: canvasData,
        workflow_id: `workflow_${Date.now()}`
      });
      
      setCurrentExecution({
        run_id: response.data.run_id,
        status: 'running',
        started_at: new Date().toISOString()
      });
      
      toast.success('工作流开始执行');
    } catch (error) {
      setIsExecuting(false);
      toast.error('执行失败: ' + (error.response?.data?.error || error.message));
    }
  };
  
  const stopExecution = async () => {
    if (currentExecution) {
      try {
        await api.post(`/workflow/cancel/${currentExecution.run_id}`);
        setIsExecuting(false);
        setCurrentExecution(null);
        toast.success('执行已停止');
      } catch (error) {
        toast.error('停止执行失败');
      }
    }
  };
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <Play className="w-4 h-4 text-blue-600 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'cancelled':
        return <Square className="w-4 h-4 text-yellow-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };
  
  const getStatusText = (status) => {
    const statusMap = {
      'pending': '等待中',
      'running': '运行中',
      'completed': '已完成',
      'failed': '执行失败',
      'cancelled': '已取消'
    };
    return statusMap[status] || status;
  };
  
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN');
  };
  
  const formatDuration = (seconds) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}秒`;
    } else if (seconds < 3600) {
      return `${(seconds / 60).toFixed(1)}分钟`;
    } else {
      return `${(seconds / 3600).toFixed(1)}小时`;
    }
  };
  
  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      {/* 头部控制 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">执行控制</h3>
          <div className="flex space-x-2">
            {!isExecuting ? (
              <button
                onClick={startExecution}
                className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Play className="w-4 h-4" />
                <span>执行</span>
              </button>
            ) : (
              <button
                onClick={stopExecution}
                className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                <Square className="w-4 h-4" />
                <span>停止</span>
              </button>
            )}
          </div>
        </div>
        
        {/* 当前执行状态 */}
        {currentExecution && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                {getStatusIcon(currentExecution.status)}
                <span className="text-sm font-medium">
                  {getStatusText(currentExecution.status)}
                </span>
              </div>
              <span className="text-xs text-gray-500">
                开始于 {formatTime(currentExecution.started_at)}
              </span>
            </div>
            <div className="text-xs text-gray-600">
              执行 ID: {currentExecution.run_id}
            </div>
          </div>
        )}
      </div>
      
      {/* 实时日志 */}
      {isExecuting && (
        <div className="border-b border-gray-200">
          <div className="p-3 bg-gray-50">
            <div className="flex items-center space-x-2 mb-2">
              <AlertCircle className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium">实时日志</span>
            </div>
            <div className="bg-black text-green-400 p-3 rounded text-xs font-mono h-32 overflow-y-auto">
              {executionLogs.map((log, index) => (
                <div key={index} className="mb-1">
                  <span className="text-gray-500">[{formatTime(log.timestamp)}]</span> {log.message}
                </div>
              ))}
              {executionLogs.length === 0 && (
                <div className="text-gray-500">等待日志输出...</div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* 执行历史 */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">执行历史</h4>
          
          {executionHistory.length > 0 ? (
            <div className="space-y-3">
              {executionHistory.map((execution) => (
                <div
                  key={execution.id}
                  className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(execution.status)}
                      <span className="text-sm font-medium">
                        {getStatusText(execution.status)}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatTime(execution.started_at)}
                    </span>
                  </div>
                  
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>执行 ID: {execution.id}</div>
                    {execution.execution_time && (
                      <div>
                        执行时间: {formatDuration(execution.execution_time)}
                      </div>
                    )}
                    {execution.error_message && (
                      <div className="text-red-600 bg-red-50 p-2 rounded">
                        错误: {execution.error_message}
                      </div>
                    )}
                  </div>
                  
                  {execution.output_data && (
                    <div className="mt-2">
                      <details className="text-xs">
                        <summary className="cursor-pointer text-blue-600 hover:text-blue-800">
                          查看结果详情
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-100 rounded overflow-x-auto">
                          {JSON.stringify(execution.output_data, null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-sm text-gray-500 py-8">
              <Clock className="w-8 h-8 mx-auto mb-2 text-gray-300" />
              <div>暂无执行记录</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExecutionPanel;
