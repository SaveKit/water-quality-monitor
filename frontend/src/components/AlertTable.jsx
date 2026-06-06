import React from "react";
import { ALERT_TYPE_CONFIG } from "../utils/fdei";
import { AlertCircle, Calendar } from "lucide-react";

export default function AlertTable({ alerts }) {
  return (
    <div className="rounded-2xl glass-panel border border-slate-800/80 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-800/60">
        <h3 className="text-base font-bold text-white">บันทึกเหตุการณ์การแจ้งเตือนการย่อยสลายไขมัน</h3>
        <p className="text-xs text-slate-400 mt-0.5">ประวัติรายการเมื่อกิจกรรมการย่อยสลาย FOG มีแนวโน้มชะลอตัว ผิดปกติ หรือถึงเป้าหมาย FDEI</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800/40 text-xs text-slate-400 font-bold uppercase bg-slate-900/20">
              <th className="py-4 px-6">วัน-เวลาเกิดเหตุ</th>
              <th className="py-4 px-6">ถังปฏิกรณ์ (Node ID)</th>
              <th className="py-4 px-4 text-center">ค่า FDEI (%)</th>
              <th className="py-4 px-4 text-center">ประเภทการแจ้งเตือน</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/30 text-sm font-medium">
            {alerts.map((alert, index) => {
              const alertCfg = ALERT_TYPE_CONFIG[alert.alert_type] || ALERT_TYPE_CONFIG.ABNORMAL;
              const formattedTime = new Date(alert.timestamp).toLocaleString("th-TH", {
                timeZone: "Asia/Bangkok",
                year: "numeric",
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
              });
              const nodeName = alert.node_id === "Node01" ? "ถังทดลอง (Sample)" : "ถังควบคุม (Control)";

              return (
                <tr key={index} className="hover:bg-slate-800/10 transition-colors duration-200">
                  <td className="py-4 px-6 text-slate-300">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-slate-500" />
                      <span>{formattedTime}</span>
                    </div>
                  </td>
                  
                  <td className="py-4 px-6">
                    <div>
                      <div className="text-white font-bold">{alert.node_id}</div>
                      <div className="text-slate-400 text-xs font-semibold mt-0.5">{nodeName}</div>
                    </div>
                  </td>
                  
                  <td className="py-4 px-4 text-center">
                    <span className="text-base font-extrabold text-white">
                      {alert.fdei_value.toFixed(1)}%
                    </span>
                  </td>

                  <td className="py-4 px-4 text-center">
                    <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold leading-none ${alertCfg.bg} ${alertCfg.border}`}>
                      <AlertCircle className={`w-4 h-4 ${alertCfg.text}`} />
                      <span className={alertCfg.text}>{alertCfg.label}</span>
                    </div>
                  </td>
                </tr>
              );
            })}

            {alerts.length === 0 && (
              <tr>
                <td colSpan="4" className="py-12 px-6 text-center text-slate-500 font-semibold">
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
