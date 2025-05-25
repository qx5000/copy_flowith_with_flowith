import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import api from '../services/api';
import toast from 'react-hot-toast';

const useCanvasStore = create(
  devtools(
    (set, get) => ({
      // 状态
      nodes: [],
      edges: [],
      selectedNodes: [],
      selectedEdges: [],
      canvasData: null,
      isLoading: false,
      isSaving: false,
      
      // 画布操作
      setNodes: (nodes) => set({ nodes }),
      setEdges: (edges) => set({ edges }),
      
      addNode: (node) => set((state) => ({
        nodes: [...state.nodes, node]
      })),
      
      deleteNode: (nodeId) => set((state) => ({
        nodes: state.nodes.filter(n => n.id !== nodeId),
        edges: state.edges.filter(e => e.source !== nodeId && e.target !== nodeId)
      })),
      
      updateNodeData: (nodeId, newData) => set((state) => ({
        nodes: state.nodes.map(node => 
          node.id === nodeId ? { ...node, data: newData } : node
        )
      })),
      
      addEdge: (edge) => set((state) => ({
        edges: [...state.edges, edge]
      })),
      
      deleteEdge: (edgeId) => set((state) => ({
        edges: state.edges.filter(e => e.id !== edgeId)
      })),
      
      // 选择操作
      setSelectedNodes: (nodeIds) => set({ selectedNodes: nodeIds }),
      setSelectedEdges: (edgeIds) => set({ selectedEdges: edgeIds }),
      
      selectNode: (nodeId) => set((state) => ({
        selectedNodes: [...state.selectedNodes, nodeId]
      })),
      
      deselectNode: (nodeId) => set((state) => ({
        selectedNodes: state.selectedNodes.filter(id => id !== nodeId)
      })),
      
      clearSelection: () => set({
        selectedNodes: [],
        selectedEdges: []
      }),
      
      // 画布数据管理
      loadCanvas: async (canvasId) => {
        set({ isLoading: true });
        try {
          const response = await api.canvas.get(canvasId);
          const canvasData = response.data;
          
          set({
            nodes: canvasData.canvas_data?.nodes || [],
            edges: canvasData.canvas_data?.edges || [],
            canvasData,
            isLoading: false
          });
          
          return canvasData;
        } catch (error) {
          set({ isLoading: false });
          toast.error('加载画布失败');
          throw error;
        }
      },
      
      saveCanvas: async (canvasId, data = null) => {
        const { nodes, edges } = get();
        const canvasData = data || { nodes, edges };
        
        set({ isSaving: true });
        try {
          await api.canvas.save(canvasId, canvasData);
          set({ isSaving: false });
          return true;
        } catch (error) {
          set({ isSaving: false });
          toast.error('保存画布失败');
          throw error;
        }
      },
      
      createCanvas: async (projectId, name, description = '') => {
        set({ isLoading: true });
        try {
          const response = await api.canvas.create({
            project_id: projectId,
            name,
            description,
            canvas_data: { nodes: [], edges: [] }
          });
          
          set({ 
            isLoading: false,
            nodes: [],
            edges: [],
            canvasData: response.data
          });
          
          toast.success('画布创建成功');
          return response.data;
        } catch (error) {
          set({ isLoading: false });
          toast.error('创建画布失败');
          throw error;
        }
      },
      
      // 画布操作
      clearCanvas: () => set({
        nodes: [],
        edges: [],
        selectedNodes: [],
        selectedEdges: []
      }),
      
      resetCanvas: () => set({
        nodes: [],
        edges: [],
        selectedNodes: [],
        selectedEdges: [],
        canvasData: null
      }),
      
      // 导入导出
      exportCanvas: () => {
        const { nodes, edges, canvasData } = get();
        const exportData = {
          metadata: {
            name: canvasData?.name || 'Untitled Canvas',
            exportTime: new Date().toISOString(),
            version: '1.0.0'
          },
          canvas: { nodes, edges }
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
          type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${exportData.metadata.name}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        toast.success('画布导出成功');
      },
      
      importCanvas: (file) => {
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (event) => {
            try {
              const importData = JSON.parse(event.target.result);
              
              if (importData.canvas && importData.canvas.nodes) {
                set({
                  nodes: importData.canvas.nodes,
                  edges: importData.canvas.edges || [],
                  selectedNodes: [],
                  selectedEdges: []
                });
                
                toast.success('画布导入成功');
                resolve(importData);
              } else {
                throw new Error('无效的画布文件格式');
              }
            } catch (error) {
              toast.error('导入失败: ' + error.message);
              reject(error);
            }
          };
          reader.readAsText(file);
        });
      },
      
      // 撤销重做功能 (简化版本)
      history: [],
      historyIndex: -1,
      
      saveToHistory: () => {
        const { nodes, edges, history, historyIndex } = get();
        const snapshot = { nodes: [...nodes], edges: [...edges] };
        
        // 移除当前位置之后的历史
        const newHistory = history.slice(0, historyIndex + 1);
        newHistory.push(snapshot);
        
        // 限制历史记录数量
        const maxHistory = 50;
        if (newHistory.length > maxHistory) {
          newHistory.shift();
        }
        
        set({
          history: newHistory,
          historyIndex: newHistory.length - 1
        });
      },
      
      undo: () => {
        const { history, historyIndex } = get();
        if (historyIndex > 0) {
          const snapshot = history[historyIndex - 1];
          set({
            nodes: [...snapshot.nodes],
            edges: [...snapshot.edges],
            historyIndex: historyIndex - 1
          });
        }
      },
      
      redo: () => {
        const { history, historyIndex } = get();
        if (historyIndex < history.length - 1) {
          const snapshot = history[historyIndex + 1];
          set({
            nodes: [...snapshot.nodes],
            edges: [...snapshot.edges],
            historyIndex: historyIndex + 1
          });
        }
      },
      
      // 画布统计信息
      getStats: () => {
        const { nodes, edges } = get();
        const agentNodes = nodes.filter(n => n.type === 'agent');
        const toolNodes = nodes.filter(n => n.type === 'tool');
        
        return {
          totalNodes: nodes.length,
          totalEdges: edges.length,
          agentCount: agentNodes.length,
          toolCount: toolNodes.length,
        };
      },
    }),
    {
      name: 'canvas-store',
    }
  )
);

export { useCanvasStore };
export default useCanvasStore;
