import React from 'react';
import { Database, ChevronRight, FileText, Code, Grid, Settings, Tag } from 'lucide-react';
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
        case 'Tag':
            return <Tag size={size} />;
        default:
            return <FileText size={size} />;
    }
};

const Sidebar: React.FC = () => {
    const { state, setActiveSection, toggleSidebar } = useAppContext();
    const { activeSection, sidebarExpanded } = state;

    const sidebarStyle = {
        background: 'linear-gradient(180deg, #f0f9ff 0%, #e6f7ff 50%, #dcf2ff 100%)',
        borderRight: '1px solid #e5e7eb',
        width: sidebarExpanded ? '16rem' : '5rem',
        display: 'flex',
        flexDirection: 'column' as const,
        transition: 'width 0.3s ease'
    };

    const logoContainerStyle = {
        display: 'flex',
        alignItems: 'center',
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb'
    };

    const navStyle = {
        flex: 1,
        paddingTop: '1rem',
        paddingBottom: '1rem'
    };

    const navItemStyle = (isActive: boolean) => ({
        display: 'flex',
        alignItems: 'center',
        width: '100%',
        padding: '0.75rem 1rem',
        backgroundColor: isActive ? '#eff6ff' : 'transparent',
        color: isActive ? '#2563eb' : '#4b5563',
        borderRight: isActive ? '4px solid #2563eb' : 'none',
        cursor: 'pointer'
    });

    const iconContainerStyle = {
        display: 'flex',
        alignItems: 'center'
    };

    const footerStyle = {
        padding: '1rem',
        borderTop: '1px solid #e5e7eb'
    };

    return (
        <div style={sidebarStyle}>
            {/* 顶部Logo */}
            <div style={logoContainerStyle}>
                <Database color="#2563eb" style={{ marginRight: '0.5rem' }} size={24} />
                {sidebarExpanded && <h1 style={{ fontSize: '1.125rem', fontWeight: 600 }}>智政知脑</h1>}
                <button
                    style={{ marginLeft: 'auto', color: '#9ca3af', cursor: 'pointer' }}
                    onClick={toggleSidebar}
                >
                    <ChevronRight size={20} style={{ 
                        transform: sidebarExpanded ? 'none' : 'rotate(180deg)',
                        transition: 'transform 0.3s ease'
                    }} />
                </button>
            </div>

            {/* 导航菜单 */}
            <nav style={navStyle}>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                    {navigationItems.map((item) => (
                        <li key={item.id}>
                            <button
                                style={navItemStyle(activeSection === item.id)}
                                onClick={() => setActiveSection(item.id)}
                            >
                <span style={iconContainerStyle}>
                  {getIconByType(item.iconType)}
                    {sidebarExpanded && <span style={{ marginLeft: '0.75rem' }}>{item.label}</span>}
                </span>
                            </button>
                        </li>
                    ))}
                </ul>
            </nav>

            {/* 底部用户信息 */}
            <div style={footerStyle}>
                {sidebarExpanded ? (
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{ 
                            width: '2rem', 
                            height: '2rem', 
                            borderRadius: '9999px', 
                            backgroundColor: '#2563eb',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white'
                        }}>
                            A
                        </div>
                        <div style={{ marginLeft: '0.75rem' }}>
                            <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>管理员</div>
                            <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>admin@example.com</div>
                        </div>
                    </div>
                ) : (
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                        <div style={{ 
                            width: '2.5rem', 
                            height: '2.5rem', 
                            borderRadius: '9999px', 
                            backgroundColor: '#2563eb',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white'
                        }}>
                            A
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Sidebar;