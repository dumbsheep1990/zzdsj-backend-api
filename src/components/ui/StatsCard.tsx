import React, { FC } from 'react';
import { StatsCardProps } from '../../utils/types';

const StatsCard: FC<StatsCardProps> = ({ icon, title, value, color, bgGradient }) => {
    return (
        <div className={`${bgGradient} rounded-xl p-4 border`}>
            <div className="flex justify-between items-start">
                <div>
                    <p className="text-sm text-gray-500 mb-1">{title}</p>
                    <p className="text-2xl font-bold">{value}</p>
                </div>
                <div className={`p-2 rounded-lg ${color}`}>
                    {icon}
                </div>
            </div>
        </div>
    );
};

export default StatsCard;