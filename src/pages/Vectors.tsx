import React, { useState } from 'react';
import VectorsHeader from '../components/modules/vectors/VectorsHeader';
import VectorsList from '../components/modules/vectors/VectorsList';
import DetailPanel from '../components/layout/DetailPanel';
import { vectorData } from '../utils/mockData';
import { VectorItem } from '../utils/types';

const Vectors: React.FC = () => {
    const [selectedItem, setSelectedItem] = useState<VectorItem | null>(null);

    return (
        <div className="flex-1 flex overflow-hidden">
            <div className={`${selectedItem ? 'w-1/2' : 'w-full'} overflow-auto transition-all duration-300 p-6`}>
                <h1 className="text-2xl font-semibold mb-6">向量化管理</h1>

                <VectorsHeader vectors={vectorData} />

                <VectorsList
                    vectors={vectorData}
                    selectedItem={selectedItem}
                    setSelectedItem={setSelectedItem}
                />
            </div>

            {selectedItem && (
                <div className="w-1/2 border-l bg-white overflow-auto transition-all duration-300">
                    <DetailPanel
                        selectedItem={selectedItem}
                        setSelectedItem={setSelectedItem}
                        activeSection="vectors"
                    />
                </div>
            )}
        </div>
    );
};

export default Vectors;