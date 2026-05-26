import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import AlertTable from "../components/AlertTable";
import client from "../api/client";
import { Activity, AlertTriangle, Info } from "lucide-react";

export default function AlertHistory() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
    <div className="min-h-screen bg-[#070913] flex">
      <Navbar />

      <main className="flex-1 pl-64 p-8 min-h-screen">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-2xl font-black text-white">ประวัติการแจ้งเตือน (Alert History)</h1>
          <p className="text-sm text-slate-400 font-semibold mt-1">ประวัติสภาวะวิกฤตคุณภาพน้ำที่สุ่มเสี่ยงและระดับการตอบสนองระบบบำบัด</p>
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
                  ระบบส่งสัญญาณแจ้งเตือนอัตโนมัติไปยังกลุ่มงานควบคุมบำบัดน้ำเสียผ่าน Telegram API ทันทีที่การพยากรณ์คุณภาพน้ำล่วงหน้า 
                  มีดัชนี WQI &gt; 75 (สภาวะแย่มาก หรือ ไม่เหมาะสมอย่างยิ่ง) เพื่อเตรียมสารบำบัดล่วงหน้าก่อนสถานการณ์จริง
                </p>
              </div>
            </div>

            {/* Alert Table */}
            <section>
              <AlertTable alerts={alerts} />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
