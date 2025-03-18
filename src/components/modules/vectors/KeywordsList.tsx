import React, { FC } from 'react';
import { Tag, BarChart, Edit, Trash2 } from 'lucide-react';
import { KeywordItem } from '../../../utils/types';

interface KeywordsListProps {
    keywords: KeywordItem[];
    selectedItem: KeywordItem | null;
    setSelectedItem: (item: KeywordItem | null) => void;
}

const KeywordsList: FC<KeywordsListProps> = ({ keywords, selectedItem, setSelectedItem }) => {
    // 获取重要性对应的样式
    const getImportanceStyle = (importance: 'high' | 'medium' | 'low') => {
        switch (importance) {
            case 'high':
                return 'bg-red-100 text-red-800';
            case 'medium':
                return 'bg-yellow-100 text-yellow-800';
            case 'low':
                return 'bg-green-100 text-green-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
                <div className="text-lg font-medium">关键词列表</div>
                <button className="px-3 py-1.5 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700">
                    添加关键词
                </button>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">关键词</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">使用频率</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">最后使用</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">分类</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">重要性</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {keywords.map((keyword) => (
                        <tr
                            key={keyword.id}
                            className={`hover:bg-gray-50 cursor-pointer ${selectedItem?.id === keyword.id ? 'bg-indigo-50' : ''}`}
                            onClick={() => setSelectedItem(keyword)}
                        >
                            <td className="px-6 py-4">
                                <div className="flex items-center">
                                    <Tag size={18} className="text-indigo-500 mr-2" />
                                    <span className="font-medium">{keyword.keyword}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4">{keyword.frequency}</td>
                            <td className="px-6 py-4">{keyword.lastUsed}</td>
                            <td className="px-6 py-4">{keyword.category}</td>
                            <td className="px-6 py-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getImportanceStyle(keyword.importance)}`}>
                                    {keyword.importance === 'high' ? '高' : keyword.importance === 'medium' ? '中' : '低'}
                                </span>
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex space-x-2">
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <BarChart size={16} />
                                    </button>
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <Edit size={16} />
                                    </button>
                                    <button className="text-gray-400 hover:text-red-600">
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <div className="px-6 py-3 flex items-center justify-between border-t">
                <div className="text-sm text-gray-500">
                    显示 <span className="font-medium">1</span> 至 <span className="font-medium">{keywords.length}</span> 条，共 <span className="font-medium">{keywords.length}</span> 条
                </div>
                <div className="flex space-x-1">
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">上一页</button>
                    <button className="px-3 py-1 border rounded-md bg-indigo-600 text-white">1</button>
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">下一页</button>
                </div>
            </div>
        </div>
    );
};

export default KeywordsList;
