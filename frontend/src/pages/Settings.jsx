import React, { useEffect, useState } from "react";
import Navbar from "../components/Navbar";
import client from "../api/client";
import {
  Settings,
  Save,
  FlaskConical,
  Activity,
  AlertTriangle,
  CheckCircle,
  Menu,
  Info,
} from "lucide-react";

export default function SettingsPage() {
  const [fogDay0, setFogDay0] = useState("");
  const [fdeiAlertThreshold, setFdeiAlertThreshold] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const fetchSettings = async () => {
    try {
      setError("");
      const response = await client.get("/api/settings");
      const data = response.data;
      setFogDay0(data.fog_day0 !== undefined ? String(data.fog_day0) : "");
      setFdeiAlertThreshold(
        data.fdei_alert_threshold !== undefined
          ? String(data.fdei_alert_threshold)
          : ""
      );
    } catch (err) {
      console.error("Error loading settings:", err);
      setError("ไม่สามารถดึงข้อมูลการตั้งค่าระบบได้");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      await client.post("/api/settings", {
        fog_day0: parseFloat(fogDay0),
        fdei_alert_threshold: parseFloat(fdeiAlertThreshold),
      });
      setSuccess("บันทึกการตั้งค่าเรียบร้อยแล้ว");
      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(""), 5000);
    } catch (err) {
      console.error("Error saving settings:", err);
      setError("ไม่สามารถบันทึกการตั้งค่าได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  return (
    <div className="min-h-screen bg-[#070913] flex flex-col md:flex-row">
      {/* Mobile Top Navigation Bar */}
      <div className="md:hidden flex h-16 items-center justify-between px-4 bg-slate-900/90 border-b border-slate-800/80 sticky top-0 z-40 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center">
            <FlaskConical className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-sm tracking-wider">
            FOG-MONITOR
          </span>
        </div>
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="p-2 text-slate-400 hover:text-white transition-colors duration-200"
        >
          <Menu className="w-6 h-6" />
        </button>
      </div>

      {/* Sidebar Navigation */}
      <Navbar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <main className="flex-1 md:ml-64 min-h-screen transition-all duration-300">
        <div className="p-4 md:p-8">
          {/* Header */}
          <header className="mb-8">
            <h1 className="text-xl md:text-2xl font-black text-white flex items-center gap-3">
              <Settings className="w-6 h-6 text-cyan-400" />
              ตั้งค่าระบบ (System Settings)
            </h1>
            <p className="text-xs md:text-sm text-slate-400 font-semibold mt-1">
              กำหนดค่าเริ่มต้นของการทดลองและเกณฑ์การแจ้งเตือน
            </p>
          </header>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2 text-xs font-semibold">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-start gap-2 text-xs font-semibold">
              <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-[50vh] gap-3">
              <Activity className="w-10 h-10 text-cyan-500 animate-pulse" />
              <p className="text-sm text-slate-400 font-bold">
                กำลังโหลดข้อมูลการตั้งค่าระบบ...
              </p>
            </div>
          ) : (
            <form onSubmit={handleSave}>
              <div className="glass-panel border border-slate-800/80 rounded-3xl p-6 md:p-8 max-w-2xl space-y-8">
                {/* FOG Day0 Input */}
                <div className="space-y-3">
                  <label className="text-sm font-bold text-white flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-cyan-400" />
                    ค่า FOG เริ่มต้นของรอบการทดลอง (Day 0)
                  </label>
                  <p className="text-xs text-slate-400 font-medium leading-relaxed">
                    ค่าไขมันเริ่มต้นที่วัดจากห้องปฏิบัติการด้วย Gravimetric
                    method (หน่วย mg/L)
                  </p>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      required
                      value={fogDay0}
                      onChange={(e) => setFogDay0(e.target.value)}
                      placeholder="เช่น 5000.00"
                      className="w-full bg-[#0a0d18] border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-3 text-sm font-semibold text-white outline-none transition-all duration-300"
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-slate-500 font-bold">
                      mg/L
                    </span>
                  </div>
                </div>

                {/* FDEI Alert Threshold Input */}
                <div className="space-y-3">
                  <label className="text-sm font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    เกณฑ์เป้าหมายการแจ้งเตือน FDEI (%)
                  </label>
                  <p className="text-xs text-slate-400 font-medium leading-relaxed">
                    ระบบจะส่ง Telegram แจ้งเตือนเมื่อค่า FDEI
                    ถึงเกณฑ์ที่กำหนดไว้ (แจ้งครั้งเดียวต่อรอบ)
                  </p>
                  <div className="relative">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="100"
                      required
                      value={fdeiAlertThreshold}
                      onChange={(e) => setFdeiAlertThreshold(e.target.value)}
                      placeholder="เช่น 80.0"
                      className="w-full bg-[#0a0d18] border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-3 text-sm font-semibold text-white outline-none transition-all duration-300"
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-slate-500 font-bold">
                      %
                    </span>
                  </div>
                </div>

                {/* Info Note */}
                <div className="rounded-xl bg-blue-500/5 border border-blue-500/15 p-4 flex gap-3 text-xs font-medium text-blue-300">
                  <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                  <p className="leading-relaxed">
                    ค่า FOG Day0 จะถูกใช้ในการคำนวณ FDEI (%)
                    ของรอบการทดลองปัจจุบัน
                    หากเริ่มรอบใหม่ให้อัปเดตค่านี้ตามผลวิเคราะห์จากห้องปฏิบัติการ
                  </p>
                </div>

                {/* Save Button */}
                <div className="flex justify-end pt-4 border-t border-slate-800/40">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold rounded-xl px-6 py-3 text-xs transition-all duration-300 disabled:opacity-50 shadow-lg shadow-cyan-500/10"
                  >
                    <Save className="w-4 h-4" />
                    <span>
                      {saving
                        ? "กำลังบันทึก..."
                        : "บันทึกการตั้งค่า"}
                    </span>
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
