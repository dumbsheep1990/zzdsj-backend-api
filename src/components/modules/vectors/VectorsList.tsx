import React from 'react';
import { Database, BarChart, RefreshCw, MoreHorizontal } from 'lucide-react';
import { VectorItem } from '../../../utils/types';

interface VectorsListProps {
    vectors: VectorItem[];
    selectedItem: VectorItem | null;
    setSelectedItem: (item: VectorItem | null) => void;
}

const VectorsList: React.FC<VectorsListProps> = ({ vectors, selectedItem, setSelectedItem }) => {
    return (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">向量库名称</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件数量</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">大小</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">最后更新</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {vectors.map((vector) => (
                    <tr
                        key={vector.id}
                        className={`hover:bg-gray-50 cursor-pointer ${selectedItem?.id === vector.id ? 'bg-indigo-50' : ''}`}
                        onClick={() => setSelectedItem(vector)}
                    >
                        <td className="px-6 py-4">
                            <div className="flex items-center">
                                <Database size={18} className="text-blue-500 mr-2" />
                                <span className="font-medium">{vector.name}</span>
                            </div>
                        </td>
                        <td className="px-6 py-4">{vector.fileCount}</td>
                        <td className="px-6 py-4">{vector.size}</td>
                        <td className="px-6 py-4">{vector.lastUpdated}</td>
                        <td className="px-6 py-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    vector.status === '活跃' ? 'bg-green-100 text-green-800' :
                        vector.status === '维护中' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                }`}>
                  {vector.status}
                </span>
                        </td>
                        <td className="px-6 py-4">
                            <div className="flex space-x-2">
                                <button className="text-gray-400 hover:text-blue-600">
                                    <BarChart size={16} />
                                </button>
                                <button className="text-gray-400 hover:text-blue-600">
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

export default VectorsList;