import React from 'react';
import { Code, Sliders, RefreshCw, MoreHorizontal } from 'lucide-react';
import { ModelItem } from '../../../utils/types';

interface ModelsListProps {
    models: ModelItem[];
    selectedItem: ModelItem | null;
    setSelectedItem: (item: ModelItem | null) => void;
}

const ModelsList: React.FC<ModelsListProps> = ({ models, selectedItem, setSelectedItem }) => {
    return (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模型名称</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">提供商</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">版本</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">最后使用</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {models.map((model) => (
                    <tr
                        key={model.id}
                        className={`hover:bg-gray-50 cursor-pointer ${selectedItem?.id === model.id ? 'bg-indigo-50' : ''}`}
                        onClick={() => setSelectedItem(model)}
                    >
                        <td className="px-6 py-4">
                            <div className="flex items-center">
                                <Code size={18} className={`mr-2 ${
                                    model.type === 'LLM' ? 'text-purple-500' : 'text-indigo-500'
                                }`} />
                                <span className="font-medium">{model.name}</span>
                            </div>
                        </td>
                        <td className="px-6 py-4">
                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                  {model.type}
                </span>
                        </td>
                        <td className="px-6 py-4">{model.provider}</td>
                        <td className="px-6 py-4">{model.version}</td>
                        <td className="px-6 py-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    model.status === '已连接' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {model.status}
                </span>
                        </td>
                        <td className="px-6 py-4">{model.lastUsed}</td>
                        <td className="px-6 py-4">
                            <div className="flex space-x-2">
                                <button className="text-gray-400 hover:text-purple-600">
                                    <Sliders size={16} />
                                </button>
                                <button className="text-gray-400 hover:text-purple-600">
                                    <RefreshCw size={16} />
                                </button>
                                <button className="text-gray-400 hover:text-gray-600">
                                    <MoreHorizontal size={16} />
                                </button>
                            </div>
                        </td>
                    </tr>
                ))}
                </tbody>
            </table>
        </div>
    );
};

export default ModelsList;