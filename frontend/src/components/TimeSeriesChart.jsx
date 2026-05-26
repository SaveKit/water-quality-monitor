import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

export default function TimeSeriesChart({ dataNode01, dataNode02, parameterLabel, unit }) {
  // Merge historical data of both nodes by timestamp
  const mergedDataMap = {};

  dataNode01.forEach((pt) => {
    const timeStr = new Date(pt.timestamp).toLocaleTimeString("th-TH", {
      hour: "2-digit",
      minute: "2-digit"
    });
    const dateStr = new Date(pt.timestamp).toLocaleDateString("th-TH", {
      day: "2-digit",
      month: "short"
    });
    const key = new Date(pt.timestamp).getTime();
    
    mergedDataMap[key] = {
      timestamp: key,
      formattedTime: `${dateStr} ${timeStr}`,
      Node01: pt.value,
      Node02: null
    };
  });

  dataNode02.forEach((pt) => {
    const timeStr = new Date(pt.timestamp).toLocaleTimeString("th-TH", {
      hour: "2-digit",
      minute: "2-digit"
    });
    const dateStr = new Date(pt.timestamp).toLocaleDateString("th-TH", {
      day: "2-digit",
      month: "short"
    });
    const key = new Date(pt.timestamp).getTime();

    if (mergedDataMap[key]) {
      mergedDataMap[key].Node02 = pt.value;
    } else {
      mergedDataMap[key] = {
        timestamp: key,
        formattedTime: `${dateStr} ${timeStr}`,
        Node01: null,
        Node02: pt.value
      };
    }
  });

  // Convert map to sorted array
  const chartData = Object.values(mergedDataMap).sort((a, b) => a.timestamp - b.timestamp);

  // Custom Glassmorphic Tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="glass-panel border border-slate-700/80 p-4 rounded-xl shadow-xl">
          <p className="text-xs font-semibold text-slate-400 mb-2">{payload[0].payload.formattedTime}</p>
          {payload.map((item) => (
            <div key={item.name} className="flex items-center justify-between gap-6 text-sm py-0.5">
              <span style={{ color: item.color }} className="font-bold">
                {item.name === "Node01" ? "จุดตรวจวัดที่ 1" : "จุดตรวจวัดที่ 2"}
              </span>
              <span className="font-extrabold text-white">
                {item.value !== null ? `${item.value.toFixed(2)} ${unit}` : "-"}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.5} />
          
          <XAxis 
            dataKey="formattedTime" 
            stroke="#64748b" 
            fontSize={10}
            tickLine={false}
            dy={10}
            fontFamily="Sarabun"
          />
          
          <YAxis 
            stroke="#64748b" 
            fontSize={10}
            tickLine={false}
            dx={-5}
            fontFamily="Sarabun"
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          <Legend 
            verticalAlign="top" 
            height={36} 
            iconType="circle"
            iconSize={8}
            wrapperStyle={{
              fontFamily: "Sarabun",
              fontSize: "12px",
              fontWeight: "600",
              color: "#94a3b8"
            }}
            formatter={(value) => (value === "Node01" ? "จุดตรวจวัดที่ 1 (สจล.)" : "จุดตรวจวัดที่ 2 (สจล.)")}
          />
          
          {/* Node 1 Line (Cyan gradient-style) */}
          <Line
            name="Node01"
            type="monotone"
            dataKey="Node01"
            stroke="#06b6d4"
            strokeWidth={3}
            dot={chartData.length < 50 ? { stroke: "#06b6d4", strokeWidth: 1, r: 3, fill: "#0891b2" } : false}
            activeDot={{ r: 5, strokeWidth: 0, fill: "#22d3ee" }}
            connectNulls
          />

          {/* Node 2 Line (Indigo gradient-style) */}
          <Line
            name="Node02"
            type="monotone"
            dataKey="Node02"
            stroke="#6366f1"
            strokeWidth={3}
            dot={chartData.length < 50 ? { stroke: "#6366f1", strokeWidth: 1, r: 3, fill: "#4f46e5" } : false}
            activeDot={{ r: 5, strokeWidth: 0, fill: "#818cf8" }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
