import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import AlertTable from "../components/AlertTable";
import client from "../api/client";
import { Activity, AlertTriangle, Info, Menu, FlaskConical } from "lucide-react";

export default function AlertHistory() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const fetchAlerts = async () => {
    try {
      const response = await client.get("/api/data/alerts");
      setAlerts(response.data);
    } catch (err) {
      console.error("Error loading alert history:", err);
      setError("ไม่สามารถดึงข้อมูลบันทึกประวัติการเตือนภัยได้");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  return (
    <div className="min-h-screen bg-[#070913] flex flex-col md:flex-row">
      {/* Mobile Top Navigation Bar */}
      <div className="md:hidden flex h-16 items-center justify-between px-4 bg-slate-900/90 border-b border-slate-800/80 sticky top-0 z-40 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center">
            <FlaskConical className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-sm tracking-wider">FOG-MONITOR</span>
        </div>
        <button 
          onClick={() => setIsSidebarOpen(true)}
          className="p-2 text-slate-400 hover:text-white transition-colors duration-200"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {/* Sidebar Navigation */}
      <Navbar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* Main Content Area */}
      <main className="flex-1 md:ml-64 min-h-screen transition-all duration-300">
        <div className="p-4 md:p-8">
          {/* Header */}
          <header className="mb-8">
            <h1 className="text-xl md:text-2xl font-black text-white">ประวัติการแจ้งเตือน (Alert History)</h1>
            <p className="text-sm text-slate-400 font-semibold mt-1">ประวัติเหตุการณ์เมื่อกิจกรรมการย่อยสลายไขมันผิดปกติ หรือประสิทธิภาพ FDEI ถึงเป้าหมาย</p>
          </header>

          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2 text-xs font-semibold">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-[50vh] gap-3">
              <Activity className="w-10 h-10 text-cyan-500 animate-pulse" />
              <p className="text-sm text-slate-400 font-bold">กำลังดึงข้อมูลประวัติเหตุการณ์เตือนภัยย้อนหลัง...</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Information Alert Banner */}
              <div className="rounded-2xl bg-amber-500/5 border border-amber-500/20 p-4 flex gap-3 text-xs font-medium text-amber-300">
                <AlertTriangle className="w-4.5 h-4.5 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-bold">กฎการแจ้งเตือน (Alerting Rules):</strong>
                  <p className="text-amber-400/80 mt-1 leading-relaxed">
                    ระบบส่งสัญญาณแจ้งเตือนอัตโนมัติผ่าน Telegram API ใน 2 กรณี: (1) เมื่อตรวจพบว่าแนวโน้มการย่อยสลายไขมันชะลอตัวหรือหยุดนิ่ง (Plateau — กิจกรรม Bacillus ลดลง) 
                    และ (2) เมื่อค่า FDEI (%) ถึงเกณฑ์เป้าหมายที่ตั้งไว้ในหน้าตั้งค่าระบบ (แจ้งครั้งเดียวต่อรอบการทดลอง)
                  </p>
                </div>
              </div>

              {/* Alert Table */}
              <section>
                <AlertTable alerts={alerts} />
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
