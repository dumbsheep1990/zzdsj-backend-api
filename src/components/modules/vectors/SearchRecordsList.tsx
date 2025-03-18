import React, { FC } from 'react';
import { Search, Clock, BarChart, ExternalLink, Trash2 } from 'lucide-react';
import { SearchRecordItem } from '../../../utils/types';

interface SearchRecordsListProps {
    searchRecords: SearchRecordItem[];
    selectedItem: SearchRecordItem | null;
    setSelectedItem: (item: SearchRecordItem | null) => void;
}

const SearchRecordsList: FC<SearchRecordsListProps> = ({ searchRecords, selectedItem, setSelectedItem }) => {
    return (
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
            <div className="p-4 border-b flex justify-between items-center">
                <div className="text-lg font-medium">u68c0u7d22u8bb0u5f55u5217u8868</div>
                <div className="flex space-x-2">
                    <button className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200">
                        u5bfcu51fau6570u636e
                    </button>
                    <button className="px-3 py-1.5 bg-red-100 text-red-700 rounded-md text-sm hover:bg-red-200">
                        u6e05u9664u8bb0u5f55
                    </button>
                </div>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u68c0u7d22u5185u5bb9</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u65f6u95f4</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u7ed3u679cu6570</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u8017u65f6</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u7528u6237</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u6765u6e90</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">u64cdu4f5c</th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {searchRecords.map((record) => (
                        <tr
                            key={record.id}
                            className={`hover:bg-gray-50 cursor-pointer ${selectedItem?.id === record.id ? 'bg-indigo-50' : ''}`}
                            onClick={() => setSelectedItem(record)}
                        >
                            <td className="px-6 py-4">
                                <div className="flex items-center">
                                    <Search size={18} className="text-indigo-500 mr-2" />
                                    <span className="font-medium">{record.query}</span>
                                </div>
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex items-center">
                                    <Clock size={16} className="text-gray-400 mr-2" />
                                    {record.timestamp}
                                </div>
                            </td>
                            <td className="px-6 py-4">{record.results}</td>
                            <td className="px-6 py-4">{record.duration}</td>
                            <td className="px-6 py-4">{record.user}</td>
                            <td className="px-6 py-4">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${record.source === 'Webu7aef' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}`}>
                                    {record.source}
                                </span>
                            </td>
                            <td className="px-6 py-4">
                                <div className="flex space-x-2">
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <BarChart size={16} />
                                    </button>
                                    <button className="text-gray-400 hover:text-indigo-600">
                                        <ExternalLink size={16} />
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
                    u663eu793a <span className="font-medium">1</span> u81f3 <span className="font-medium">{searchRecords.length}</span> u6761uff0cu5171 <span className="font-medium">{searchRecords.length}</span> u6761
                </div>
                <div className="flex space-x-1">
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">u4e0au4e00u9875</button>
                    <button className="px-3 py-1 border rounded-md bg-indigo-600 text-white">1</button>
                    <button className="px-3 py-1 border rounded-md text-gray-500 hover:bg-gray-50">u4e0bu4e00u9875</button>
                </div>
            </div>
        </div>
    );
};

export default SearchRecordsList;
