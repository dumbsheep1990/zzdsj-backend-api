// 定义应用中使用的类型

// 文件类型
export interface FileItem {
    id: number;
    name: string;
    type: string;
    size: string;
    date: string;
    status: string;
    category: string;
}

// 模型类型
export interface ModelItem {
    id: number;
    name: string;
    type: string;
    status: string;
    lastUsed: string;
    provider: string;
    version: string;
    usageCount: number;
}

// 向量库类型
export interface VectorItem {
    id: number;
    name: string;
    fileCount: number;
    lastUpdated: string;
    size: string;
    status: string;
}

// 元数据模板类型
export interface MetadataItem {
    id: number;
    name: string;
    fields: number;
    lastUpdated: string;
    usage: string;
}

// 导航项类型
export interface NavItem {
    id: string;
    label: string;
    iconType: string; // 改为使用图标类型字符串
}

// 统计卡片类型
export interface StatsCardProps {
    icon: React.ReactNode;
    title: string;
    value: string | number;
    color: string;
    bgGradient: string;
}

// 通用详情面板Props
export interface DetailPanelProps {
    selectedItem: FileItem | ModelItem | VectorItem | MetadataItem | null;
    setSelectedItem: React.Dispatch<React.SetStateAction<any | null>>;
    activeSection: string;
}

// 应用全局状态
export interface AppState {
    activeSection: string;
    sidebarExpanded: boolean;
    darkMode: boolean;
}