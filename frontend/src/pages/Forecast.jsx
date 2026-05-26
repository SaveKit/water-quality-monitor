import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import WQICard from "../components/WQICard";
import client from "../api/client";
import { Cpu, Activity, Info, Brain } from "lucide-react";

export default function Forecast() {
  const [forecastData, setForecastData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchForecast = async () => {
    try {
      const response = await client.get("/api/data/forecast");
      setForecastData(response.data);
    } catch (err) {
      console.error("Error loading forecast data:", err);
      setError("ไม่สามารถเชื่อมต่อดึงข้อมูลการพยากรณ์ล่วงหน้าได้");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecast();
  }, []);

  return (
    <div className="min-h-screen bg-[#070913] flex">
      <Navbar />

      <main className="flex-1 pl-64 p-8 min-h-screen">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-2xl font-black text-white">การพยากรณ์ดัชนีคุณภาพน้ำ (AI Forecast)</h1>
          <p className="text-sm text-slate-400 font-semibold mt-1">คาดการณ์ระดับคุณภาพน้ำทิ้งล่วงหน้า 24 ชั่วโมง เพื่อเตรียมการบำบัดเชิงรุก</p>
        </header>

        {/* Info Bar - Model Specification */}
        <div className="mb-8 rounded-2xl bg-gradient-to-r from-blue-500/10 via-cyan-500/5 to-purple-500/5 border border-blue-500/25 p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shrink-0">
            <Cpu className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">AI Prediction Model v1.2 — ความแม่นยำ 94.6%</h4>
            <p className="text-xs text-slate-400 font-semibold mt-0.5">โมเดลโครงข่ายประสาทผสมผสาน CNN-GRU-SVR ประมวลผลบนระบบ AWS Lambda</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2 text-xs font-semibold">
            <Info className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center h-[50vh] gap-3">
            <Activity className="w-10 h-10 text-cyan-500 animate-pulse" />
            <p className="text-sm text-slate-400 font-bold">กำลังประมวลผลดึงข้อมูลพยากรณ์จากเซิร์ฟเวอร์...</p>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Forecast Cards Grid (2 Nodes) */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {forecastData.map((nodeForecast) => {
                const nodeName = nodeForecast.node_id === "Node01" ? "จุดตรวจวัดที่ 1 (คาดการณ์)" : "จุดตรวจวัดที่ 2 (คาดการณ์)";
                return (
                  <WQICard
                    key={nodeForecast.node_id}
                    nodeId={nodeForecast.node_id}
                    nodeTitle={nodeName}
                    wqi={nodeForecast.forecasted_wqi}
                    timestamp={nodeForecast.timestamp}
                    isForecast={true}
                  />
                );
              })}
            </section>

            {/* AI Architecture Overview */}
            <section className="rounded-2xl glass-panel p-6 border border-slate-800/80">
              <h3 className="text-base font-bold text-white flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-cyan-400" />
                <span>คำอธิบายกลไกโมเดลประมวลผล (CNN-GRU-SVR)</span>
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed font-medium">
                โมเดลพยากรณ์เป็นรูปแบบ Hybrid Network: ส่วนของ <strong className="text-slate-300">CNN (Convolutional Neural Network)</strong> ทำหน้าที่สกัดความสัมพันธ์เชิงคุณลักษณะในแต่ละตัวแปรตรวจวัด (Cross-correlation of parameters) 
                จากนั้นส่งต่อให้ <strong className="text-slate-300">GRU (Gated Recurrent Unit)</strong> เพื่อวิเคราะห์แนวโน้มการเปลี่ยนแปลงตามลำดับเวลา (Time-series sequences) 
                และปรับให้มีความแม่นยำสูงขึ้น (Refinement) ด้วย <strong className="text-slate-300">SVR (Support Vector Regression)</strong> เพื่อป้องกันการพยากรณ์ที่ผิดเพี้ยนจากปัจจัยรบกวนภายนอก
              </p>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
