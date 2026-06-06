import React from "react";
import { Info } from "lucide-react";

export default function SensorTable({ realtimeData }) {
  // Safe checks for sensor parameters
  const isOutOfRangePH = (ph) => ph < 6.5 || ph > 8.5;
  const isHighTDS = (tds) => tds > 500;
  const isHighTurbidity = (turb) => turb > 5;

  return (
    <div className="rounded-2xl glass-panel border border-slate-800/80 overflow-hidden">
      {/* Table Header Section */}
      <div className="px-6 py-4 border-b border-slate-800/60 flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white">ตารางข้อมูลจากเซ็นเซอร์ (เรียลไทม์)</h3>
          <p className="text-xs text-slate-400 mt-0.5">ข้อมูลดิบจากถังปฏิกรณ์ชีวภาพ — ค่าเซ็นเซอร์ล่าสุดสำหรับคำนวณ FDEI</p>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-slate-500 font-semibold bg-slate-800/20 px-2 py-1 rounded-lg">
          <Info className="w-3.5 h-3.5" />
          <span>อัปเดตอัตโนมัติทุก 5 นาที</span>
        </div>
      </div>

      {/* Responsive Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800/40 text-xs text-slate-400 font-bold uppercase bg-slate-900/20">
              <th className="py-4 px-6">ถังปฏิกรณ์ (Node ID)</th>
              <th className="py-4 px-3 text-center">pH</th>
              <th className="py-4 px-3 text-center">CO₂ (ppm)</th>
              <th className="py-4 px-3 text-center">TDS (ppm)</th>
              <th className="py-4 px-3 text-center">Turbidity (NTU)</th>
              <th className="py-4 px-3 text-center">อุณหภูมิ (°C)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/30 text-sm font-medium">
            {realtimeData.map((row) => {
              const nodeName = row.node_id === "Node01" ? "ถังทดลอง (Sample)" : "ถังควบคุม (Control)";

              return (
                <tr key={row.node_id} className="hover:bg-slate-800/10 transition-colors duration-200">
                  <td className="py-4 px-6">
                    <div>
                      <div className="text-white font-bold text-sm">{row.node_id}</div>
                      <div className="text-slate-400 text-xs font-semibold mt-0.5">{nodeName}</div>
                    </div>
                  </td>
                  
                  {/* pH Parameter */}
                  <td className="py-4 px-3 text-center">
                    <span className={`text-sm ${isOutOfRangePH(row.ph) ? "text-rose-400 font-bold" : "text-slate-200"}`}>
                      {row.ph.toFixed(2)}
                    </span>
                  </td>

                  {/* CO2 Parameter */}
                  <td className="py-4 px-3 text-center">
                    <span className="text-slate-200">{row.co2.toFixed(1)}</span>
                  </td>

                  {/* TDS Parameter */}
                  <td className="py-4 px-3 text-center">
                    <span className={`text-sm ${isHighTDS(row.tds) ? "text-rose-400 font-bold" : "text-slate-200"}`}>
                      {row.tds.toFixed(1)}
                    </span>
                  </td>

                  {/* Turbidity Parameter */}
                  <td className="py-4 px-3 text-center">
                    <span className={`text-sm ${isHighTurbidity(row.turbidity) ? "text-rose-400 font-bold" : "text-slate-200"}`}>
                      {row.turbidity.toFixed(2)}
                    </span>
                  </td>

                  {/* Temp Parameter */}
                  <td className="py-4 px-3 text-center">
                    <span className="text-slate-200">{row.temp.toFixed(1)}</span>
                  </td>
                </tr>
              );
            })}
            
            {realtimeData.length === 0 && (
              <tr>
                <td colSpan="6" className="py-8 px-6 text-center text-slate-500 font-semibold">
                  ไม่มีข้อมูลในขณะนี้
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
