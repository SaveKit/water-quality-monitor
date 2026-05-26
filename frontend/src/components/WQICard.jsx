import React from "react";
import { WQI_CONFIG, TREATMENT_LABELS, getWQIStatus } from "../utils/wqi";
import { AlertCircle, CheckCircle, Flame, Shield } from "lucide-react";

export default function WQICard({ nodeTitle, nodeId, wqi, timestamp, isForecast = false }) {
  const statusKey = getWQIStatus(wqi);
  const cfg = WQI_CONFIG[statusKey];
  const treatment = TREATMENT_LABELS[statusKey];
  
  const formattedTime = timestamp 
    ? new Date(timestamp).toLocaleString("th-TH", {
        timeZone: "Asia/Bangkok",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        day: "2-digit",
        month: "short"
      })
    : "-";

  // Status-specific icons
  const getStatusIcon = () => {
    switch (statusKey) {
      case "GOOD":
        return <Shield className="w-5 h-5 text-emerald-400" />;
      case "FAIR":
        return <CheckCircle className="w-5 h-5 text-amber-400" />;
      case "POOR":
        return <AlertCircle className="w-5 h-5 text-orange-400" />;
      case "CRITICAL":
        return <Flame className="w-5 h-5 text-rose-400 pulse-glow" />;
      default:
        return null;
    }
  };

  return (
    <div className={`relative overflow-hidden rounded-2xl glass-panel p-6 border transition-all duration-500 hover:shadow-2xl hover:scale-[1.02] ${cfg.border}`}>
      {/* Background glow shadow effect based on status */}
      <div className={`absolute -right-16 -top-16 w-36 h-36 rounded-full blur-[80px] pointer-events-none opacity-40 ${
        statusKey === "GOOD" ? "bg-emerald-500" :
        statusKey === "FAIR" ? "bg-amber-500" :
        statusKey === "POOR" ? "bg-orange-500" : "bg-rose-500"
      }`}></div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
            {nodeId}
          </span>
          <h3 className="text-lg font-bold text-white mt-0.5">{nodeTitle}</h3>
        </div>
        
        {isForecast ? (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
            พยากรณ์ล่วงหน้า
          </span>
        ) : (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            เวลาปัจจุบัน
          </span>
        )}
      </div>

      {/* WQI Value Display */}
      <div className="my-6 flex items-baseline gap-4">
        <div>
          <span className={`text-6xl font-extrabold tracking-tight ${cfg.text}`}>
            {wqi}
          </span>
          <span className="text-slate-400 font-semibold ml-2 text-sm">WQI</span>
        </div>
      </div>

      {/* Status Badge */}
      <div className="flex items-center gap-2 mt-2">
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${cfg.bg} ${cfg.border}`}>
          {getStatusIcon()}
          <span className={`text-xs font-bold ${cfg.text}`}>{cfg.label}</span>
        </div>
      </div>

      {/* Details & Recommendation */}
      <div className="mt-5 pt-4 border-t border-slate-800/50">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-slate-400 font-medium">ระดับการบำบัดที่จำเป็น</span>
          <span className="text-sm font-semibold text-white">{treatment}</span>
        </div>
      </div>

      {/* Footer Timestamp */}
      <div className="mt-4 flex items-center justify-between text-[10px] text-slate-500">
        <span>อัปเดตล่าสุด: {formattedTime}</span>
        
        <button className={`px-4 py-2 rounded-xl text-xs font-bold transition-all duration-300 ${cfg.btn}`}>
          {statusKey === "GOOD" || statusKey === "FAIR" ? "ตรวจบำรุงรักษา" : "เริ่มดำเนินการบำบัด"}
        </button>
      </div>
    </div>
  );
}
