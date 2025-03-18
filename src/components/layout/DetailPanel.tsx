import React from 'react';
import { Share2, Download, X, Info, PlusCircle, Tag, Search } from 'lucide-react';
import { DetailPanelProps } from '../../utils/types';

const PencilIcon = ({ size = 20, className = "" }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12 20h9"></path>
        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
    </svg>
);

const TrashIcon = ({ size = 20, className = "" }) => (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <polyline points="3 6 5 6 21 6"></polyline>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    </svg>
);

const DetailPanel: React.FC<DetailPanelProps> = ({ selectedItem, setSelectedItem, activeSection }) => {
    if (!selectedItem) {
        return (
            <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center p-6">
                    <Info size={48} className="mx-auto mb-4" />
                    <p className="text-lg">选择一个项目查看详细信息</p>
                </div>
            </div>
        );
    }

    const getTypeDisplay = (): string => {
        if ('type' in selectedItem && selectedItem.type) {
            return selectedItem.type.toUpperCase();
        } else if ('category' in selectedItem && selectedItem.category) {
            return selectedItem.category;
        } else {
            return '未分类';
        }
    };

    const getSizeOrCount = (): string => {
        if ('size' in selectedItem && selectedItem.size) {
            return selectedItem.size;
        } else if ('fileCount' in selectedItem && selectedItem.fileCount !== undefined) {
            return `${selectedItem.fileCount} 个文件`;
        } else if ('fields' in selectedItem && selectedItem.fields !== undefined) {
            return `${selectedItem.fields} 个字段`;
        } else if ('frequency' in selectedItem && selectedItem.frequency !== undefined) {
            return `${selectedItem.frequency} 次使用`;
        } else if ('results' in selectedItem && selectedItem.results !== undefined) {
            return `${selectedItem.results} 个结果`;
        } else {
            return '—';
        }
    };

    const getDate = (): string => {
        if ('date' in selectedItem && selectedItem.date) {
            return selectedItem.date;
        } else if ('lastUsed' in selectedItem && selectedItem.lastUsed) {
            return selectedItem.lastUsed;
        } else if ('lastUpdated' in selectedItem && selectedItem.lastUpdated) {
            return selectedItem.lastUpdated;
        } else if ('timestamp' in selectedItem && selectedItem.timestamp) {
            return selectedItem.timestamp;
        } else {
            return '—';
        }
    };

    const getStatusInfo = () => {
        let statusText = '活跃';
        let statusClass = 'bg-gray-100 text-gray-800';

        if ('status' in selectedItem && selectedItem.status) {
            statusText = selectedItem.status;
            if (selectedItem.status === '已向量化' || selectedItem.status === '已连接' || selectedItem.status === '活跃') {
                statusClass = 'bg-green-100 text-green-800';
            } else if (selectedItem.status === '处理中' || selectedItem.status === '维护中') {
                statusClass = 'bg-yellow-100 text-yellow-800';
            }
        } else if ('usage' in selectedItem && selectedItem.usage) {
            statusText = selectedItem.usage;
            if (selectedItem.usage === '广泛使用') {
                statusClass = 'bg-green-100 text-green-800';
            } else if (selectedItem.usage === '部分使用') {
                statusClass = 'bg-blue-100 text-blue-800';
            }
        } else if ('importance' in selectedItem && selectedItem.importance) {
            statusText = selectedItem.importance === 'high' ? '高重要性' : 
                        selectedItem.importance === 'medium' ? '中重要性' : '低重要性';
            if (selectedItem.importance === 'high') {
                statusClass = 'bg-red-100 text-red-800';
            } else if (selectedItem.importance === 'medium') {
                statusClass = 'bg-yellow-100 text-yellow-800';
            } else {
                statusClass = 'bg-green-100 text-green-800';
            }
        } else if ('source' in selectedItem && selectedItem.source) {
            statusText = selectedItem.source;
            statusClass = selectedItem.source === 'Web来源' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800';
        }

        return { text: statusText, className: statusClass };
    };

    const statusInfo = getStatusInfo();

    // 获取标题
    const getTitle = (): string => {
        if ('name' in selectedItem && selectedItem.name) {
            return selectedItem.name;
        } else if ('keyword' in selectedItem && selectedItem.keyword) {
            return selectedItem.keyword;
        } else if ('query' in selectedItem && selectedItem.query) {
            return selectedItem.query;
        } else {
            return `ID-${selectedItem.id}`;
        }
    };

    // 获取标题图标
    const getTitleIcon = () => {
        if ('keyword' in selectedItem) {
            return <Tag size={18} className="text-indigo-500 mr-2" />;
        } else if ('query' in selectedItem) {
            return <Search size={18} className="text-indigo-500 mr-2" />;
        } else {
            return null;
        }
    };

    return (
        <div className="p-0 h-full overflow-auto">
            <div className="sticky top-0 z-10 bg-white border-b">
                <div className="flex justify-between items-center p-4">
                    <h2 className="text-xl font-semibold flex items-center">
                        {getTitleIcon()}
                        {getTitle()}
                    </h2>
                    <div className="flex items-center space-x-2">
                        <button className="p-2 hover:bg-gray-100 rounded-full">
                            <Share2 size={18} className="text-gray-500" />
                        </button>
                        <button className="p-2 hover:bg-gray-100 rounded-full">
                            <Download size={18} className="text-gray-500" />
                        </button>
                        <button
                            className="p-2 hover:bg-gray-100 rounded-full"
                            onClick={() => setSelectedItem(null)}
                        >
                            <X size={18} className="text-gray-500" />
                        </button>
                    </div>
                </div>
                <div className="flex px-4 border-b">
                    <button className="px-4 py-2 border-b-2 border-indigo-600 text-indigo-600 font-medium">
                        基本信息
                    </button>
                    <button className="px-4 py-2 text-gray-500 hover:text-gray-700">
                        元数据
                    </button>
                    <button className="px-4 py-2 text-gray-500 hover:text-gray-700">
                        使用记录
                    </button>
                </div>
            </div>

            <div className="p-6">
                {/* 基本信息卡片 */}
                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-5 mb-6">
                    <div className="grid grid-cols-2 gap-6">
                        <div>
                            <p className="text-sm text-gray-500 mb-1">类型</p>
                            <div className="flex items-center">
                <span className={`mr-2 w-3 h-3 rounded-full ${
                    'type' in selectedItem ? (
                        selectedItem.type === 'pdf' || selectedItem.type === 'docx' ? 'bg-blue-500' :
                            selectedItem.type === 'xlsx' || selectedItem.type === 'pptx' ? 'bg-green-500' :
                                selectedItem.type === 'LLM' ? 'bg-purple-500' :
                                    selectedItem.type === '嵌入模型' ? 'bg-indigo-500' :
                                        'bg-orange-500'
                    ) : 'bg-gray-500'
                }`}></span>
                                <p className="font-medium">{getTypeDisplay()}</p>
                            </div>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 mb-1">大小 / 项目数</p>
                            <p className="font-medium">{getSizeOrCount()}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 mb-1">创建/更新日期</p>
                            <p className="font-medium">{getDate()}</p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500 mb-1">状态</p>
                            <div className="flex items-center">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.className}`}>
                  {statusInfo.text}
                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 元数据区域 */}
                <div className="mb-6">
                    <div className="flex justify-between items-center mb-3">
                        <h3 className="font-medium text-lg">元数据</h3>
                        <button className="text-sm text-indigo-600 hover:text-indigo-800 flex items-center">
                            <PlusCircle size={16} className="mr-1" />
                            添加字段
                        </button>
                    </div>
                    <div className="bg-white rounded-xl overflow-hidden shadow-sm border">
                        <table className="w-full">
                            <tbody className="divide-y divide-gray-200">
                            <tr>
                                <td className="p-3 bg-gray-50 w-1/3 text-gray-600">标识符</td>
                                <td className="p-3 flex justify-between items-center">
                                    <span>ID-{selectedItem.id}</span>
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <PencilIcon size={14} />
                                    </button>
                                </td>
                            </tr>
                            <tr>
                                <td className="p-3 bg-gray-50 text-gray-600">创建者</td>
                                <td className="p-3 flex justify-between items-center">
                                    <span>智政知脑管理员</span>
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <PencilIcon size={14} />
                                    </button>
                                </td>
                            </tr>
                            <tr>
                                <td className="p-3 bg-gray-50 text-gray-600">权限</td>
                                <td className="p-3 flex justify-between items-center">
                                    <span>可读/可写</span>
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <PencilIcon size={14} />
                                    </button>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* 根据页面特定内容 */}
                {renderPageSpecificContent(activeSection, selectedItem)}
            </div>
        </div>
    );
};

// 根据页面特定内容
const renderPageSpecificContent = (activeSection: string, selectedItem: any) => {
    switch (activeSection) {
        case 'files':
            // 文件管理特有内容
            if ('status' in selectedItem) {
                return (
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-3">
                            <h3 className="font-medium text-lg">向量化状态</h3>
                            <button className="text-sm text-indigo-600 hover:text-indigo-800">查看详情</button>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border p-5">
                            <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-2 ${
                      selectedItem.status === '已向量化' ? 'bg-green-100 text-green-800' :
                          selectedItem.status === '处理中' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                  }`}>
                    {selectedItem.status || '未处理'}
                  </span>
                                    <span className="text-sm text-gray-500">
                    {selectedItem.status === '已向量化' ? '向量化完成于 ' + selectedItem.date :
                        selectedItem.status === '处理中' ? '正在处理...' : '尚未向量化'}
                  </span>
                                </div>
                            </div>

                            {selectedItem.status === '已向量化' && (
                                <div className="mt-3">
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>向量维度</span>
                                        <span>1536</span>
                                    </div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span>嵌入模型</span>
                                        <span>Embedding-v3</span>
                                    </div>
                                    <div className="flex justify-between text-sm mb-3">
                                        <span>索引方式</span>
                                        <span>HNSW</span>
                                    </div>
                                </div>
                            )}

                            <div className="mt-4">
                                <button className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 shadow-sm mr-2">
                                    {selectedItem.status === '已向量化' ? '更新向量' : '开始向量化'}
                                </button>
                                {selectedItem.status === '已向量化' && (
                                    <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                                        查看向量数据
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                );
            }
            return null;

        case 'models':
            // 模型管理特有内容
            if ('provider' in selectedItem) {
                return (
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-3">
                            <h3 className="font-medium text-lg">模型配置</h3>
                            <button className="text-sm text-indigo-600 hover:text-indigo-800">查看使用日志</button>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border p-5">
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    API密钥
                                </label>
                                <div className="flex">
                                    <input
                                        type="password"
                                        value="••••••••••••••••••••••••••"
                                        className="flex-1 border rounded-l-md px-3 py-2 bg-gray-50"
                                        disabled
                                    />
                                    <button className="px-3 py-2 bg-gray-100 border border-l-0 rounded-r-md hover:bg-gray-200">
                                        查看
                                    </button>
                                </div>
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    服务端点
                                </label>
                                <input
                                    type="text"
                                    value="https://api.openai.com/v1/completions"
                                    className="w-full border rounded-md px-3 py-2"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    请求参数
                                </label>
                                <div className="border border-gray-300 rounded-md p-3 bg-gray-50">
                  <pre className="text-xs">{`{
  "temperature": 0.7,
  "max_tokens": 1024,
  "top_p": 1,
  "frequency_penalty": 0,
  "presence_penalty": 0
}`}</pre>
                                </div>
                            </div>
                            <div className="flex">
                                <button className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 shadow-sm mr-2">
                                    保存配置
                                </button>
                                <button className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-md hover:from-emerald-600 hover:to-teal-600 shadow-sm">
                                    测试连接
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }
            return null;

        case 'vectors':
            // 向量库管理特有内容
            if ('fileCount' in selectedItem) {
                return (
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-3">
                            <h3 className="font-medium text-lg">向量库统计</h3>
                            <button className="text-sm text-indigo-600 hover:text-indigo-800">查看全部文件</button>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border p-5">
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="bg-gradient-to-br from-indigo-50 to-blue-50 p-4 rounded-lg">
                                    <div className="text-sm text-gray-500 mb-1">文件数量</div>
                                    <div className="text-2xl font-semibold">{selectedItem.fileCount}</div>
                                </div>
                                <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-4 rounded-lg">
                                    <div className="text-sm text-gray-500 mb-1">数据大小</div>
                                    <div className="text-2xl font-semibold">{selectedItem.size}</div>
                                </div>
                            </div>
                            <div className="mb-4">
                                <div className="text-sm font-medium mb-2">文件类型分布</div>
                                <div className="h-8 bg-gray-200 rounded-full overflow-hidden">
                                    <div className="flex h-full">
                                        <div className="bg-blue-500 h-full w-1/2" title="PDF: 50%"></div>
                                        <div className="bg-green-500 h-full w-1/4" title="DOCX: 25%"></div>
                                        <div className="bg-yellow-500 h-full w-1/8" title="XLSX: 12.5%"></div>
                                        <div className="bg-red-500 h-full w-1/8" title="其他: 12.5%"></div>
                                    </div>
                                </div>
                                <div className="flex text-xs justify-between mt-1 text-gray-500">
                                    <span>PDF (50%)</span>
                                    <span>DOCX (25%)</span>
                                    <span>XLSX (12.5%)</span>
                                    <span>其他 (12.5%)</span>
                                </div>
                            </div>
                            <div className="flex">
                                <button className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 shadow-sm mr-2">
                                    重建索引
                                </button>
                                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                                    导出统计
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }
            return null;

        case 'metadata':
            if ('fields' in selectedItem) {
                return (
                    <div className="mb-6">
                        <div className="flex justify-between items-center mb-3">
                            <h3 className="font-medium text-lg">元数据模板字段</h3>
                            <button className="text-sm text-indigo-600 hover:text-indigo-800">添加字段</button>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border">
                            <div className="divide-y divide-gray-200">
                                {Array(selectedItem.fields).fill(0).map((_, index) => (
                                    <div key={index} className="p-3 flex justify-between items-center hover:bg-gray-50">
                                        <div>
                                            <span className="font-medium">{['标题', '作者', '分类', '发布日期', '关键词', '摘要', '状态', '审核人', '版本', '来源', '页数', '保密级别'][index % 12]}</span>
                                            <span className="ml-2 text-xs text-gray-500">{['文本', '文本', '选择项', '日期', '标签', '长文本', '选择项', '文本', '文本', '文本', '数字', '选择项'][index % 12]}</span>
                                        </div>
                                        <div className="flex space-x-2">
                                            <button className="text-gray-400 hover:text-indigo-600">
                                                <PencilIcon size={14} />
                                            </button>
                                            <button className="text-gray-400 hover:text-red-600">
                                                <TrashIcon size={14} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="p-4 border-t">
                                <button className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-md hover:from-indigo-700 hover:to-purple-700 shadow-sm mr-2">
                                    保存模板
                                </button>
                                <button className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50">
                                    导出模板
                                </button>
                            </div>
                        </div>
                    </div>
                );
            }
            return null;

        default:
            return null;
    }
};

export default DetailPanel;