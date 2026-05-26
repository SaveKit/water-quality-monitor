import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import WQICard from "../components/WQICard";
import SensorTable from "../components/SensorTable";
import client from "../api/client";
import { RefreshCw, Activity, AlertTriangle, Menu, Droplet } from "lucide-react";

export default function Overview() {
  const [realtimeData, setRealtimeData] = useState([]);
  const [wqiData, setWqiData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const fetchData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      setError("");
      const [realtimeRes, wqiRes] = await Promise.all([
        client.get("/api/data/realtime"),
        client.get("/api/data/wqi"),
      ]);
      setRealtimeData(realtimeRes.data);
      setWqiData(wqiRes.data);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setError("ไม่สามารถเชื่อมต่อระบบหลังบ้านหรือดึงข้อมูลเซ็นเซอร์ได้");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Auto-refresh every 5 minutes (300,000 ms)
    const interval = setInterval(() => {
      fetchData();
    }, 300000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#070913] flex flex-col md:flex-row">
      {/* Mobile Top Navigation Bar */}
      <div className="md:hidden flex h-16 items-center justify-between px-4 bg-slate-900/90 border-b border-slate-800/80 sticky top-0 z-40 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center">
            <Droplet className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-sm tracking-wider">WQ-MONITOR</span>
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
          <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
            <div>
              <h1 className="text-xl md:text-2xl font-black text-white">ระบบตรวจสอบคุณภาพน้ำเรียลไทม์</h1>
              <p className="text-xs md:text-sm text-slate-400 font-semibold mt-1">ภาพรวมคุณภาพน้ำทิ้งและสถานะเซ็นเซอร์ประมวลผล สจล.</p>
            </div>

            <button
              onClick={() => fetchData(true)}
              disabled={refreshing}
              className="flex items-center gap-2 bg-slate-800/60 hover:bg-slate-800 text-slate-200 border border-slate-700/60 rounded-xl px-4 py-2.5 text-xs font-bold transition-all duration-300 disabled:opacity-50 w-full sm:w-auto justify-center"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "กำลังโหลด..." : "ดึงข้อมูลใหม่"}</span>
            </button>
          </header>

          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-3 text-xs font-semibold">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-[50vh] gap-3">
              <Activity className="w-10 h-10 text-cyan-500 animate-pulse" />
              <p className="text-sm text-slate-400 font-bold">กำลังโหลดข้อมูลดัชนี WQI และระบบตรวจวัด...</p>
            </div>
          ) : (
            <div className="space-y-8">
              {/* WQI Cards Grid (2 Nodes) */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {wqiData.map((nodeWqi) => {
                  const nodeName = nodeWqi.node_id === "Node01" ? "จุดตรวจวัดที่ 1 (ทิศเหนือ)" : "จุดตรวจวัดที่ 2 (ทิศใต้)";
                  return (
                    <WQICard
                      key={nodeWqi.node_id}
                      nodeId={nodeWqi.node_id}
                      nodeTitle={nodeName}
                      wqi={nodeWqi.wqi}
                      timestamp={nodeWqi.timestamp}
                      isForecast={false}
                    />
                  );
                })}
              </section>

              {/* Detailed Sensor Readings Table */}
              <section>
                <SensorTable realtimeData={realtimeData} wqiData={wqiData} />
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
