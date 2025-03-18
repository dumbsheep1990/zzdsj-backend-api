import React, { FC } from 'react';
import { Search, ChevronDown, Filter, Upload, PlusCircle } from 'lucide-react';
import { FileItem } from '../../../utils/types';

interface FilesHeaderProps {
    files: FileItem[];
}

const FilesHeader: FC<FilesHeaderProps> = ({ files }) => {
    return (
        <div className="bg-white rounded-xl shadow-md mb-6 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-600 to-indigo-700">
                <div className="flex justify-between items-center">
                    <h2 className="text-xl font-semibold text-white">文件管理控制台</h2>
                    <div className="flex space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-200 text-blue-800">
              总计: {files.length} 个文件
            </span>
                    </div>
                </div>
            </div>
            <div className="p-4 border-b">
                <div className="flex flex-wrap items-center justify-between">
                    <div className="flex space-x-2 mb-2 sm:mb-0">
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                            <input
                                type="text"
                                placeholder="搜索文件..."
                                className="pl-10 pr-4 py-2 border rounded-lg w-64"
                            />
                        </div>
                        <div className="relative">
                            <select className="pl-3 pr-8 py-2 border rounded-lg appearance-none bg-white">
                                <option>所有类型</option>
                                <option>PDF</option>
                                <option>DOCX</option>
                                <option>XLSX</option>
                                <option>PPTX</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-2.5 text-gray-400 pointer-events-none" size={18} />
                        </div>
                        <button className="p-2 border rounded-lg text-gray-700 hover:bg-gray-50">
                            <Filter size={18} />
                        </button>
                    </div>
                    <div className="flex space-x-2">
                        <button className="flex items-center bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50">
                            <Upload size={18} className="mr-1" />
                            导入
                        </button>
                        <button className="flex items-center bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2 rounded-lg hover:from-indigo-700 hover:to-purple-700 shadow-sm">
                            <PlusCircle size={18} className="mr-1" />
                            上传文件
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilesHeader;