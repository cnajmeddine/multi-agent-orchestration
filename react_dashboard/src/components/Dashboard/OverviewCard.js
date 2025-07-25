import React from 'react';

const OverviewCard = ({ title, value, change, icon }) => {
  return (
    <div className="gradient-bg rounded-xl border border-slate-700 p-6 neon-glow-hover transition-all duration-300">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-400 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {change && (
            <p className={`text-sm mt-2 ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {change >= 0 ? '+' : ''}{change}% from last hour
            </p>
          )}
        </div>
        {icon && (
          <div className="text-cyan-400">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};

export default OverviewCard;