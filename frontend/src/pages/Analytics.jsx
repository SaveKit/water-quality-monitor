import React, { useState } from "react";
import Navbar from "../components/Navbar";
import TimeSeriesChart from "../components/TimeSeriesChart";
import client from "../api/client";
import { SENSOR_TYPES } from "../utils/wqi";
import { Calendar, Search, Download, Database, Check, Layers, AlertCircle, Menu, Droplet } from "lucide-react";

export default function Analytics() {
  // Set default dates representing late May 2026 (matching current dataset)
  const defaultEndDate = "2026-05-26T23:59";
  const defaultStartDate = "2026-05-23T00:00";

  const [startDate, setStartDate] = useState(defaultStartDate);
  const [endDate, setEndDate] = useState(defaultEndDate);
  const [selectedNodes, setSelectedNodes] = useState({ Node01: true, Node02: true });
  const [selectedParams, setSelectedParams] = useState({
    ph: true,
    co2: false,
    tds: true,
    turbidity: false,
    temp: true,
  });

  // Applied states (frozen at the moment of click)
  const [appliedStartDate, setAppliedStartDate] = useState(defaultStartDate);
  const [appliedEndDate, setAppliedEndDate] = useState(defaultEndDate);
  const [appliedNodes, setAppliedNodes] = useState({ Node01: true, Node02: true });
  const [appliedParams, setAppliedParams] = useState({
    ph: true,
    co2: false,
    tds: true,
    turbidity: false,
    temp: true,
  });

  const [historicalData, setHistoricalData] = useState({}); // { ph: { Node01: [...], Node02: [...] }, ... }
  const [rawTableData, setRawTableData] = useState([]); // Computed once on fetch, prevent re-sorting lag
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleNodeToggle = (node) => {
    setSelectedNodes((prev) => ({ ...prev, [node]: !prev[node] }));
  };

  const handleParamToggle = (param) => {
    setSelectedParams((prev) => ({ ...prev, [param]: !prev[param] }));
  };

  const fetchHistoricalData = async () => {
    setLoading(true);
    setError("");
    const newHistoricalData = {};

    const activeParams = Object.keys(selectedParams).filter((p) => selectedParams[p]);
    const activeNodes = Object.keys(selectedNodes).filter((n) => selectedNodes[n]);

    if (activeParams.length === 0) {
      setError("กรุณาเลือกอย่างน้อย 1 พารามิเตอร์");
      setLoading(false);
      return;
    }
    if (activeNodes.length === 0) {
      setError("กรุณาเลือกอย่างน้อย 1 จุดตรวจวัด");
      setLoading(false);
      return;
    }

    try {
      const startIso = new Date(startDate).toISOString();
      const endIso = new Date(endDate).toISOString();

      const promises = [];
      const keys = [];

      activeParams.forEach((param) => {
        activeNodes.forEach((node) => {
          promises.push(
            client.get("/api/data/historical", {
              params: {
                node_id: node,
                sensor_type: param,
                start_time: startIso,
                end_time: endIso,
              },
            })
          );
          keys.push({ param, node });
        });
      });

      const responses = await Promise.all(promises);

      responses.forEach((res, index) => {
        const { param, node } = keys[index];
        if (!newHistoricalData[param]) {
          newHistoricalData[param] = { Node01: [], Node02: [] };
        }
        newHistoricalData[param][node] = res.data;
      });

      // Calculate combined raw data points ONCE here and save in state
      const combined = [];
      Object.keys(newHistoricalData).forEach((param) => {
        const nodes = newHistoricalData[param];
        Object.keys(nodes).forEach((node) => {
          nodes[node].forEach((pt) => {
            combined.push({
              timestamp: new Date(pt.timestamp).getTime(),
              timestampStr: pt.timestamp,
              node_id: node,
              sensor_type: param,
              value: pt.value,
              unit: pt.unit,
            });
          });
        });
      });
      
      // Sort and slice to top 100 once
      combined.sort((a, b) => b.timestamp - a.timestamp);
      
      setRawTableData(combined.slice(0, 100));
      setHistoricalData(newHistoricalData);
      
      // Freeze inputs for display
      setAppliedStartDate(startDate);
      setAppliedEndDate(endDate);
      setAppliedNodes({ ...selectedNodes });
      setAppliedParams({ ...selectedParams });
      
      setHasSearched(true);
    } catch (err) {
      console.error("Error loading historical analytics:", err);
      setError("เกิดข้อผิดพลาดในการดึงข้อมูลประวัติย้อนหลัง");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async (node, param) => {
    try {
      const startIso = new Date(appliedStartDate).toISOString();
      const endIso = new Date(appliedEndDate).toISOString();
      
      const response = await client.get("/api/data/export/csv", {
        params: {
          node_id: node,
          sensor_type: param,
          start_time: startIso,
          end_time: endIso,
        },
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `water_quality_${node}_${param}_export.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Export CSV failed:", err);
      alert("ไม่สามารถดาวน์โหลดไฟล์ CSV ได้");
    }
  };

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
          <header className="mb-8">
            <h1 className="text-xl md:text-2xl font-black text-white">วิเคราะห์ข้อมูลเชิงลึก (Analytics)</h1>
            <p className="text-xs md:text-sm text-slate-400 font-semibold mt-1">
              เครื่องมือกองข้อมูลความถี่ ดึงข้อมูลย้อนหลัง และตรวจสอบเปรียบเทียบแนวโน้มคุณภาพน้ำระหว่างสถานี
            </p>
          </header>

          {/* Filter Control Panel */}
          <section className="glass-panel border border-slate-800 p-6 rounded-3xl mb-8 space-y-6">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>ตั้งค่าช่วงเวลาและข้อมูลที่ต้องการเปรียบเทียบ</span>
            </h3>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Start and End date time pickers (Calendar and Time Range selector) */}
              <div className="space-y-3">
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  ช่วงเวลาตรวจวัด (เลือกปฏิทินและเวลา)
                </label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="flex-1 space-y-1">
                    <span className="text-[10px] text-slate-500 font-bold">เริ่มต้น</span>
                    <input
                      type="datetime-local"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full bg-[#0a0d18] border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs font-semibold text-white outline-none"
                    />
                  </div>
                  <div className="flex-1 space-y-1">
                    <span className="text-[10px] text-slate-500 font-bold">สิ้นสุด</span>
                    <input
                      type="datetime-local"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-[#0a0d18] border border-slate-800 focus:border-cyan-500 rounded-xl px-3 py-2 text-xs font-semibold text-white outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Checkbox Node Picker (No direction suffix) */}
              <div className="space-y-3">
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider">
                  สถานีจุดตรวจวัด
                </label>
                <div className="flex flex-col gap-2">
                  {["Node01", "Node02"].map((node) => (
                    <button
                      key={node}
                      onClick={() => handleNodeToggle(node)}
                      className={`flex items-center justify-between px-4 py-2.5 rounded-xl border text-xs font-bold transition-all duration-300 ${
                        selectedNodes[node]
                          ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30"
                          : "bg-slate-900/40 text-slate-500 border-slate-800"
                      }`}
                    >
                      <span>{node === "Node01" ? "จุดตรวจวัดที่ 1" : "จุดตรวจวัดที่ 2"}</span>
                      {selectedNodes[node] && <Check className="w-4 h-4" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Multi-select parameter checks */}
              <div className="space-y-3">
                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider">
                  ตัวแปรพารามิเตอร์เซ็นเซอร์
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {SENSOR_TYPES.map((type) => (
                    <button
                      key={type.key}
                      onClick={() => handleParamToggle(type.key)}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl border text-xs font-bold transition-all duration-300 ${
                        selectedParams[type.key]
                          ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                          : "bg-slate-900/40 text-slate-500 border-slate-800"
                      }`}
                    >
                      <span>{type.label}</span>
                      {selectedParams[type.key] && <Check className="w-3 h-3" />}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800/40">
              <button
                onClick={fetchHistoricalData}
                disabled={loading}
                className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold rounded-xl px-6 py-3 text-xs transition-all duration-300 disabled:opacity-50 w-full sm:w-auto justify-center"
              >
                <Search className="w-4 h-4" />
                <span>{loading ? "กำลังวิเคราะห์ข้อมูล..." : "เริ่มค้นหาและเปรียบเทียบ"}</span>
              </button>
            </div>
          </section>

          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2 text-xs font-semibold">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-[40vh] gap-3">
              <Database className="w-10 h-10 text-cyan-500 animate-pulse" />
              <p className="text-sm text-slate-400 font-bold">กำลังดึงฐานข้อมูลเซ็นเซอร์ย้อนหลัง...</p>
            </div>
          ) : !hasSearched ? (
            <div className="flex flex-col items-center justify-center h-[35vh] gap-3 glass-panel border border-slate-800/80 rounded-3xl p-6">
              <Database className="w-8 h-8 text-slate-500" />
              <p className="text-sm text-slate-400 font-bold">กรุณาตั้งค่าช่วงเวลา พารามิเตอร์ และจุดวัด แล้วกดปุ่ม "เริ่มค้นหาและเปรียบเทียบ"</p>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Time Series Charts section */}
              <section className="space-y-6">
                {Object.keys(appliedParams).filter((p) => appliedParams[p]).map((param) => {
                  const typeObj = SENSOR_TYPES.find((t) => t.key === param);
                  const nodesData = historicalData[param] || { Node01: [], Node02: [] };
                  const activeNodes = Object.keys(appliedNodes).filter((n) => appliedNodes[n]);

                  return (
                    <div key={param} className="glass-panel border border-slate-800/80 rounded-3xl p-6">
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                        <div>
                          <h4 className="text-base font-bold text-white">กราฟแนวโน้ม: {typeObj?.label}</h4>
                          <p className="text-xs text-slate-400 mt-0.5">การบันทึกการวัดแบบต่อเนื่องตามแนวโน้มเวลา</p>
                        </div>
                        
                        {/* Export CSV actions dropdown */}
                        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
                          {activeNodes.map((node) => (
                            <button
                              key={node}
                              onClick={() => handleExportCSV(node, param)}
                              className="flex items-center gap-1.5 bg-slate-800/50 hover:bg-slate-800 text-slate-300 border border-slate-700/50 rounded-xl px-3 py-1.5 text-[10px] font-bold transition-all duration-300 w-full sm:w-auto justify-center"
                            >
                              <Download className="w-3.5 h-3.5" />
                              <span>Export CSV ({node === "Node01" ? "จุดตรวจวัดที่ 1" : "จุดตรวจวัดที่ 2"})</span>
                            </button>
                          ))}
                        </div>
                      </div>
                      
                      <TimeSeriesChart
                        dataNode01={nodesData.Node01}
                        dataNode02={nodesData.Node02}
                        activeNodes={appliedNodes}
                        parameterLabel={typeObj?.label}
                        unit={typeObj?.unit}
                      />
                    </div>
                  );
                })}
              </section>

              {/* Raw Data Table List Section */}
              <section className="rounded-2xl glass-panel border border-slate-800/80 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800/60">
                  <h3 className="text-base font-bold text-white">ตารางบันทึกค่าดิบย้อนหลัง (100 แถวแรก)</h3>
                  <p className="text-xs text-slate-400 mt-0.5">รายการพิกัดตัวเลขอ้างอิงจริงที่ดึงออกมาจากฐานข้อมูล DynamoDB</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800/40 text-xs text-slate-400 font-bold uppercase bg-slate-900/20">
                        <th className="py-3 px-6">วัน-เวลา</th>
                        <th className="py-3 px-6">จุดตรวจวัด</th>
                        <th className="py-3 px-6">ตัวแปร</th>
                        <th className="py-3 px-6 text-right">ค่าที่บันทึกได้</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/30 text-xs font-semibold">
                      {rawTableData.map((row, index) => {
                        const typeObj = SENSOR_TYPES.find((t) => t.key === row.sensor_type);
                        const formattedTime = new Date(row.timestampStr).toLocaleString("th-TH", {
                          timeZone: "Asia/Bangkok",
                          month: "short",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        });

                        return (
                          <tr key={index} className="hover:bg-slate-800/10 transition-colors duration-200">
                            <td className="py-3 px-6 text-slate-400">{formattedTime}</td>
                            <td className="py-3 px-6 text-white">
                              {row.node_id === "Node01" ? "จุดตรวจวัดที่ 1" : "จุดตรวจวัดที่ 2"}
                            </td>
                            <td className="py-3 px-6 text-slate-300">{typeObj?.label || row.sensor_type}</td>
                            <td className="py-3 px-6 text-right text-cyan-400 font-bold">
                              {row.value.toFixed(2)} {row.unit}
                            </td>
                          </tr>
                        );
                      })}
                      {rawTableData.length === 0 && (
                        <tr>
                          <td colSpan="4" className="py-8 px-6 text-center text-slate-500 font-bold">
                            ไม่พบข้อมูลในช่วงเวลาและสถานีที่ระบุ
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
