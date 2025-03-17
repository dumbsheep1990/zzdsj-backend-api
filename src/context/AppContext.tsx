import React, { createContext, useContext, useState, ReactNode } from 'react';
import { AppState } from '../utils/types';

// 创建上下文的默认值
const defaultState: AppState = {
    activeSection: 'files',
    sidebarExpanded: true,
    darkMode: false
};

// 创建上下文类型
interface AppContextType {
    state: AppState;
    setActiveSection: (section: string) => void;
    toggleSidebar: () => void;
    toggleDarkMode: () => void;
}

// 创建上下文
const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [state, setState] = useState<AppState>(defaultState);

    // 更新当前活动栏目
    const setActiveSection = (section: string) => {
        setState(prev => ({ ...prev, activeSection: section }));
    };

    // 切换侧边栏展开状态
    const toggleSidebar = () => {
        setState(prev => ({ ...prev, sidebarExpanded: !prev.sidebarExpanded }));
    };

    // 切换暗黑模式
    const toggleDarkMode = () => {
        setState(prev => ({ ...prev, darkMode: !prev.darkMode }));
    };

    return (
        <AppContext.Provider value={{ state, setActiveSection, toggleSidebar, toggleDarkMode }}>
            {children}
        </AppContext.Provider>
    );
};

export const useAppContext = () => {
    const context = useContext(AppContext);
    if (context === undefined) {
        throw new Error('useAppContext must be used within an AppProvider');
    }
    return context;
};