import React, { useState } from 'react';
import { TabsContainer, TabButton } from '../components/ui/Tabs';
import VectorsList from '../components/modules/vectors/VectorsList';
import KeywordsList from '../components/modules/vectors/KeywordsList';
import SearchRecordsList from '../components/modules/vectors/SearchRecordsList';
import DetailPanel from '../components/layout/DetailPanel';
import { vectorData, keywordsData, searchRecordsData } from '../utils/mockData';
import { VectorItem, KeywordItem, SearchRecordItem } from '../utils/types';

const Vectors: React.FC = () => {
    const [activeModule, setActiveModule] = useState<'vectors' | 'keywords' | 'searchRecords'>('vectors');
    const [selectedVector, setSelectedVector] = useState<VectorItem | null>(null);
    const [selectedKeyword, setSelectedKeyword] = useState<KeywordItem | null>(null);
    const [selectedSearchRecord, setSelectedSearchRecord] = useState<SearchRecordItem | null>(null);

    // 获取当前选中的项目（根据当前活动模块）
    const getSelectedItem = () => {
        switch (activeModule) {
            case 'vectors':
                return selectedVector;
            case 'keywords':
                return selectedKeyword;
            case 'searchRecords':
                return selectedSearchRecord;
            default:
                return null;
        }
    };

    // 设置当前选中的项目（根据当前活动模块）
    const setSelectedItem = (item: VectorItem | KeywordItem | SearchRecordItem | null) => {
        switch (activeModule) {
            case 'vectors':
                setSelectedVector(item as VectorItem | null);
                break;
            case 'keywords':
                setSelectedKeyword(item as KeywordItem | null);
                break;
            case 'searchRecords':
                setSelectedSearchRecord(item as SearchRecordItem | null);
                break;
        }
    };

    // 渲染不同模块的内容
    const renderModuleContent = () => {
        switch (activeModule) {
            case 'vectors':
                return (
                    <VectorsList 
                        vectors={vectorData} 
                        selectedItem={selectedVector} 
                        setSelectedItem={setSelectedVector} 
                    />
                );
            case 'keywords':
                return (
                    <KeywordsList 
                        keywords={keywordsData} 
                        selectedItem={selectedKeyword} 
                        setSelectedItem={setSelectedKeyword} 
                    />
                );
            case 'searchRecords':
                return (
                    <SearchRecordsList 
                        searchRecords={searchRecordsData} 
                        selectedItem={selectedSearchRecord} 
                        setSelectedItem={setSelectedSearchRecord} 
                    />
                );
            default:
                return null;
        }
    };

    // 样式定义
    const containerStyle = {
        flex: 1,
        display: 'flex',
        overflow: 'hidden'
    };

    const mainContentStyle = {
        width: getSelectedItem() ? '50%' : '100%',
        overflow: 'auto',
        transition: 'width 0.3s ease',
        padding: '1.5rem'
    };

    const detailPanelStyle = {
        width: '50%',
        borderLeft: '1px solid #e5e7eb',
        backgroundColor: 'white',
        overflow: 'auto',
        transition: 'all 0.3s ease'
    };

    return (
        <div style={containerStyle}>
            <div style={mainContentStyle}>
                <h1 className="text-2xl font-bold mb-6">向量数据库管理</h1>
                <p className="text-gray-600 mb-6">管理向量数据、关键词和搜索记录</p>

                <TabsContainer>
                    <TabButton 
                        active={activeModule === 'vectors'} 
                        onClick={() => setActiveModule('vectors')}
                    >
                        向量数据
                    </TabButton>
                    <TabButton 
                        active={activeModule === 'keywords'} 
                        onClick={() => setActiveModule('keywords')}
                    >
                        关键词管理
                    </TabButton>
                    <TabButton 
                        active={activeModule === 'searchRecords'} 
                        onClick={() => setActiveModule('searchRecords')}
                    >
                        搜索记录
                    </TabButton>
                </TabsContainer>

                <div className="mt-6">
                    {renderModuleContent()}
                </div>
            </div>

            {getSelectedItem() && (
                <div style={detailPanelStyle}>
                    <DetailPanel 
                        selectedItem={getSelectedItem()} 
                        setSelectedItem={setSelectedItem}
                        activeSection="vectors"
                    />
                </div>
            )}
        </div>
    );
};

export default Vectors;