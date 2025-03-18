import React, { useState, useMemo } from 'react';
import FilesHeader from '../components/modules/files/FilesHeader';
import FilesList from '../components/modules/files/FilesList';
import DetailPanel from '../components/layout/DetailPanel';
import { fileData } from '../utils/mockData';
import { FileItem } from '../utils/types';

const Files: React.FC = () => {
    const [selectedItem, setSelectedItem] = useState<FileItem | null>(null);
    const [activeCategory, setActiveCategory] = useState<string>('all');

    // 从文件数据中提取所有唯一的类别
    const categories = useMemo(() => {
        const uniqueCategories = new Set(fileData.map(file => file.category));
        return ['all', ...Array.from(uniqueCategories)];
    }, []);

    // 样式定义
    const containerStyle = {
        flex: 1,
        display: 'flex',
        overflow: 'hidden'
    };

    const mainContentStyle = {
        width: selectedItem ? 'calc(100% - 384px)' : '100%',
        overflow: 'auto',
        transition: 'width 0.3s ease',
        padding: '1.5rem'
    };

    const categoryTabStyle = {
        display: 'flex',
        marginBottom: '1rem',
        borderBottom: '1px solid #e5e7eb',
        overflow: 'auto'
    };

    const tabItemStyle = (isActive: boolean) => ({
        padding: '0.75rem 1.25rem',
        cursor: 'pointer',
        borderBottom: isActive ? '2px solid #4f46e5' : '2px solid transparent',
        color: isActive ? '#4f46e5' : '#6b7280',
        fontWeight: isActive ? 600 : 400,
        whiteSpace: 'nowrap' as const
    });

    const filteredFiles = activeCategory === 'all' 
        ? fileData 
        : fileData.filter(file => file.category === activeCategory);

    return (
        <div style={containerStyle}>
            <div style={mainContentStyle}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '1.5rem' }}>文件管理</h1>

                <FilesHeader files={filteredFiles} />

                {/* 类别选项卡 */}
                <div style={categoryTabStyle}>
                    {categories.map((category) => (
                        <div 
                            key={category} 
                            style={tabItemStyle(activeCategory === category)}
                            onClick={() => setActiveCategory(category)}
                        >
                            {category === 'all' ? '全部文件' : category}
                            {category === 'all' 
                                ? ` (${fileData.length})` 
                                : ` (${fileData.filter(f => f.category === category).length})`}
                        </div>
                    ))}
                </div>

                <FilesList 
                    files={filteredFiles} 
                    selectedItem={selectedItem} 
                    setSelectedItem={setSelectedItem} 
                />
            </div>

            {selectedItem && (
                <div className="fixed right-0 top-0 h-screen z-10">
                    <DetailPanel 
                        selectedItem={selectedItem} 
                        onClose={() => setSelectedItem(null)}
                    />
                </div>
            )}
        </div>
    );
};

export default Files;