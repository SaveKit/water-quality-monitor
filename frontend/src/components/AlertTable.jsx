import React from "react";
import { WQI_CONFIG } from "../utils/wqi";
import { AlertCircle, Flame, Calendar } from "lucide-react";

export default function AlertTable({ alerts }) {
  const getSeverityIcon = (status) => {
    if (status === "CRITICAL") {
      return <Flame className="w-5 h-5 text-rose-400 animate-pulse" />;
    }
    return <AlertCircle className="w-5 h-5 text-orange-400" />;
  };

  return (
    <div className="rounded-2xl glass-panel border border-slate-800/80 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-800/60">
        <h3 className="text-base font-bold text-white">บันทึกเหตุการณ์การแจ้งเตือนสภาวะน้ำเสีย</h3>
        <p className="text-xs text-slate-400 mt-0.5">ประวัติรายการเมื่อพยากรณ์คุณภาพน้ำได้ค่า WQI &gt; 75 (แย่มาก หรือ ไม่เหมาะสมอย่างยิ่ง)</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800/40 text-xs text-slate-400 font-bold uppercase bg-slate-900/20">
              <th className="py-4 px-6">วัน-เวลาเกิดเหตุ</th>
              <th className="py-4 px-6">จุดตรวจวัด (Node ID)</th>
              <th className="py-4 px-4 text-center">ดัชนี WQI</th>
              <th className="py-4 px-4 text-center">ระดับความรุนแรง</th>
              <th className="py-4 px-6 text-right">มาตรการที่ต้องดำเนินการบำบัด</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/30 text-sm font-medium">
            {alerts.map((alert, index) => {
              const cfg = WQI_CONFIG[alert.status] || WQI_CONFIG.GOOD;
              const formattedTime = new Date(alert.timestamp).toLocaleString("th-TH", {
                timeZone: "Asia/Bangkok",
                year: "numeric",
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
              });

              return (
                <tr key={index} className="hover:bg-slate-800/10 transition-colors duration-200">
                  <td className="py-4 px-6 text-slate-300">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-slate-500" />
                      <span>{formattedTime}</span>
                    </div>
                  </td>
                  
                  <td className="py-4 px-6 text-white font-bold">
                    {alert.node_id}
                  </td>
                  
                  <td className="py-4 px-4 text-center">
                    <span className={`text-base font-extrabold ${cfg.text}`}>
                      {alert.wqi_value.toFixed(1)}
                    </span>
                  </td>

                  <td className="py-4 px-4 text-center">
                    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold leading-none bg-slate-950/40 border-slate-800">
                      {getSeverityIcon(alert.status)}
                      <span className={cfg.text}>{cfg.label}</span>
                    </div>
                  </td>
                  
                  <td className="py-4 px-6 text-right text-slate-200">
                    <span className="bg-rose-500/10 text-rose-300 border border-rose-500/10 px-3 py-1 rounded-xl text-xs font-bold">
                      {alert.recommendation}
                    </span>
                  </td>
                </tr>
              );
            })}

            {alerts.length === 0 && (
              <tr>
                <td colSpan="5" className="py-12 px-6 text-center text-slate-500 font-semibold">
                  ไม่มีประวัติการแจ้งเตือนภัยในระบบ
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
