import React from 'react';

const statusColors = {
  healthy: 'text-green-400 bg-green-400/20',
  running: 'text-green-400 bg-green-400/20',
  degraded: 'text-yellow-400 bg-yellow-400/20',
  unhealthy: 'text-red-400 bg-red-400/20',
  unreachable: 'text-gray-400 bg-gray-400/20',
  unknown: 'text-gray-400 bg-gray-400/20'
};

const ServiceStatus = ({ name, status, responseTime }) => {
  const statusColor = statusColors[status] || statusColors.unknown;

  return (
    <div className="gradient-bg rounded-lg border border-slate-700 p-4 mb-3 neon-glow-hover transition-all duration-300">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${statusColor}`}></div>
          <span className="text-white font-medium">{name}</span>
        </div>
        <div className="flex items-center space-x-4">
          {responseTime && (
            <span className="text-slate-400 text-sm">{responseTime}ms</span>
          )}
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColor}`}>
            {status}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ServiceStatus;