import React from 'react';
import { FileText, Share2, Download, MoreHorizontal } from 'lucide-react';
import { FileItem } from '../../../utils/types';

interface FilesListProps {
    files: FileItem[];
    selectedItem: FileItem | null;
    setSelectedItem: (item: FileItem | null) => void;
}

const FilesList: React.FC<FilesListProps> = ({ files, selectedItem, setSelectedItem }) => {
    return (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">文件名</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">分类</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">大小</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">更新日期</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">状态</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
                </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {files.map((file) => (
                    <tr
                        key={file.id}
                        className={`hover:bg-gray-50 cursor-pointer ${selectedItem?.id === file.id ? 'bg-indigo-50' : ''}`}
                        onClick={() => setSelectedItem(file)}
                    >
                        <td className="px-6 py-4">
                            <div className="flex items-center">
                                <FileText size={18} className={`mr-2 ${
                                    file.type === 'pdf' ? 'text-red-500' :
                                        file.type === 'docx' ? 'text-blue-500' :
                                            file.type === 'xlsx' ? 'text-green-500' :
                                                file.type === 'pptx' ? 'text-orange-500' :
                                                    'text-gray-500'
                                }`} />
                                <span className="font-medium">{file.name}</span>
                            </div>
                        </td>
                        <td className="px-6 py-4">
                <span className="px-2 py-1 bg-gray-100 rounded text-xs">
                  {file.type.toUpperCase()}
                </span>
                        </td>
                        <td className="px-6 py-4">
                            <span>{file.category}</span>
                        </td>
                        <td className="px-6 py-4">{file.size}</td>
                        <td className="px-6 py-4">{file.date}</td>
                        <td className="px-6 py-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    file.status === '已向量化' ? 'bg-green-100 text-green-800' :
                        file.status === '处理中' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                }`}>
                  {file.status}
                </span>
                        </td>
                        <td className="px-6 py-4">
                            <div className="flex space-x-2">
                                <button className="text-gray-400 hover:text-indigo-600">
                                    <Share2 size={16} />
                                </button>
                                <button className="text-gray-400 hover:text-indigo-600">
                                    <Download size={16} />
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
            <div className="px-6 py-3 flex items-center justify-between border-t">
                <div className="text-sm text-gray-500">
                    显示 <span className="font-medium">1</span> 至 <span className="font-medium">{files.length}</span> 条，共 <span className="font-medium">324</span> 条
                </div>
                <div className="flex space-x-1">
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">上一页</button>
                    <button className="px-3 py-1 border rounded-md bg-indigo-600 text-white">1</button>
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">2</button>
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">3</button>
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">下一页</button>
                </div>
            </div>
        </div>
    );
};

export default FilesList;