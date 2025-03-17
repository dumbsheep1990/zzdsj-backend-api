import React from 'react';
import { Search, ChevronDown, PlusCircle, Code, Grid, BarChart, Zap } from 'lucide-react';
import { ModelItem } from '../../../utils/types';
import StatsCard from '../../ui/StatsCard';

interface ModelsHeaderProps {
    models: ModelItem[];
}

const ModelsHeader: React.FC<ModelsHeaderProps> = ({ models }) => {
    return (
        <div className="bg-white rounded-xl shadow-md mb-6 overflow-hidden">
            <div className="p-4 bg-gradient-to-r from-purple-600 to-indigo-700">
                <div className="flex justify-between items-center">
                    <h2 className="text-xl font-semibold text-white">模型管理控制台</h2>
                    <div className="flex space-x-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-200 text-purple-800">
              已连接: {models.filter(m => m.status === '已连接').length}/{models.length}
            </span>
                    </div>
                </div>
            </div>
            <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <StatsCard
                        icon={<Code size={20} color="white" />}
                        title="大型语言模型"
                        value={models.filter(m => m.type === 'LLM').length}
                        color="bg-purple-600"
                        bgGradient="bg-gradient-to-br from-purple-50 to-indigo-50"
                    />
                    <StatsCard
                        icon={<Grid size={20} color="white" />}
                        title="嵌入模型"
                        value={models.filter(m => m.type === '嵌入模型').length}
                        color="bg-indigo-600"
                        bgGradient="bg-gradient-to-br from-indigo-50 to-blue-50"
                    />
                    <StatsCard
                        icon={<BarChart size={20} color="white" />}
                        title="总调用次数"
                        value={models.reduce((sum, model) => sum + (model.usageCount || 0), 0)}
                        color="bg-blue-600"
                        bgGradient="bg-gradient-to-br from-blue-50 to-cyan-50"
                    />
                    <StatsCard
                        icon={<Zap size={20} color="white" />}
                        title="平均响应时间"
                        value="356ms"
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
                                placeholder="搜索模型..."
                                className="pl-10 pr-4 py-2 border rounded-lg w-64"
                            />
                        </div>
                        <div className="relative">
                            <select className="pl-3 pr-8 py-2 border rounded-lg appearance-none bg-white">
                                <option>所有类型</option>
                                <option>大型语言模型</option>
                                <option>嵌入模型</option>
                            </select>
                            <ChevronDown className="absolute right-3 top-2.5 text-gray-400 pointer-events-none" size={18} />
                        </div>
                    </div>
                    <button className="flex items-center bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-indigo-700 shadow-sm">
                        <PlusCircle size={18} className="mr-1" />
                        添加新模型
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ModelsHeader;