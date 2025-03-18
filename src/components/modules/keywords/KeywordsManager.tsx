import React, { useState } from 'react';
import { KeywordItem, FileItem } from '../../../utils/types';
import { keywordsData, fileData } from '../../../utils/mockData';
import { Plus, Edit, Trash2, Search, Tag, FileText } from 'lucide-react';
import KnowledgeGraph from './KnowledgeGraph';

interface KeywordsManagerProps {
  onSelectKeyword?: (keyword: KeywordItem) => void;
  onSelectFile?: (file: FileItem) => void;
}

const KeywordsManager: React.FC<KeywordsManagerProps> = ({
  onSelectKeyword,
  onSelectFile
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedKeywordId, setSelectedKeywordId] = useState<number | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKeyword, setNewKeyword] = useState({
    keyword: '',
    category: '',
    importance: 'medium' as 'high' | 'medium' | 'low'
  });

  // u8fc7u6ee4u5173u952eu8bcd
  const filteredKeywords = keywordsData.filter(keyword =>
    keyword.keyword.toLowerCase().includes(searchTerm.toLowerCase()) ||
    keyword.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // u627eu5230u4e0eu9009u4e2du5173u952eu8bcdu76f8u5173u7684u6587u4ef6
  const relatedFiles = selectedKeywordId
    ? fileData.filter(file => 
        file.keywords?.some(k => k.keywordId === selectedKeywordId)
      )
    : [];

  // u627eu5230u4e0eu9009u4e2du5173u952eu8bcdu76f8u5173u7684u5176u4ed6u5173u952eu8bcd
  const relatedKeywords = selectedKeywordId
    ? keywordsData.find(k => k.id === selectedKeywordId)?.relatedKeywords?.map(id => 
        keywordsData.find(k => k.id === id)
      ).filter(Boolean) as KeywordItem[]
    : [];

  const handleKeywordClick = (keyword: KeywordItem) => {
    setSelectedKeywordId(keyword.id);
    if (onSelectKeyword) {
      onSelectKeyword(keyword);
    }
  };

  const handleFileClick = (file: FileItem) => {
    if (onSelectFile) {
      onSelectFile(file);
    }
  };

  const handleAddKeyword = () => {
    // u5728u5b9eu9645u5e94u7528u4e2du8fd9u91ccu4f1au8c03u7528APIu6dfbu52a0u5173u952eu8bcd
    setShowAddModal(false);
    setNewKeyword({
      keyword: '',
      category: '',
      importance: 'medium'
    });
  };

  return (
    <div className="keywords-manager grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* u5de6u4fa7u5173u952eu8bcdu5217u8868 */}
      <div className="keywords-list col-span-1 bg-white rounded-lg shadow-md p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">u5173u952eu8bcdu7ba1u7406</h3>
          <button 
            onClick={() => setShowAddModal(true)}
            className="p-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition-colors"
          >
            <Plus size={16} />
          </button>
        </div>
        
        <div className="search-box relative mb-4">
          <input
            type="text"
            placeholder="u641cu7d22u5173u952eu8bcd..."
            className="w-full p-2 pl-10 border rounded-md"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Search size={18} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
        </div>
        
        <div className="keywords-table overflow-y-auto max-h-[500px]">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u5173u952eu8bcd</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u9891u7387</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u91cdu8981u5ea6</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u64cdu4f5c</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredKeywords.map((keyword) => (
                <tr 
                  key={keyword.id} 
                  className={`hover:bg-gray-50 cursor-pointer ${selectedKeywordId === keyword.id ? 'bg-blue-50' : ''}`}
                  onClick={() => handleKeywordClick(keyword)}
                >
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center">
                      <Tag size={16} className="mr-2 text-gray-500" />
                      <span className="font-medium">{keyword.keyword}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">{keyword.frequency}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs rounded-full ${keyword.importance === 'high' ? 'bg-red-100 text-red-800' : keyword.importance === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                      {keyword.importance === 'high' ? 'u9ad8' : keyword.importance === 'medium' ? 'u4e2d' : 'u4f4e'}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex space-x-2">
                      <button className="text-blue-500 hover:text-blue-700">
                        <Edit size={16} />
                      </button>
                      <button className="text-red-500 hover:text-red-700">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* u4e2du95f4u77e5u8bc6u56feu8c31 */}
      <div className="graph-container col-span-2">
        <KnowledgeGraph 
          height={600} 
          width={800} 
          selectedKeywordId={selectedKeywordId || undefined}
        />
      </div>
      
      {/* u5173u952eu8bcdu8be6u60c5 */}
      {selectedKeywordId && (
        <div className="keyword-details col-span-1 bg-white rounded-lg shadow-md p-4">
          <h3 className="text-lg font-semibold mb-4">u5173u952eu8bcdu8be6u60c5</h3>
          
          {/* u9009u4e2du7684u5173u952eu8bcdu4fe1u606f */}
          {selectedKeywordId && (
            <div className="selected-keyword mb-6">
              <h4 className="font-medium text-gray-700 mb-2">
                {keywordsData.find(k => k.id === selectedKeywordId)?.keyword}
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="info-item">
                  <span className="text-gray-500">u5206u7c7buff1a</span>
                  <span>{keywordsData.find(k => k.id === selectedKeywordId)?.category}</span>
                </div>
                <div className="info-item">
                  <span className="text-gray-500">u9891u7387uff1a</span>
                  <span>{keywordsData.find(k => k.id === selectedKeywordId)?.frequency}</span>
                </div>
                <div className="info-item">
                  <span className="text-gray-500">u6700u540eu4f7fu7528uff1a</span>
                  <span>{keywordsData.find(k => k.id === selectedKeywordId)?.lastUsed}</span>
                </div>
                <div className="info-item">
                  <span className="text-gray-500">u91cdu8981u5ea6uff1a</span>
                  <span className={`${keywordsData.find(k => k.id === selectedKeywordId)?.importance === 'high' ? 'text-red-500' : keywordsData.find(k => k.id === selectedKeywordId)?.importance === 'medium' ? 'text-yellow-500' : 'text-green-500'}`}>
                    {keywordsData.find(k => k.id === selectedKeywordId)?.importance === 'high' ? 'u9ad8' : keywordsData.find(k => k.id === selectedKeywordId)?.importance === 'medium' ? 'u4e2d' : 'u4f4e'}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          {/* u76f8u5173u5173u952eu8bcd */}
          <div className="related-keywords mb-6">
            <h4 className="font-medium text-gray-700 mb-2">u76f8u5173u5173u952eu8bcd</h4>
            {relatedKeywords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {relatedKeywords.map(keyword => (
                  <span 
                    key={keyword.id}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm cursor-pointer hover:bg-blue-200"
                    onClick={() => handleKeywordClick(keyword)}
                  >
                    {keyword.keyword}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">u6ca1u6709u76f8u5173u5173u952eu8bcd</p>
            )}
          </div>
          
          {/* u76f8u5173u6587u4ef6 */}
          <div className="related-files">
            <h4 className="font-medium text-gray-700 mb-2">u76f8u5173u6587u4ef6 ({relatedFiles.length})</h4>
            {relatedFiles.length > 0 ? (
              <div className="overflow-y-auto max-h-[200px]">
                {relatedFiles.map(file => {
                  const relevance = file.keywords?.find(k => k.keywordId === selectedKeywordId)?.relevance || 0;
                  return (
                    <div 
                      key={file.id}
                      className="p-2 border-b hover:bg-gray-50 cursor-pointer flex items-center justify-between"
                      onClick={() => handleFileClick(file)}
                    >
                      <div className="flex items-center">
                        <FileText size={16} className="mr-2 text-gray-500" />
                        <span>{file.name}</span>
                      </div>
                      <div className="relevance-indicator flex items-center">
                        <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden mr-2">
                          <div 
                            className={`h-full ${relevance > 80 ? 'bg-green-500' : relevance > 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${relevance}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-500">{relevance}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">u6ca1u6709u76f8u5173u6587u4ef6</p>
            )}
          </div>
        </div>
      )}
      
      {/* u6dfbu52a0u5173u952eu8bcdu6a21u6001u6846 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">u6dfbu52a0u65b0u5173u952eu8bcd</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">u5173u952eu8bcd</label>
              <input
                type="text"
                className="w-full p-2 border rounded-md"
                value={newKeyword.keyword}
                onChange={(e) => setNewKeyword({...newKeyword, keyword: e.target.value})}
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">u5206u7c7b</label>
              <input
                type="text"
                className="w-full p-2 border rounded-md"
                value={newKeyword.category}
                onChange={(e) => setNewKeyword({...newKeyword, category: e.target.value})}
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">u91cdu8981u5ea6</label>
              <select
                className="w-full p-2 border rounded-md"
                value={newKeyword.importance}
                onChange={(e) => setNewKeyword({...newKeyword, importance: e.target.value as 'high' | 'medium' | 'low'})}
              >
                <option value="high">u9ad8</option>
                <option value="medium">u4e2d</option>
                <option value="low">u4f4e</option>
              </select>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                className="px-4 py-2 border rounded-md hover:bg-gray-100"
                onClick={() => setShowAddModal(false)}
              >
                u53d6u6d88
              </button>
              <button
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                onClick={handleAddKeyword}
              >
                u6dfbu52a0
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KeywordsManager;
