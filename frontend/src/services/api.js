import axios from 'axios';
import toast from 'react-hot-toast';

// 创建 axios 实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
});

// 请求拦截器 - 添加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 统一处理错误
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期或无效
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      toast.error('登录已过期，请重新登录');
    } else if (error.response?.status === 403) {
      toast.error('权限不足');
    } else if (error.response?.status >= 500) {
      toast.error('服务器错误，请稍后重试');
    } else if (error.code === 'ECONNABORTED') {
      toast.error('请求超时，请检查网络连接');
    } else if (error.response?.data?.detail) {
      toast.error(error.response.data.detail);
    }
    
    return Promise.reject(error);
  }
);

// API 方法封装
const apiMethods = {
  // 认证相关
  auth: {
    login: (credentials) => api.post('/auth/token', credentials),
    register: (userData) => api.post('/auth/register', userData),
    getProfile: () => api.get('/auth/me'),
  },
  
  // 项目管理
  projects: {
    list: () => api.get('/projects'),
    get: (id) => api.get(`/projects/${id}`),
    create: (data) => api.post('/projects', data),
    update: (id, data) => api.put(`/projects/${id}`, data),
    delete: (id) => api.delete(`/projects/${id}`),
  },
  
  // 画布管理
  canvas: {
    listByProject: (projectId) => api.get(`/canvas/project/${projectId}`),
    get: (id) => api.get(`/canvas/${id}`),
    create: (data) => api.post('/canvas', data),
    update: (id, data) => api.put(`/canvas/${id}`, data),
    save: (id, data) => api.post(`/canvas/${id}/save`, data),
    delete: (id) => api.delete(`/canvas/${id}`),
  },
  
  // Agent 管理
  agents: {
    listConfigs: () => api.get('/agents/configs'),
    getConfig: (id) => api.get(`/agents/configs/${id}`),
    createConfig: (data) => api.post('/agents/configs', data),
    updateConfig: (id, data) => api.put(`/agents/configs/${id}`, data),
    listTools: () => api.get('/agents/tools'),
    createTool: (data) => api.post('/agents/tools', data),
  },
  
  // 知识库管理
  knowledge: {
    listBases: () => api.get('/knowledge/bases'),
    getBase: (id) => api.get(`/knowledge/bases/${id}`),
    createBase: (data) => api.post('/knowledge/bases', data),
    deleteBase: (id) => api.delete(`/knowledge/bases/${id}`),
    uploadFile: (kbId, file) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post(`/knowledge/bases/${kbId}/sources/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
    },
    search: (kbId, query, options = {}) => 
      api.post(`/knowledge/bases/${kbId}/search`, { query, ...options }),
  },
  
  // 工作流执行
  workflow: {
    execute: (data) => api.post('/workflow/execute', data),
    getStatus: (runId) => api.get(`/workflow/status/${runId}`),
    cancel: (runId) => api.post(`/workflow/cancel/${runId}`),
    listRuns: (params) => api.get('/workflow/runs', { params }),
  },
  
  // 通用方法
  get: (url, config) => api.get(url, config),
  post: (url, data, config) => api.post(url, data, config),
  put: (url, data, config) => api.put(url, data, config),
  delete: (url, config) => api.delete(url, config),
};

export default apiMethods;
