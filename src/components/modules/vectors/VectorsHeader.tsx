import React, { FC } from 'react';
import { Search, ChevronDown, PlusCircle, Grid, FileText, Database, BarChart } from 'lucide-react';
import { VectorItem } from '../../../utils/types';
import StatsCard from '../../ui/StatsCard';

interface VectorsHeaderProps {
    vectors: VectorItem[];
}

const VectorsHeader: FC<VectorsHeaderProps> = ({ vectors }) => {
    return (
        <div className="bg-white rounded-xl shadow-md mb-6 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-blue-500 to-indigo-700">
                <div className="flex justify-between items-center">
                    <h2 className="text-xl font-semibold text-white">向量库管理</h2>
                    <div className="flex space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-200 text-blue-800">
              总文档数: {vectors.reduce((sum, vector) => sum + vector.fileCount, 0)}
            </span>
                    </div>
                </div>
            </div>
            <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <StatsCard
                        icon={<Grid size={20} color="white" />}
                        title="向量库数量"
                        value={vectors.length}
                        color="bg-blue-600"
                        bgGradient="bg-gradient-to-br from-blue-50 to-indigo-50"
                    />
                    <StatsCard
                        icon={<FileText size={20} color="white" />}
                        title="总文件数"
                        value={vectors.reduce((sum, vector) => sum + vector.fileCount, 0)}
                        color="bg-indigo-600"
                        bgGradient="bg-gradient-to-br from-indigo-50 to-violet-50"
                    />
                    <StatsCard
                        icon={<Database size={20} color="white" />}
                        title="总存储空间"
                        value={`${Math.round(vectors.reduce((sum, vector) => {
                            // 提取数字部分（移除 'MB'）
                            const sizeNum = parseInt(vector.size.replace('MB', ''));
                            return sum + sizeNum;
                        }, 0) / 1024)} GB`}
                        color="bg-violet-600"
                        bgGradient="bg-gradient-to-br from-violet-50 to-purple-50"
                    />
                    <StatsCard
                        icon={<BarChart size={20} color="white" />}
                        title="本月检索次数"
                        value="15,234"
                        color="bg-emerald-600"
                        bgGradient="bg-gradient-to-br from-emerald-50 to-teal-50"
                    />
                </div>

                <div className="flex justify-between items-center mb-4">
                    <div className="flex space-x-2">
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                            <input
                                type="text"
                                placeholder="搜索向量库..."
                                className="pl-10 pr-4 py-2 border rounded-lg w-64"
                            />
                        </div>
                        <div className="relative">
                            <select className="pl-3 pr-8 py-2 border rounded-lg appearance-none bg-white">
                                <option>所有状态</option>
                                <option>活跃</option>
                                <option>维护中</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-2.5 text-gray-400 pointer-events-none" size={18} />
                        </div>
                    </div>
                    <button className="flex items-center bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-4 py-2 rounded-lg hover:from-blue-700 hover:to-indigo-700 shadow-sm">
                        <PlusCircle size={18} className="mr-1" />
                        创建向量库
                    </button>
                </div>
            </div>
        </div>
    );
};

export default VectorsHeader;