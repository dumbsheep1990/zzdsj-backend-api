import React, { useState, useEffect } from 'react';
import { KeywordItem, FileItem } from '../utils/types';
import KeywordsManager from '../components/modules/keywords/KeywordsManager';
import { keywordsData } from '../utils/mockData';
import { Info, Tag, BarChart2 } from 'lucide-react';

const Keywords: React.FC = () => {
  // 这里添加了对 KeywordsManager 组件更新的监听，用于更新相关信息
  const [selectedKeyword, setSelectedKeyword] = useState<KeywordItem | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  
  // 按重要性统计关键词数量
  const keywordStats = {
    high: keywordsData.filter(k => k.importance === 'high').length,
    medium: keywordsData.filter(k => k.importance === 'medium').length,
    low: keywordsData.filter(k => k.importance === 'low').length,
    total: keywordsData.length
  };

  // 当选择的关键词发生变化时的效果
  useEffect(() => {
    if (selectedKeyword) {
      console.log(`选择了关键词: ${selectedKeyword.keyword}`);
      // 将来可以在这里添加更新相关信息的代码，如更新关键词相关的统计信息
    }
  }, [selectedKeyword]);

  // 当选择的文件发生变化时的效果
  useEffect(() => {
    if (selectedFile) {
      console.log(`选择了文件: ${selectedFile.name}`);
      // 将来可以在这里添加更新相关信息的代码，如更新文件相关的统计信息
    }
  }, [selectedFile]);

  return (
    <div className="keywords-page">
      <div className="page-header flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold">关键词管理</h1>
          <p className="text-gray-600">管理文件关键词和关联关系</p>
        </div>
        <div className="stats-cards flex space-x-4">
          <div className="stat-card bg-gradient-to-r from-red-50 to-red-100 p-4 rounded-lg shadow-sm">
            <div className="flex items-center">
              <Tag className="text-red-500 mr-2" size={20} />
              <span className="text-sm font-medium text-gray-700">高重要度关键词</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-800">{keywordStats.high}</div>
          </div>
          <div className="stat-card bg-gradient-to-r from-yellow-50 to-yellow-100 p-4 rounded-lg shadow-sm">
            <div className="flex items-center">
              <Tag className="text-yellow-500 mr-2" size={20} />
              <span className="text-sm font-medium text-gray-700">中重要度关键词</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-800">{keywordStats.medium}</div>
          </div>
          <div className="stat-card bg-gradient-to-r from-green-50 to-green-100 p-4 rounded-lg shadow-sm">
            <div className="flex items-center">
              <Tag className="text-green-500 mr-2" size={20} />
              <span className="text-sm font-medium text-gray-700">低重要度关键词</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-800">{keywordStats.low}</div>
          </div>
          <div className="stat-card bg-gradient-to-r from-blue-50 to-blue-100 p-4 rounded-lg shadow-sm">
            <div className="flex items-center">
              <BarChart2 className="text-blue-500 mr-2" size={20} />
              <span className="text-sm font-medium text-gray-700">总关键词数</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-800">{keywordStats.total}</div>
          </div>
        </div>
      </div>

      <div className="info-banner bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded-r-md">
        <div className="flex items-start">
          <Info className="text-blue-500 mr-2 flex-shrink-0 mt-1" size={20} />
          <div>
            <h3 className="font-medium text-blue-800">关键词知识图谱</h3>
            <p className="text-blue-600 text-sm">
              通过知识图谱可视化关键词之间的关联关系和文件关联度。点击节点可查看详细信息，拖拽节点可调整图谱布局。
            </p>
          </div>
        </div>
      </div>

      <KeywordsManager 
        onSelectKeyword={setSelectedKeyword} 
        onSelectFile={setSelectedFile} 
      />
    </div>
  );
};

export default Keywords;
