import React, { useState } from 'react';
import { File, Folder, X, Info, Tag, Cpu } from 'lucide-react';
import { FileItem, ModelItem, VectorItem, MetadataItem, KeywordItem, SearchRecordItem } from '../../utils/types';

// 移动到本地的帮助函数
const formatDate = (dateString: string): string => {
  if (!dateString) return '';

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    console.error('日期格式化错误:', error);
    return '日期格式化错误';
  }
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

import KeywordsManager from '../modules/keywords/KeywordsManager';

interface DetailPanelProps {
  selectedItem: FileItem | ModelItem | VectorItem | MetadataItem | KeywordItem | SearchRecordItem | null;
  onClose: () => void;
}

const DetailPanel: React.FC<DetailPanelProps> = ({ selectedItem, onClose }) => {
  const [activeTab, setActiveTab] = useState<'basic' | 'keywords' | 'vector'>('basic');

  if (!selectedItem) return null;

  // 根据选中项目类型显示不同的图标
  const renderIcon = () => {
    if ('type' in selectedItem && selectedItem.type === 'file') {
      return <File size={24} className="text-blue-500" />;
    } else if ('type' in selectedItem && selectedItem.type === 'folder') {
      return <Folder size={24} className="text-yellow-500" />;
    } else if ('type' in selectedItem && selectedItem.type === 'model') {
      return <Cpu size={24} className="text-purple-500" />;
    } else if ('type' in selectedItem && selectedItem.type === 'vector') {
      return <Tag size={24} className="text-green-500" />;
    } else {
      return <Info size={24} className="text-gray-500" />;
    }
  };

  // 根据项目类型显示不同的属性
  const renderProperties = () => {
    if ('type' in selectedItem) {
      switch (selectedItem.type) {
        case 'file':
          return (
            <div className="grid grid-cols-2 gap-4">
              <div className="property-item">
                <span className="text-gray-500">类型：</span>
                <span>{(selectedItem as FileItem).category || '未知'}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">大小：</span>
                <span>{formatFileSize(parseInt((selectedItem as FileItem).size) || 0)}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">上传时间：</span>
                <span>{formatDate((selectedItem as FileItem).date)}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">状态：</span>
                <span>{(selectedItem as FileItem).status || '未知'}</span>
              </div>
              <div className="property-item col-span-2">
                <span className="text-gray-500">分类：</span>
                <span>{(selectedItem as FileItem).category || '未分类'}</span>
              </div>
            </div>
          );
        case 'folder':
          return (
            <div className="grid grid-cols-2 gap-4">
              <div className="property-item">
                <span className="text-gray-500">项目数：</span>
                <span>{(selectedItem as any).itemCount || 0}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">创建时间：</span>
                <span>{(selectedItem as any).date ? formatDate((selectedItem as any).date) : '未知'}</span>
              </div>
            </div>
          );
        case 'model':
          return (
            <div className="grid grid-cols-2 gap-4">
              <div className="property-item">
                <span className="text-gray-500">提供商：</span>
                <span>{(selectedItem as ModelItem).provider}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">版本：</span>
                <span>{(selectedItem as ModelItem).version}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">最后使用：</span>
                <span>{formatDate((selectedItem as ModelItem).lastUsed)}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">状态：</span>
                <span className={`${(selectedItem as ModelItem).status === 'active' ? 'text-green-500' : 'text-red-500'}`}>
                  {(selectedItem as ModelItem).status === 'active' ? '活跃' : '停用'}
                </span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">使用次数：</span>
                <span>{(selectedItem as ModelItem).usageCount}</span>
              </div>
            </div>
          );
        case 'vector':
          const vectorItem = selectedItem as unknown as VectorItem;
          return (
            <div className="grid grid-cols-2 gap-4">
              <div className="property-item">
                <span className="text-gray-500">文件数：</span>
                <span>{vectorItem.fileCount}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">大小：</span>
                <span>{vectorItem.size}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">最后更新：</span>
                <span>{formatDate(vectorItem.lastUpdated)}</span>
              </div>
              <div className="property-item">
                <span className="text-gray-500">状态：</span>
                <span>{vectorItem.status}</span>
              </div>
            </div>
          );
        default:
          return <div>无详细信息</div>;
      }
    } else if ('keyword' in selectedItem) {
      // 关键词详情
      return (
        <div className="grid grid-cols-2 gap-4">
          <div className="property-item">
            <span className="text-gray-500">分类：</span>
            <span>{(selectedItem as KeywordItem).category}</span>
          </div>
          <div className="property-item">
            <span className="text-gray-500">频率：</span>
            <span>{(selectedItem as KeywordItem).frequency}</span>
          </div>
          <div className="property-item">
            <span className="text-gray-500">重要度：</span>
            <span className={`${(selectedItem as KeywordItem).importance === 'high' ? 'text-red-500' : (selectedItem as KeywordItem).importance === 'medium' ? 'text-yellow-500' : 'text-green-500'}`}>
              {(selectedItem as KeywordItem).importance === 'high' ? '高' : (selectedItem as KeywordItem).importance === 'medium' ? '中' : '低'}
            </span>
          </div>
          <div className="property-item">
            <span className="text-gray-500">最后使用：</span>
            <span>{(selectedItem as KeywordItem).lastUsed}</span>
          </div>
        </div>
      );
    } else {
      return <div>无详细信息</div>;
    }
  };

  // 判断是否显示关键词管理选项卡
  const showKeywordsTab = 'type' in selectedItem && selectedItem.type === 'file';

  // 判断是否显示向量管理选项卡
  const showVectorTab = 'type' in selectedItem && (selectedItem.type === 'file' || selectedItem.type === 'model');

  return (
    <div className="detail-panel h-screen w-96 bg-white shadow-lg overflow-y-auto p-6">
      {/* 头部 */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold flex items-center">
          {renderIcon()}
          <span className="ml-2">详细信息</span>
        </h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <X size={20} />
        </button>
      </div>

      {/* 标题 */}
      <div className="mb-6">
        <h3 className="text-2xl font-bold mb-2">
          {'name' in selectedItem ? selectedItem.name : ('keyword' in selectedItem ? selectedItem.keyword : '未命名项目')}
        </h3>
        {'id' in selectedItem && (
          <div className="text-sm text-gray-500">
            ID: {selectedItem.id}
          </div>
        )}
      </div>

      {/* 标签导航 */}
      <div className="tabs mb-6 border-b">
        <div className="flex space-x-4">
          <button 
            className={`pb-2 px-1 ${activeTab === 'basic' ? 'border-b-2 border-blue-500 text-blue-500 font-medium' : 'text-gray-500'}`}
            onClick={() => setActiveTab('basic')}
          >
            基本信息
          </button>
          {showKeywordsTab && (
            <button 
              className={`pb-2 px-1 ${activeTab === 'keywords' ? 'border-b-2 border-blue-500 text-blue-500 font-medium' : 'text-gray-500'}`}
              onClick={() => setActiveTab('keywords')}
            >
              关键词管理
            </button>
          )}
          {showVectorTab && (
            <button 
              className={`pb-2 px-1 ${activeTab === 'vector' ? 'border-b-2 border-blue-500 text-blue-500 font-medium' : 'text-gray-500'}`}
              onClick={() => setActiveTab('vector')}
            >
              向量管理
            </button>
          )}
        </div>
      </div>

      {/* 内容区域 */}
      <div className="content-area">
        {activeTab === 'basic' && (
          <div className="basic-info">
            {renderProperties()}
          </div>
        )}

        {activeTab === 'keywords' && showKeywordsTab && (
          <div className="keywords-management">
            <KeywordsManager 
              selectedItem={selectedItem} 
              compact={true} 
              onSelectKeyword={(_) => {
                // 
              }}
              onSelectFile={(_) => {
                // 
              }}
            />
          </div>
        )}

        {activeTab === 'vector' && showVectorTab && (
          <div className="vector-management">
            <h3 className="text-lg font-semibold mb-4">向量管理</h3>
            <p className="text-gray-500">向量管理功能开发中...</p>
          </div>
        )}
      </div>

      {/* 底部操作区 */}
      <div className="actions mt-8 pt-4 border-t">
        <div className="flex justify-between items-center text-sm text-gray-500">
          <div>
            {'date' in selectedItem && selectedItem.date && (
              <span>创建于 {formatDate(selectedItem.date)}</span>
            )}
            {'lastUsed' in selectedItem && selectedItem.lastUsed && (
              <span>最后使用于 {formatDate(selectedItem.lastUsed)}</span>
            )}
          </div>
          <div>
            <button className="text-blue-500 hover:text-blue-700">编辑</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DetailPanel;