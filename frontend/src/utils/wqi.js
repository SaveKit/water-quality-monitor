export const WQI_CONFIG = {
  GOOD: {
    range: [0, 50],
    label: "ดีเยี่ยม / ดี",
    color: "emerald",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    text: "text-emerald-400",
    btn: "bg-emerald-500 hover:bg-emerald-600 text-white"
  },
  FAIR: {
    range: [51, 75],
    label: "พอใช้",
    color: "amber",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    text: "text-amber-400",
    btn: "bg-amber-500 hover:bg-amber-600 text-white"
  },
  POOR: {
    range: [76, 100],
    label: "แย่มาก",
    color: "orange",
    bg: "bg-orange-500/10",
    border: "border-orange-500/20",
    text: "text-orange-400",
    btn: "bg-orange-500 hover:bg-orange-600 text-white"
  },
  CRITICAL: {
    range: [101, Infinity],
    label: "ไม่เหมาะสมอย่างยิ่ง",
    color: "rose",
    bg: "bg-rose-500/10",
    border: "border-rose-500/20",
    text: "text-rose-400",
    btn: "bg-rose-500 hover:bg-rose-600 text-white"
  },
};

export const TREATMENT_LABELS = {
  GOOD: "เฝ้าระวัง",
  FAIR: "บำบัดขั้นต้น (Primary)",
  POOR: "บำบัดขั้นที่สอง (Secondary)",
  CRITICAL: "บำบัดขั้นสูง (Advanced)",
};

export function getWQIStatus(wqi) {
  if (wqi <= 50) return "GOOD";
  if (wqi <= 75) return "FAIR";
  if (wqi <= 100) return "POOR";
  return "CRITICAL";
}

// sensor_type values ที่ใช้ใน API
export const SENSOR_TYPES = [
  { key: "ph", label: "pH", unit: "" },
  { key: "co2", label: "CO₂", unit: "ppm" },
  { key: "tds", label: "TDS", unit: "ppm" },
  { key: "turbidity", label: "Turbidity", unit: "NTU" },
  { key: "temp", label: "อุณหภูมิ", unit: "°C" },
];
