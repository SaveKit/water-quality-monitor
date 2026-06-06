import React from "react";
import { FlaskConical, Shield, Clock, TrendingUp } from "lucide-react";

/**
 * FDEICard — Premium card component for displaying Fat Degradation Efficiency Index.
 *
 * Props:
 *   nodeTitle  - Display name for the node
 *   nodeId     - "Node01" or "Node02"
 *   fdei       - FDEI value (0-100%)
 *   co2Cumulative - CO₂ cumulative value (ppm·s)
 *   timestamp  - ISO timestamp string
 *   isForecast - Boolean indicating if this is a forecast value
 */
export default function FDEICard({
  nodeTitle,
  nodeId,
  fdei = 0,
  co2Cumulative = 0,
  timestamp,
  isForecast = false,
}) {
  const clampedFdei = Math.min(100, Math.max(0, fdei));

  // Color tier based on FDEI percentage
  const getColorTier = (value) => {
    if (value >= 70) return "high";
    if (value >= 40) return "mid";
    return "low";
  };

  const tier = getColorTier(clampedFdei);

  const tierConfig = {
    high: {
      text: "text-emerald-400",
      glow: "bg-emerald-500",
      stroke: "url(#gaugeGradientHigh)",
      border: "border-emerald-500/20",
      label: "ประสิทธิภาพสูง",
    },
    mid: {
      text: "text-amber-400",
      glow: "bg-amber-500",
      stroke: "url(#gaugeGradientMid)",
      border: "border-amber-500/20",
      label: "ประสิทธิภาพปานกลาง",
    },
    low: {
      text: "text-rose-400",
      glow: "bg-rose-500",
      stroke: "url(#gaugeGradientLow)",
      border: "border-rose-500/20",
      label: "ประสิทธิภาพต่ำ",
    },
  };

  const cfg = tierConfig[tier];

  // SVG semi-circular gauge calculations
  const radius = 80;
  const strokeWidth = 10;
  const cx = 100;
  const cy = 95;
  // Arc spans 180° (from left to right, bottom-open semicircle)
  const circumference = Math.PI * radius; // half circle
  const fillLength = (clampedFdei / 100) * circumference;
  const dashOffset = circumference - fillLength;

  // Node icon: Flask for sample, Shield for control
  const NodeIcon = nodeId === "Node01" ? FlaskConical : Shield;

  const formattedTime = timestamp
    ? new Date(timestamp).toLocaleString("th-TH", {
        timeZone: "Asia/Bangkok",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
    : "-";

  const formattedCO2 = co2Cumulative
    ? co2Cumulative.toLocaleString("en-US", {
        maximumFractionDigits: 1,
      })
    : "0";

  return (
    <div
      className={`relative overflow-hidden rounded-2xl glass-panel p-6 border transition-all duration-500 hover:shadow-2xl hover:scale-[1.02] ${cfg.border}`}
    >
      {/* Background glow effect */}
      <div
        className={`absolute -right-16 -top-16 w-36 h-36 rounded-full blur-[80px] pointer-events-none opacity-30 ${cfg.glow}`}
      ></div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              nodeId === "Node01"
                ? "bg-cyan-500/10 border border-cyan-500/20"
                : "bg-indigo-500/10 border border-indigo-500/20"
            }`}
          >
            <NodeIcon
              className={`w-5 h-5 ${
                nodeId === "Node01" ? "text-cyan-400" : "text-indigo-400"
              }`}
            />
          </div>
          <div>
            <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
              {nodeId}
            </span>
            <h3 className="text-lg font-bold text-white mt-0.5">
              {nodeTitle}
            </h3>
          </div>
        </div>

        {isForecast ? (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            พยากรณ์ล่วงหน้า
          </span>
        ) : (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            เวลาปัจจุบัน
          </span>
        )}
      </div>

      {/* SVG Semi-Circular Gauge */}
      <div className="flex flex-col items-center mt-4 mb-2">
        <svg
          width="200"
          height="115"
          viewBox="0 0 200 115"
          className="overflow-visible"
        >
          <defs>
            <linearGradient
              id="gaugeGradientHigh"
              x1="0%"
              y1="0%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#34d399" />
            </linearGradient>
            <linearGradient
              id="gaugeGradientMid"
              x1="0%"
              y1="0%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="100%" stopColor="#fbbf24" />
            </linearGradient>
            <linearGradient
              id="gaugeGradientLow"
              x1="0%"
              y1="0%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor="#f43f5e" />
              <stop offset="100%" stopColor="#fb7185" />
            </linearGradient>
          </defs>

          {/* Background track */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="rgba(51, 65, 85, 0.3)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Filled arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke={cfg.stroke}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className="transition-all duration-1000 ease-out"
          />

          {/* FDEI percentage text */}
          <text
            x={cx}
            y={cy - 20}
            textAnchor="middle"
            className={`text-4xl font-extrabold ${cfg.text}`}
            fill="currentColor"
            style={{ fontFamily: "Sarabun, sans-serif" }}
          >
            {clampedFdei.toFixed(1)}
          </text>
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            fill="rgb(148, 163, 184)"
            style={{
              fontSize: "12px",
              fontWeight: 600,
              fontFamily: "Sarabun, sans-serif",
            }}
          >
            FDEI (%)
          </text>
        </svg>
      </div>

      {/* Status Badge */}
      <div className="flex items-center justify-center gap-2 mb-4">
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${cfg.border} bg-slate-900/40`}
        >
          <span
            className={`w-2 h-2 rounded-full ${cfg.glow} ${
              tier === "low" ? "animate-pulse" : ""
            }`}
          ></span>
          <span className={`text-xs font-bold ${cfg.text}`}>{cfg.label}</span>
        </div>
      </div>

      {/* CO₂ Cumulative Badge */}
      <div className="bg-slate-800/30 rounded-xl p-3 border border-slate-800/50">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
            CO₂ Cumulative (สะสม)
          </span>
          <span className="text-sm font-bold text-white">
            {formattedCO2}{" "}
            <span className="text-[10px] text-slate-400 font-semibold">
              ppm·s
            </span>
          </span>
        </div>
      </div>

      {/* Footer Timestamp */}
      <div className="mt-4 flex items-center gap-1.5 text-[10px] text-slate-500">
        <Clock className="w-3 h-3" />
        <span>อัปเดตล่าสุด: {formattedTime}</span>
      </div>
    </div>
  );
}
