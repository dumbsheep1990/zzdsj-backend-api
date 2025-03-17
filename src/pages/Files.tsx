import React, { useState } from 'react';
import FilesHeader from '../components/modules/files/FilesHeader';
import FilesList from '../components/modules/files/FilesList';
import DetailPanel from '../components/layout/DetailPanel';
import { fileData } from '../utils/mockData';
import { FileItem } from '../utils/types';

const Files: React.FC = () => {
    const [selectedItem, setSelectedItem] = useState<FileItem | null>(null);

    return (
        <div className="flex-1 flex overflow-hidden">
            <div className={`${selectedItem ? 'w-1/2' : 'w-full'} overflow-auto transition-all duration-300 p-6`}>
                <h1 className="text-2xl font-semibold mb-6">文件管理</h1>

                <FilesHeader files={fileData} />

                <FilesList
                    files={fileData}
                    selectedItem={selectedItem}
                    setSelectedItem={setSelectedItem}
                />
            </div>

            {selectedItem && (
                <div className="w-1/2 border-l bg-white overflow-auto transition-all duration-300">
                    <DetailPanel
                        selectedItem={selectedItem}
                        setSelectedItem={setSelectedItem}
                        activeSection="files"
                    />
                </div>
            )}
        </div>
    );
};

export default Files;