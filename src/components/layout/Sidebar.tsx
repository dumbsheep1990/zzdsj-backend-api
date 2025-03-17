import React from 'react';
import { Database, ChevronRight, FileText, Code, Grid, Settings } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import { navigationItems } from '../../utils/mockData';

const getIconByType = (iconType: string, size: number = 20) => {
    switch (iconType) {
        case 'FileText':
            return <FileText size={size} />;
        case 'Code':
            return <Code size={size} />;
        case 'Grid':
            return <Grid size={size} />;
        case 'Database':
            return <Database size={size} />;
        case 'Settings':
            return <Settings size={size} />;
        default:
            return <FileText size={size} />;
    }
};

const Sidebar: React.FC = () => {
    const { state, setActiveSection, toggleSidebar } = useAppContext();
    const { activeSection, sidebarExpanded } = state;

    return (
        <div className={`bg-white border-r ${sidebarExpanded ? 'w-64' : 'w-20'} flex flex-col transition-all duration-300`}>
            {/* 顶部Logo */}
            <div className="flex items-center p-4 border-b">
                <Database className="text-blue-600 mr-2" size={24} />
                {sidebarExpanded && <h1 className="text-lg font-semibold">智政知脑</h1>}
                <button
                    className="ml-auto text-gray-400 hover:text-gray-600"
                    onClick={toggleSidebar}
                >
                    <ChevronRight size={20} className={`transform transition-transform ${sidebarExpanded ? '' : 'rotate-180'}`} />
                </button>
            </div>

            {/* 导航菜单 */}
            <nav className="flex-1 py-4">
                <ul>
                    {navigationItems.map((item) => (
                        <li key={item.id}>
                            <button
                                className={`flex items-center w-full px-4 py-3 ${
                                    activeSection === item.id
                                        ? 'bg-blue-50 text-blue-600 border-r-4 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                }`}
                                onClick={() => setActiveSection(item.id)}
                            >
                <span className="flex items-center">
                  {getIconByType(item.iconType)}
                    {sidebarExpanded && <span className="ml-3">{item.label}</span>}
                </span>
                            </button>
                        </li>
                    ))}
                </ul>
            </nav>

            {/* 底部用户信息 */}
            <div className="p-4 border-t">
                {sidebarExpanded ? (
                    <div className="flex items-center">
                        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
                            A
                        </div>
                        <div className="ml-3">
                            <div className="text-sm font-medium">管理员</div>
                            <div className="text-xs text-gray-500">admin@example.com</div>
                        </div>
                    </div>
                ) : (
                    <div className="flex justify-center">
                        <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white">
                            A
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Sidebar;