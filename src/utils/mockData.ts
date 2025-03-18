import { FileItem, ModelItem, VectorItem, MetadataItem, KeywordItem, SearchRecordItem, KeywordRelevance } from "./types";

export const fileData: FileItem[] = [
    { 
        id: 1, 
        name: '城市规划白皮书.pdf', 
        type: 'pdf', 
        size: '2.4MB', 
        date: '2025-03-15', 
        status: '已向量化', 
        category: '政策文档',
        keywords: [
            { keywordId: 1, keyword: '智慧城市建设', relevance: 92 },
            { keywordId: 6, keyword: '城市规划', relevance: 88 },
            { keywordId: 2, keyword: '数字经济发展', relevance: 65 }
        ]
    },
    { 
        id: 2, 
        name: '政策解读手册.docx', 
        type: 'docx', 
        size: '1.8MB', 
        date: '2025-03-14', 
        status: '已向量化', 
        category: '政策文档',
        keywords: [
            { keywordId: 3, keyword: '政策解读', relevance: 95 },
            { keywordId: 7, keyword: '法规标准', relevance: 72 },
            { keywordId: 5, keyword: '人工智能', relevance: 45 }
        ]
    },
    { 
        id: 3, 
        name: '经济发展数据报告.xlsx', 
        type: 'xlsx', 
        size: '4.2MB', 
        date: '2025-03-10', 
        status: '处理中', 
        category: '数据分析',
        keywords: [
            { keywordId: 2, keyword: '数字经济发展', relevance: 90 },
            { keywordId: 4, keyword: '数据分析', relevance: 85 },
            { keywordId: 5, keyword: '人工智能', relevance: 60 }
        ]
    },
    { 
        id: 4, 
        name: '智慧城市建设方案.pptx', 
        type: 'pptx', 
        size: '5.6MB', 
        date: '2025-03-05', 
        status: '已向量化', 
        category: '方案规划',
        keywords: [
            { keywordId: 1, keyword: '智慧城市建设', relevance: 98 },
            { keywordId: 6, keyword: '城市规划', relevance: 85 },
            { keywordId: 5, keyword: '人工智能', relevance: 75 }
        ]
    },
    { 
        id: 5, 
        name: '政务AI研究论文.pdf', 
        type: 'pdf', 
        size: '3.7MB', 
        date: '2025-02-28', 
        status: '未处理', 
        category: '研究资料',
        keywords: [
            { keywordId: 5, keyword: '人工智能', relevance: 96 },
            { keywordId: 1, keyword: '智慧城市建设', relevance: 62 },
            { keywordId: 3, keyword: '政策解读', relevance: 45 }
        ]
    }
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

export const keywordsData: KeywordItem[] = [
    { 
        id: 1, 
        keyword: '智慧城市建设', 
        frequency: 156, 
        lastUsed: '2025-03-16', 
        category: '城市建设方案', 
        importance: 'high',
        relatedKeywords: [6, 2, 5]
    },
    { 
        id: 2, 
        keyword: '数字经济发展', 
        frequency: 124, 
        lastUsed: '2025-03-15', 
        category: '经济发展数据', 
        importance: 'high',
        relatedKeywords: [1, 4, 5]
    },
    { 
        id: 3, 
        keyword: '政策解读', 
        frequency: 98, 
        lastUsed: '2025-03-14', 
        category: '政策文档', 
        importance: 'medium',
        relatedKeywords: [7, 5]
    },
    { 
        id: 4, 
        keyword: '数据分析', 
        frequency: 87, 
        lastUsed: '2025-03-12', 
        category: '数据分析', 
        importance: 'medium',
        relatedKeywords: [2, 5]
    },
    { 
        id: 5, 
        keyword: '人工智能', 
        frequency: 76, 
        lastUsed: '2025-03-10', 
        category: '人工智能研究', 
        importance: 'medium',
        relatedKeywords: [1, 2, 3, 4]
    },
    { 
        id: 6, 
        keyword: '城市规划', 
        frequency: 65, 
        lastUsed: '2025-03-08', 
        category: '城市规划方案', 
        importance: 'high',
        relatedKeywords: [1]
    },
    { 
        id: 7, 
        keyword: '法规标准', 
        frequency: 54, 
        lastUsed: '2025-03-05', 
        category: '法规标准', 
        importance: 'low',
        relatedKeywords: [3]
    },
    { 
        id: 8, 
        keyword: '历史会议', 
        frequency: 43, 
        lastUsed: '2025-03-02', 
        category: '历史会议记录', 
        importance: 'low',
        relatedKeywords: []
    }
];

export const searchRecordsData: SearchRecordItem[] = [
    { id: 1, query: '智慧城市建设方案', timestamp: '2025-03-16 15:30:22', results: 24, duration: '0.8s', user: '管理员', source: 'Web界面' },
    { id: 2, query: '数字经济发展数据', timestamp: '2025-03-16 14:15:47', results: 18, duration: '0.6s', user: '管理员', source: 'Web界面' },
    { id: 3, query: '城市规划白皮书', timestamp: '2025-03-15 16:42:33', results: 15, duration: '0.7s', user: '用户1', source: 'API' },
    { id: 4, query: '政策解读手册', timestamp: '2025-03-15 11:20:15', results: 32, duration: '1.2s', user: '用户2', source: 'Web界面' },
    { id: 5, query: '历史会议记录', timestamp: '2025-03-14 09:45:38', results: 12, duration: '0.5s', user: '用户3', source: 'API' },
    { id: 6, query: '法规标准', timestamp: '2025-03-14 08:30:12', results: 9, duration: '0.4s', user: '管理员', source: 'Web界面' },
    { id: 7, query: '数据分析报告', timestamp: '2025-03-13 16:15:27', results: 21, duration: '0.9s', user: '用户4', source: 'API' },
    { id: 8, query: '人工智能研究', timestamp: '2025-03-13 14:50:55', results: 16, duration: '0.7s', user: '用户5', source: 'Web界面' }
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

// 生成知识图谱数据的辅助函数
export const generateKnowledgeGraphData = () => {
    const nodes = [];
    const links = [];
    
    // 添加关键词节点
    keywordsData.forEach(keyword => {
        nodes.push({
            id: `keyword-${keyword.id}`,
            label: keyword.keyword,
            type: 'keyword',
            value: keyword.frequency / 10, // 节点大小基于频率
            color: keyword.importance === 'high' ? '#ef4444' : 
                   keyword.importance === 'medium' ? '#f59e0b' : '#10b981'
        });
        
        // 添加关键词之间的关联
        if (keyword.relatedKeywords) {
            keyword.relatedKeywords.forEach(relatedId => {
                links.push({
                    source: `keyword-${keyword.id}`,
                    target: `keyword-${relatedId}`,
                    value: 2 // 关键词之间的关联强度
                });
            });
        }
    });
    
    // 添加文件节点
    fileData.forEach(file => {
        nodes.push({
            id: `file-${file.id}`,
            label: file.name,
            type: 'file',
            value: 3, // 文件节点大小固定
            color: '#3b82f6'
        });
        
        // 添加文件与关键词的关联
        if (file.keywords) {
            file.keywords.forEach(keywordRel => {
                links.push({
                    source: `file-${file.id}`,
                    target: `keyword-${keywordRel.keywordId}`,
                    value: keywordRel.relevance / 25 // 关联强度基于相关性
                });
            });
        }
    });
    
    return { nodes, links };
};