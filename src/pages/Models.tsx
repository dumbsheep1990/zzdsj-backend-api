import React, { useState, FC } from 'react';
import ModelsHeader from '../components/modules/models/ModelsHeader';
import ModelsList from '../components/modules/models/ModelsList';
import DetailPanel from '../components/layout/DetailPanel';
import { modelData } from '../utils/mockData';
import { ModelItem } from '../utils/types';

const Models: FC = () => {
    const [selectedItem, setSelectedItem] = useState<ModelItem | null>(null);

    // 容器样式
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

    return (
        <div style={containerStyle}>
            <div style={mainContentStyle}>
                <h1 className="text-2xl font-semibold mb-6">模型管理</h1>

                <ModelsHeader models={modelData} />

                <ModelsList
                    models={modelData}
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

export default Models;