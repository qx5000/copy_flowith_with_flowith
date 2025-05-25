import React, { useState, useEffect } from 'react';
import { Search, Upload, FileText, Database, Trash2 } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

const KnowledgePanel = () => {
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKB, setSelectedKB] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  // 加载知识库列表
  useEffect(() => {
    loadKnowledgeBases();
  }, []);
  
  const loadKnowledgeBases = async () => {
    try {
      const response = await api.get('/knowledge/bases');
      setKnowledgeBases(response.data);
    } catch (error) {
      toast.error('加载知识库失败');
      console.error('Error loading knowledge bases:', error);
    }
  };
  
  const createKnowledgeBase = async () => {
    const name = prompt('请输入知识库名称:');
    if (!name) return;
    
    try {
      await api.post('/knowledge/bases', {
        name,
        description: `知识库: ${name}`,
        embedding_model: 'all-MiniLM-L6-v2',
        chunk_size: 1000,
        chunk_overlap: 200
      });
      
      toast.success('知识库创建成功');
      loadKnowledgeBases();
    } catch (error) {
      toast.error('创建知识库失败');
      console.error('Error creating knowledge base:', error);
    }
  };
  
  const uploadFile = async (file) => {
    if (!selectedKB) {
      toast.error('请先选择知识库');
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      await api.post(`/knowledge/bases/${selectedKB.id}/sources/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      toast.success('文件上传成功');
      // 刷新知识库信息
      loadKnowledgeBaseDetail(selectedKB.id);
    } catch (error) {
      toast.error('文件上传失败');
      console.error('Error uploading file:', error);
    } finally {
      setIsUploading(false);
    }
  };
  
  const loadKnowledgeBaseDetail = async (kbId) => {
    try {
      const response = await api.get(`/knowledge/bases/${kbId}`);
      const updatedKB = response.data;
      setSelectedKB(updatedKB);
      
      // 更新列表中的知识库信息
      setKnowledgeBases(kbs => 
        kbs.map(kb => kb.id === kbId ? updatedKB : kb)
      );
    } catch (error) {
      console.error('Error loading knowledge base detail:', error);
    }
  };
  
  const searchKnowledge = async () => {
    if (!selectedKB || !searchQuery.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await api.post(`/knowledge/bases/${selectedKB.id}/search`, {
        query: searchQuery,
        n_results: 5
      });
      
      setSearchResults(response.data.results);
    } catch (error) {
      toast.error('搜索失败');
      console.error('Error searching knowledge:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const allowedTypes = ['.pdf', '.txt', '.md', '.docx', '.doc'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExt)) {
        toast.error('不支持的文件类型');
        return;
      }
      
      if (file.size > 50 * 1024 * 1024) { // 50MB
        toast.error('文件大小不能超过 50MB');
        return;
      }
      
      uploadFile(file);
    }
  };
  
  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <Database className="w-5 h-5 mr-2 text-blue-600" />
            知识库
          </h3>
          <button
            onClick={createKnowledgeBase}
            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
          >
            新建
          </button>
        </div>
        
        {/* 知识库选择 */}
        <select
          value={selectedKB?.id || ''}
          onChange={(e) => {
            const kb = knowledgeBases.find(kb => kb.id === e.target.value);
            setSelectedKB(kb);
            if (kb) loadKnowledgeBaseDetail(kb.id);
          }}
          className="w-full p-2 border border-gray-300 rounded text-sm"
        >
          <option value="">选择知识库</option>
          {knowledgeBases.map((kb) => (
            <option key={kb.id} value={kb.id}>
              {kb.name} ({kb.source_count} 个文档)
            </option>
          ))}
        </select>
      </div>
      
      {selectedKB && (
        <>
          {/* 文件上传 */}
          <div className="p-4 border-b border-gray-200">
            <label className="block">
              <input
                type="file"
                onChange={handleFileUpload}
                accept=".pdf,.txt,.md,.docx,.doc"
                className="hidden"
                disabled={isUploading}
              />
              <div
                className={`
                  border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer
                  hover:border-blue-400 hover:bg-blue-50 transition-colors
                  ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <Upload className="w-6 h-6 mx-auto mb-2 text-gray-400" />
                <div className="text-sm text-gray-600">
                  {isUploading ? '上传中...' : '点击上传文件'}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  支持 PDF, TXT, MD, DOCX
                </div>
              </div>
            </label>
          </div>
          
          {/* 文档列表 */}
          <div className="p-4 border-b border-gray-200">
            <h4 className="text-sm font-medium text-gray-900 mb-2">文档列表</h4>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {selectedKB.sources?.map((source) => (
                <div
                  key={source.id}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded text-xs"
                >
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-gray-500" />
                    <span className="truncate max-w-[150px]">{source.name}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span className={`px-2 py-1 rounded ${
                      source.processing_status === 'completed' 
                        ? 'bg-green-100 text-green-700'
                        : source.processing_status === 'processing'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {source.processing_status === 'completed' ? '已完成' :
                       source.processing_status === 'processing' ? '处理中' : '失败'}
                    </span>
                    <span className="text-gray-500">({source.chunk_count} 块)</span>
                  </div>
                </div>
              )) || <div className="text-xs text-gray-500">暂无文档</div>}
            </div>
          </div>
          
          {/* 搜索 */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex space-x-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索知识库..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm"
                onKeyPress={(e) => e.key === 'Enter' && searchKnowledge()}
              />
              <button
                onClick={searchKnowledge}
                disabled={isLoading || !searchQuery.trim()}
                className="px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Search className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* 搜索结果 */}
          <div className="flex-1 overflow-y-auto p-4">
            {isLoading ? (
              <div className="text-center text-sm text-gray-500">搜索中...</div>
            ) : searchResults.length > 0 ? (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-900">搜索结果</h4>
                {searchResults.map((result, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-50 rounded-lg border border-gray-200"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="text-xs text-gray-500">
                        {result.source_name} - 第 {result.rank} 位
                      </div>
                      <div className="text-xs text-green-600">
                        相似度: {(result.similarity * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="text-sm text-gray-800 leading-relaxed">
                      {result.document.length > 200 
                        ? `${result.document.slice(0, 200)}...`
                        : result.document
                      }
                    </div>
                  </div>
                ))}
              </div>
            ) : searchQuery && !isLoading ? (
              <div className="text-center text-sm text-gray-500">未找到相关内容</div>
            ) : null}
          </div>
        </>
      )}
      
      {!selectedKB && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <Database className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <div className="text-sm">请选择或创建知识库</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgePanel;
