import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { 
  FlaskConical, 
  LayoutDashboard, 
  TrendingUp, 
  LineChart, 
  AlertTriangle, 
  Settings2,
  LogOut,
  User,
  X
} from "lucide-react";

export default function Navbar({ isOpen, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const user = JSON.parse(sessionStorage.getItem("user") || '{"username": "Admin"}');

  const navItems = [
    { label: "ภาพรวมระบบ", path: "/", icon: LayoutDashboard },
    { label: "พยากรณ์การย่อยสลายไขมัน (FDEI)", path: "/forecast", icon: TrendingUp },
    { label: "วิเคราะห์เชิงลึก", path: "/analytics", icon: LineChart },
    { label: "ประวัติการเตือนภัย", path: "/alerts", icon: AlertTriangle },
    { label: "ตั้งค่าระบบ", path: "/settings", icon: Settings2 },
  ];

  const handleLogout = () => {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
    navigate("/login");
  };

  return (
    <>
      {/* Mobile backdrop overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      <aside className={`w-64 fixed inset-y-0 left-0 glass-panel border-r border-slate-800/80 flex flex-col justify-between z-50 transition-transform duration-300 md:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}>
        {/* Brand Header */}
        <div>
          <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800/50">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <FlaskConical className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-sm tracking-wide text-white leading-none">FOG-MONITOR</h1>
                <span className="text-[10px] text-slate-400 font-medium">KMITL Bioreactor</span>
              </div>
            </div>

            {/* Mobile close button */}
            <button onClick={onClose} className="md:hidden text-slate-400 hover:text-slate-200">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="mt-6 px-4 space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onClose} // Close menu after navigation on mobile
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                    isActive
                      ? "bg-gradient-to-r from-blue-500/20 to-cyan-500/10 text-cyan-400 border-l-4 border-cyan-500"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Session Info & Logout */}
        <div className="p-4 border-t border-slate-800/50 space-y-3">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-800/30">
            <div className="w-8 h-8 rounded-lg bg-slate-700/50 flex items-center justify-center">
              <User className="w-4 h-4 text-slate-300" />
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-slate-200 truncate">{user.username}</p>
              <p className="text-[10px] text-slate-400 font-medium truncate">ผู้ดูแลระบบ</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 transition-all duration-300 border border-rose-500/20"
          >
            <LogOut className="w-4 h-4" />
            <span>ออกจากระบบ</span>
          </button>
        </div>
      </aside>
    </>
  );
}
