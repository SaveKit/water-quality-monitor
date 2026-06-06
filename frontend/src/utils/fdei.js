// sensor_type values used in API
export const SENSOR_TYPES = [
  { key: "ph", label: "pH", unit: "" },
  { key: "co2", label: "CO₂ (MQ-135)", unit: "ppm" },
  { key: "tds", label: "TDS", unit: "ppm" },
  { key: "turbidity", label: "Turbidity", unit: "NTU" },
  { key: "temp", label: "อุณหภูมิ (ควบคุม)", unit: "°C" },
  { key: "fdei", label: "FDEI (ประสิทธิภาพการย่อย)", unit: "%" },
];

// Alert type badges config
export const ALERT_TYPE_CONFIG = {
  PLATEAU: {
    label: "การย่อยชะลอตัว (Plateau)",
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    text: "text-amber-400",
  },
  TARGET_REACHED: {
    label: "ถึงเป้าหมายการย่อยสลาย",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    text: "text-emerald-400",
  },
  ABNORMAL: {
    label: "พารามิเตอร์ผิดปกติ",
    bg: "bg-rose-500/10",
    border: "border-rose-500/20",
    text: "text-rose-400",
  },
};
