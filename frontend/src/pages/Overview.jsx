import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import FDEICard from "../components/FDEICard";
import SensorTable from "../components/SensorTable";
import client from "../api/client";
import { SENSOR_TYPES } from "../utils/fdei";
import { RefreshCw, Activity, AlertTriangle, Menu, FlaskConical } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";

// Mini Sparkline Trend Chart Component
function MiniTrendChart({ dataNode01 = [], dataNode02 = [], unit }) {
  const mergedMap = {};

  dataNode01.forEach((pt) => {
    const key = new Date(pt.timestamp).getTime();
    mergedMap[key] = {
      timestamp: key,
      formattedTime: new Date(pt.timestamp).toLocaleTimeString("th-TH", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      Node01: pt.value,
      Node02: null,
    };
  });

  dataNode02.forEach((pt) => {
    const key = new Date(pt.timestamp).getTime();
    if (mergedMap[key]) {
      mergedMap[key].Node02 = pt.value;
    } else {
      mergedMap[key] = {
        timestamp: key,
        formattedTime: new Date(pt.timestamp).toLocaleTimeString("th-TH", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        Node01: null,
        Node02: pt.value,
      };
    }
  });

  const chartData = Object.values(mergedMap).sort((a, b) => a.timestamp - b.timestamp);

  // Downsample to max 30 points to render quickly and smoothly
  const maxPoints = 30;
  let finalData = chartData;
  if (chartData.length > maxPoints) {
    const step = Math.ceil(chartData.length / maxPoints);
    finalData = chartData.filter((_, idx) => idx % step === 0);
  }

  return (
    <div className="w-full h-12 mt-2">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={finalData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Tooltip
            contentStyle={{
              background: "rgba(15, 23, 42, 0.95)",
              borderColor: "rgba(255, 255, 255, 0.08)",
              borderRadius: "12px",
              fontSize: "10px",
              fontFamily: "Sarabun",
              backdropFilter: "blur(4px)",
            }}
            itemStyle={{ color: "#fff", padding: "1px 0" }}
            labelFormatter={() => "แนวโน้ม"}
            formatter={(value, name) => [
              `${Number(value).toFixed(2)} ${unit}`,
              name === "Node01" ? "ถังทดลอง (Sample)" : "ถังควบคุม (Control)",
            ]}
          />
          <Line
            type="monotone"
            dataKey="Node01"
            stroke="#06b6d4"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: "#22d3ee" }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="Node02"
            stroke="#6366f1"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: "#818cf8" }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Overview() {
  const [realtimeData, setRealtimeData] = useState([]);
  const [fdeiData, setFdeiData] = useState([]);
  const [trendsData, setTrendsData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const fetchData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      setError("");
      
      // Calculate 24h ranges for trends
      const endIso = new Date().toISOString();
      const startIso = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
      
      const [realtimeRes, fdeiRes] = await Promise.all([
        client.get("/api/data/realtime"),
        client.get("/api/data/fdei"),
      ]);
      setRealtimeData(realtimeRes.data);
      setFdeiData(fdeiRes.data);

      // Fetch trends for all parameters
      const paramsList = ["ph", "co2", "tds", "turbidity", "temp"];
      const nodes = ["Node01", "Node02"];
      const trendPromises = [];
      const trendKeys = [];

      paramsList.forEach((param) => {
        nodes.forEach((node) => {
          trendPromises.push(
            client.get("/api/data/historical", {
              params: {
                node_id: node,
                sensor_type: param,
                start_time: startIso,
                end_time: endIso,
              },
            })
          );
          trendKeys.push({ param, node });
        });
      });

      const trendResponses = await Promise.all(trendPromises);
      const newTrends = {};

      trendResponses.forEach((res, index) => {
        const { param, node } = trendKeys[index];
        if (!newTrends[param]) {
          newTrends[param] = { Node01: [], Node02: [] };
        }
        newTrends[param][node] = res.data;
      });

      setTrendsData(newTrends);
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

    // Auto-refresh every 5 minutes (300,000 ms) matching bioreactor sampling rate
    console.log("Setting up auto-refresh interval (5 minutes)...");
    const interval = setInterval(() => {
      console.log("Auto-refreshing dashboard and trends data...");
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
          <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
            <div>
              <h1 className="text-xl md:text-2xl font-black text-white">ระบบเฝ้าระวังการย่อยสลายไขมัน (FOG) เรียลไทม์</h1>
              <p className="text-xs md:text-sm text-slate-400 font-semibold mt-1">ภาพรวมถังปฏิกรณ์ชีวภาพ ดัชนี FDEI และสถานะเซ็นเซอร์ สจล.</p>
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
              <p className="text-sm text-slate-400 font-bold">กำลังโหลดข้อมูลดัชนี FDEI และระบบตรวจวัด...</p>
            </div>
          ) : (
            <div className="space-y-8">
              {/* FDEI Cards Grid (2 Nodes) */}
              <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {fdeiData.map((nodeFdei) => {
                  const nodeName = nodeFdei.node_id === "Node01" ? "ถังทดลอง (Sample)" : "ถังควบคุม (Control)";
                  return (
                    <FDEICard
                      key={nodeFdei.node_id}
                      nodeId={nodeFdei.node_id}
                      nodeTitle={nodeName}
                      fdei={nodeFdei.fdei}
                      co2Cumulative={nodeFdei.co2_cumulative}
                      timestamp={nodeFdei.timestamp}
                      isForecast={false}
                    />
                  );
                })}
              </section>

              {/* Sparkline Trend Graphs Grid */}
              <section className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <h3 className="text-xs font-black text-slate-300 uppercase tracking-wider">
                    แนวโน้มพารามิเตอร์ล่าสุด (24 ชั่วโมงที่ผ่านมา)
                  </h3>
                  <span className="text-[10px] text-slate-500 font-bold">เปรียบเทียบถังทดลอง & ถังควบคุม</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                  {SENSOR_TYPES.filter((type) => type.key !== "fdei").map((type) => {
                    const paramData = trendsData[type.key] || { Node01: [], Node02: [] };
                    const latestN1 = paramData.Node01?.[paramData.Node01.length - 1]?.value;
                    const latestN2 = paramData.Node02?.[paramData.Node02.length - 1]?.value;

                    return (
                      <div
                        key={type.key}
                        className="glass-panel border border-slate-800/80 rounded-2xl p-4 flex flex-col justify-between transition-all duration-300 hover:border-slate-700/60"
                      >
                        <div>
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-bold text-slate-300">{type.label}</span>
                            <span className="text-[9px] text-slate-500 font-bold uppercase">{type.unit || "unitless"}</span>
                          </div>
                          <div className="flex justify-between items-baseline mt-1.5 text-[10px] font-bold">
                            <span className="text-cyan-400">N1: {latestN1 !== undefined ? latestN1.toFixed(1) : "-"}</span>
                            <span className="text-indigo-400">N2: {latestN2 !== undefined ? latestN2.toFixed(1) : "-"}</span>
                          </div>
                        </div>
                        <MiniTrendChart
                          dataNode01={paramData.Node01}
                          dataNode02={paramData.Node02}
                          unit={type.unit}
                        />
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Detailed Sensor Readings Table */}
              <section>
                <SensorTable realtimeData={realtimeData} />
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
