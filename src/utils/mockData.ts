import { FileItem, ModelItem, VectorItem, MetadataItem } from "./types";

export const fileData: FileItem[] = [
    { id: 1, name: '城市规划白皮书.pdf', type: 'pdf', size: '2.4MB', date: '2025-03-15', status: '已向量化', category: '政策文档' },
    { id: 2, name: '政策解读手册.docx', type: 'docx', size: '1.8MB', date: '2025-03-14', status: '已向量化', category: '政策文档' },
    { id: 3, name: '经济发展数据报告.xlsx', type: 'xlsx', size: '4.2MB', date: '2025-03-10', status: '处理中', category: '数据分析' },
    { id: 4, name: '智慧城市建设方案.pptx', type: 'pptx', size: '5.6MB', date: '2025-03-05', status: '已向量化', category: '方案规划' },
    { id: 5, name: '政务AI研究论文.pdf', type: 'pdf', size: '3.7MB', date: '2025-02-28', status: '未处理', category: '研究资料' }
];


export const modelData: ModelItem[] = [
    { id: 1, name: 'OpenAI-GPT-4', type: 'LLM', status: '已连接', lastUsed: '2025-03-16', provider: 'OpenAI', version: '4.0', usageCount: 145 },
    { id: 2, name: 'Claude-3', type: 'LLM', status: '已连接', lastUsed: '2025-03-15', provider: 'Anthropic', version: '3.0', usageCount: 87 },
    { id: 3, name: 'Embedding-v3', type: '嵌入模型', status: '已连接', lastUsed: '2025-03-16', provider: 'OpenAI', version: '3.0', usageCount: 230 },
    { id: 4, name: 'BERT-Chinese', type: '嵌入模型', status: '未连接', lastUsed: '2025-03-01', provider: 'Hugging Face', version: '1.2', usageCount: 42 }
];


export const vectorData: VectorItem[] = [
    { id: 1, name: '政策文档向量库', fileCount: 126, lastUpdated: '2025-03-16', size: '458MB', status: '活跃' },
    { id: 2, name: '法规条例向量库', fileCount: 84, lastUpdated: '2025-03-14', size: '312MB', status: '活跃' },
    { id: 3, name: '历史会议记录', fileCount: 53, lastUpdated: '2025-03-10', size: '215MB', status: '活跃' },
    { id: 4, name: '经济数据分析', fileCount: 37, lastUpdated: '2025-03-05', size: '178MB', status: '维护中' }
];


export const metadataTemplates: MetadataItem[] = [
    { id: 1, name: '政策文档模板', fields: 12, lastUpdated: '2025-03-15', usage: '广泛使用' },
    { id: 2, name: '会议记录模板', fields: 8, lastUpdated: '2025-03-10', usage: '部分使用' },
    { id: 3, name: '法规标准模板', fields: 15, lastUpdated: '2025-03-05', usage: '广泛使用' },
    { id: 4, name: '研究报告模板', fields: 10, lastUpdated: '2025-02-28', usage: '部分使用' }
];

export const navigationItems = [
    { id: 'files', label: '文件管理', iconType: 'FileText' },
    { id: 'models', label: '模型管理', iconType: 'Code' },
    { id: 'vectors', label: '向量化管理', iconType: 'Grid' },
    { id: 'metadata', label: '元数据管理', iconType: 'Database' },
    { id: 'settings', label: '系统设置', iconType: 'Settings' }
];