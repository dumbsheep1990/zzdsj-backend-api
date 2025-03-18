import React, { useState, useEffect } from 'react';
import { Plus, Search, X } from 'lucide-react';
import { FileItem, ModelItem, VectorItem, MetadataItem, KeywordItem, SearchRecordItem } from '../../../utils/types';
import KnowledgeGraph from './KnowledgeGraph';

interface KeywordsManagerProps {
  selectedItem?: FileItem | ModelItem | VectorItem | MetadataItem | KeywordItem | SearchRecordItem | null;
  compact?: boolean;
  onSelectKeyword?: (keyword: KeywordItem | null) => void;
  onSelectFile?: (file: FileItem | null) => void;
}

const KeywordsManager: React.FC<KeywordsManagerProps> = ({ 
  selectedItem, 
  compact = false, 
  onSelectKeyword, 
  onSelectFile 
}) => {
  const [keywords, setKeywords] = useState<KeywordItem[]>([
    { id: 1, keyword: '人工智能', frequency: 120, lastUsed: '2023-05-15', category: '技术', importance: 'high' },
    { id: 2, keyword: '机器学习', frequency: 95, lastUsed: '2023-05-10', category: '技术', importance: 'high', relatedKeywords: [1, 3] },
    { id: 3, keyword: '深度学习', frequency: 78, lastUsed: '2023-05-08', category: '技术', importance: 'medium', relatedKeywords: [1, 2] },
    { id: 4, keyword: '自然语言处理', frequency: 65, lastUsed: '2023-05-05', category: '技术', importance: 'medium', relatedKeywords: [1, 3] },
    { id: 5, keyword: '计算机视觉', frequency: 50, lastUsed: '2023-05-01', category: '技术', importance: 'medium', relatedKeywords: [1] },
    { id: 6, keyword: '神经网络', frequency: 45, lastUsed: '2023-04-28', category: '技术', importance: 'medium', relatedKeywords: [1, 3, 5] },
    { id: 7, keyword: '大数据', frequency: 40, lastUsed: '2023-04-25', category: '技术', importance: 'low', relatedKeywords: [1] },
    { id: 8, keyword: '云计算', frequency: 35, lastUsed: '2023-04-20', category: '技术', importance: 'low' },
    { id: 9, keyword: '区块链', frequency: 30, lastUsed: '2023-04-15', category: '技术', importance: 'low' },
    { id: 10, keyword: '物联网', frequency: 25, lastUsed: '2023-04-10', category: '技术', importance: 'low', relatedKeywords: [7, 8] },
  ]);

  const [relatedFiles, setRelatedFiles] = useState<FileItem[]>([
    { id: 1, name: 'AI研究报告.pdf', type: 'file', size: '2500000', date: '2023-05-15', status: 'active', category: '文档' },
    { id: 2, name: '机器学习算法.py', type: 'file', size: '15000', date: '2023-05-10', status: 'active', category: '代码' },
    { id: 3, name: '深度学习模型.h5', type: 'file', size: '75000000', date: '2023-05-08', status: 'active', category: '模型' },
    { id: 4, name: 'NLP项目说明.docx', type: 'file', size: '1800000', date: '2023-05-05', status: 'active', category: '文档' },
  ]);

  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [selectedKeyword, setSelectedKeyword] = useState<KeywordItem | null>(null);
  const [showGraph, setShowGraph] = useState(false);

  // 过滤关键词
  const filteredKeywords = keywords.filter((keyword: KeywordItem) => 
    keyword.keyword.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // 添加新关键词
  const handleAddKeyword = () => {
    if (newKeyword.trim() === '') return;
    
    const newKeywordItem: KeywordItem = {
      id: keywords.length + 1,
      keyword: newKeyword,
      frequency: 1,
      lastUsed: new Date().toISOString().split('T')[0],
      category: '未分类',
      importance: 'low'
    };
    
    setKeywords([...keywords, newKeywordItem]);
    setNewKeyword('');
    setShowAddModal(false);
  };

  // 选择关键词
  const handleSelectKeyword = (keyword: KeywordItem) => {
    setSelectedKeyword(keyword);
    
    // 如果有外部回调函数，则调用
    if (onSelectKeyword) {
      onSelectKeyword(keyword);
    }
    
    // 模拟获取相关文件
    // 实际应用中，这里应该是一个API调用
    setRelatedFiles(relatedFiles.slice(0, Math.floor(Math.random() * 5)));
  };

  // 选择文件
  const handleSelectFile = (file: FileItem) => {
    if (onSelectFile) {
      onSelectFile(file);
    }
  };

  // 根据compact属性调整布局
  const containerClassName = compact 
    ? "keywords-manager grid grid-cols-1 gap-2" 
    : "keywords-manager grid grid-cols-1 lg:grid-cols-3 gap-6";

  const keywordsListClassName = compact 
    ? "keywords-list col-span-1 bg-white p-3 max-h-[180px] overflow-y-auto" 
    : "keywords-list col-span-1 bg-white rounded-lg shadow-md p-4";

  const relatedFilesClassName = compact 
    ? "related-files col-span-1 bg-white p-3 max-h-[180px] overflow-y-auto" 
    : "related-files col-span-1 bg-white rounded-lg shadow-md p-4";

  const graphContainerClassName = compact 
    ? "knowledge-graph col-span-1 bg-white p-3 h-[220px]" 
    : "knowledge-graph col-span-1 lg:col-span-3 bg-white rounded-lg shadow-md p-4 h-[400px]";

  // 如果有选中的项目，并且是文件类型，则初始化相关关键词
  useEffect(() => {
    if (selectedItem && 'type' in selectedItem && selectedItem.type === 'file' && 'keywords' in selectedItem) {
      // 如果文件有关键词，则选择第一个关键词
      if (selectedItem.keywords && selectedItem.keywords.length > 0) {
        const keywordId = selectedItem.keywords[0].keywordId;
        const foundKeyword = keywords.find(k => k.id === keywordId);
        if (foundKeyword) {
          setSelectedKeyword(foundKeyword);
        }
      }
    }
  }, [selectedItem, keywords]);

  return (
    <div className={containerClassName}>
      {/* 关键词列表 */}
      <div className={keywordsListClassName}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">关键词管理</h3>
          <button onClick={() => setShowAddModal(true)} className="p-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition-colors">
            <Plus size={16} />
          </button>
        </div>
        
        <div className="search-bar relative mb-4">
          <input
            type="text"
            placeholder="搜索关键词..."
            className="w-full p-2 pl-8 border rounded-md"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Search size={16} className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-400" />
        </div>
        
        <div className="keywords-list-items space-y-2">
          {filteredKeywords.map((keyword: KeywordItem) => (
            <div 
              key={keyword.id} 
              className={`keyword-item p-2 rounded-md cursor-pointer hover:bg-gray-100 flex justify-between items-center ${selectedKeyword?.id === keyword.id ? 'bg-blue-50 border border-blue-200' : ''}`}
              onClick={() => handleSelectKeyword(keyword)}
            >
              <div>
                <span className="font-medium">{keyword.keyword}</span>
                <div className="text-xs text-gray-500">
                  <span>频率: {keyword.frequency}</span>
                  <span className="ml-2">类别: {keyword.category}</span>
                </div>
              </div>
              <div className={`importance-indicator w-3 h-3 rounded-full ${keyword.importance === 'high' ? 'bg-red-500' : keyword.importance === 'medium' ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            </div>
          ))}
          
          {filteredKeywords.length === 0 && (
            <div className="text-center text-gray-500 py-4">
              没有找到匹配的关键词
            </div>
          )}
        </div>
      </div>

      {/* 相关文件 */}
      {selectedKeyword && (
        <div className={relatedFilesClassName}>
          <h3 className="text-lg font-semibold mb-4">相关文件</h3>
          
          {relatedFiles.length > 0 ? (
            <div className="related-files-list space-y-2">
              {relatedFiles.map(file => (
                <div 
                  key={file.id} 
                  className="file-item p-2 rounded-md hover:bg-gray-100"
                  onClick={() => handleSelectFile(file)}
                >
                  <div className="flex items-center">
                    <div className="file-icon mr-2">
                      {file.type === 'file' && <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-500">F</div>}
                    </div>
                    <div className="file-info">
                      <div className="font-medium">{file.name}</div>
                      <div className="text-xs text-gray-500">
                        <span>{file.category}</span>
                        <span className="ml-2">{file.date}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-gray-500 py-4">
              没有相关文件
            </div>
          )}
          
          <div className="mt-4 flex justify-end">
            <button 
              className="text-sm text-blue-500 hover:text-blue-700"
              onClick={() => setShowGraph(!showGraph)}
            >
              {showGraph ? '隐藏知识图谱' : '显示知识图谱'}
            </button>
          </div>
        </div>
      )}

      {/* 知识图谱 */}
      {showGraph && (
        <div className={graphContainerClassName}>
          <h3 className="text-lg font-semibold mb-2">知识图谱</h3>
          <KnowledgeGraph 
            width={compact ? 300 : 800} 
            height={compact ? 250 : 350} 
            selectedKeywordId={selectedKeyword?.id}
            onNodeClick={(node) => {
              if (node.type === 'keyword') {
                const keyword = keywords.find(k => k.id === parseInt(node.id));
                if (keyword) {
                  handleSelectKeyword(keyword);
                }
              } else if (node.type === 'file') {
                const file = relatedFiles.find(f => f.id === parseInt(node.id));
                if (file) {
                  handleSelectFile(file);
                }
              }
            }}
          />
        </div>
      )}

      {/* 添加关键词模态框 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">添加新关键词</h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-500 hover:text-gray-700">
                <X size={20} />
              </button>
            </div>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">关键词</label>
              <input
                type="text"
                className="w-full p-2 border rounded-md"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                placeholder="输入新关键词..."
              />
            </div>
            
            <div className="flex justify-end">
              <button 
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md mr-2 hover:bg-gray-300"
                onClick={() => setShowAddModal(false)}
              >
                取消
              </button>
              <button 
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                onClick={handleAddKeyword}
              >
                添加
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KeywordsManager;
