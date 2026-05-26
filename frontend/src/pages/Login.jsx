import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Droplet, Lock, Mail, AlertCircle, ArrowRight } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Read environment variables
  const cognitoUserPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID || "";
  const cognitoClientId = import.meta.env.VITE_COGNITO_APP_CLIENT_ID || "";
  const cognitoRegion = import.meta.env.VITE_COGNITO_REGION || "ap-southeast-1";

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const isMockMode = !cognitoClientId || cognitoClientId.includes("XXXXXX") || cognitoClientId === "XXXXXXXXXXXXXXXX";

    // Standard dev credentials fallback check
    if (isMockMode) {
      console.log("Operating in local mock mode...");
      if (username === "admin" && password === "Password123!") {
        sessionStorage.setItem("token", "mock_token");
        sessionStorage.setItem("user", JSON.stringify({ username: "Admin Local" }));
        navigate("/");
        setLoading(false);
        return;
      } else {
        setError("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง (Mock Mode: admin / Password123!)");
        setLoading(false);
        return;
      }
    }

    // Call Cognito InitiateAuth REST endpoint directly
    try {
      const response = await axios.post(
        `https://cognito-idp.${cognitoRegion}.amazonaws.com/`,
        {
          AuthFlow: "USER_PASSWORD_AUTH",
          ClientId: cognitoClientId,
          AuthParameters: {
            USERNAME: username,
            PASSWORD: password,
          },
        },
        {
          headers: {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
          },
        }
      );

      const authResult = response.data.AuthenticationResult;
      if (authResult && authResult.IdToken) {
        sessionStorage.setItem("token", authResult.IdToken);
        sessionStorage.setItem("user", JSON.stringify({ username }));
        navigate("/");
      } else {
        throw new Error("Authentication succeeded but returned no IdToken.");
      }
    } catch (err) {
      console.error("Cognito login error:", err);
      const errMsg = err.response?.data?.message || err.message || "การเชื่อมต่อกับเซิร์ฟเวอร์ Cognito ล้มเหลว";
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#070913] px-4 relative overflow-hidden">
      {/* Decorative colored glow background */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[150px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[150px] pointer-events-none"></div>

      <div className="w-full max-w-md glass-panel p-8 rounded-3xl border border-slate-800/80 shadow-2xl relative z-10">
        {/* Brand logo header */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/30 mb-4">
            <Droplet className="w-7 h-7 text-white" />
          </div>
          <h2 className="text-2xl font-black tracking-tight text-white">ระบบเฝ้าระวังคุณภาพน้ำ</h2>
          <p className="text-slate-400 text-sm mt-1 font-semibold">ลงชื่อเข้าใช้งาน Dashboard (KMITL)</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-start gap-2 text-xs font-semibold">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          {/* Email / Username field */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">ชื่อผู้ใช้ / อีเมล</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Mail className="w-4 h-4 text-slate-500" />
              </span>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ระบุชื่อผู้ใช้งาน"
                className="w-full bg-[#0a0d19] border border-slate-800 focus:border-cyan-500 text-white rounded-2xl py-3 pl-11 pr-4 text-sm font-semibold transition-all duration-300 outline-none"
              />
            </div>
          </div>

          {/* Password field */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">รหัสผ่าน</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Lock className="w-4 h-4 text-slate-500" />
              </span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="ระบุรหัสผ่านของคุณ"
                className="w-full bg-[#0a0d19] border border-slate-800 focus:border-cyan-500 text-white rounded-2xl py-3 pl-11 pr-4 text-sm font-semibold transition-all duration-300 outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white font-bold rounded-2xl py-3.5 transition-all duration-300 shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 mt-4 disabled:opacity-50 text-sm"
          >
            {loading ? "กำลังตรวจสอบข้อมูล..." : "เข้าสู่ระบบการตรวจสอบ"}
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
