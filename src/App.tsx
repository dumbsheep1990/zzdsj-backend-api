import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import Files from './pages/Files';
import Models from './pages/Models';
import Vectors from './pages/Vectors';
import { AppProvider, useAppContext } from './context/AppContext';

const AppContent: React.FC = () => {
    const { state } = useAppContext();
    const { activeSection } = state;

    const renderContent = () => {
        switch (activeSection) {
            case 'files':
                return <Files />;
            case 'models':
                return <Models />;
            case 'vectors':
                return <Vectors />;
            case 'metadata':
                return <div className="flex-1 p-6"><h1 className="text-2xl font-semibold">元数据管理（开发中）</h1></div>;
            case 'settings':
                return <div className="flex-1 p-6"><h1 className="text-2xl font-semibold">系统设置（开发中）</h1></div>;
            default:
                return <Files />;
        }
    };

    return (
        <div className="flex h-screen bg-gray-100">
            <Sidebar />

            {renderContent()}
        </div>
    );
};

const App: React.FC = () => {
    return (
        <AppProvider>
            <Router>
                <AppContent />
            </Router>
        </AppProvider>
    );
};

export default App;