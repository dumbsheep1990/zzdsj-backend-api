import React, { useState } from 'react';
import ModelsHeader from '../components/modules/models/ModelsHeader';
import ModelsList from '../components/modules/models/ModelsList';
import DetailPanel from '../components/layout/DetailPanel';
import { modelData } from '../utils/mockData';
import { ModelItem } from '../utils/types';

const Models: React.FC = () => {
    const [selectedItem, setSelectedItem] = useState<ModelItem | null>(null);

    return (
        <div className="flex-1 flex overflow-hidden">
            <div className={`${selectedItem ? 'w-1/2' : 'w-full'} overflow-auto transition-all duration-300 p-6`}>
                <h1 className="text-2xl font-semibold mb-6">模型管理</h1>

                <ModelsHeader models={modelData} />

                <ModelsList
                    models={modelData}
                    selectedItem={selectedItem}
                    setSelectedItem={setSelectedItem}
                />
            </div>

            {selectedItem && (
                <div className="w-1/2 border-l bg-white overflow-auto transition-all duration-300">
                    <DetailPanel
                        selectedItem={selectedItem}
                        setSelectedItem={setSelectedItem}
                        activeSection="models"
                    />
                </div>
            )}
        </div>
    );
};

export default Models;