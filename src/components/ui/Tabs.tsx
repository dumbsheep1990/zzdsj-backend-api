import React from 'react';

interface TabsContainerProps {
    children: React.ReactNode;
}

interface TabButtonProps {
    children: React.ReactNode;
    active: boolean;
    onClick: () => void;
}

export const TabsContainer: React.FC<TabsContainerProps> = ({ children }) => {
    return (
        <div className="flex border-b border-gray-200 mb-4">
            {children}
        </div>
    );
};

export const TabButton: React.FC<TabButtonProps> = ({ children, active, onClick }) => {
    return (
        <button
            className={`px-4 py-2 font-medium text-sm rounded-md mr-2 ${active ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:text-gray-800'}`}
            onClick={onClick}
        >
            {children}
        </button>
    );
};
