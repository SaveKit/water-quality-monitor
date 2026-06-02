import pandas as pd
import numpy as np

def load_data(file_path):
    """
    โหลดข้อมูลดิบจากไฟล์ CSV ปรับปรุง datetime และตั้งเป็น Index
    """
    print(f"[Preprocess] โหลดข้อมูลจาก: {file_path}")
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    # คำนวณ elapsed_days เพื่อรองรับโมเดล AI
    df['elapsed_days'] = (df.index - df.index.min()).total_seconds() / 86400.0
    return df

def handle_missing_values(df, method='bfill'):
    """
    จัดการค่าว่างใน DataFrame
    method: 'bfill' (Backward Fill), 'ffill' (Forward Fill), 'interpolate' (Linear Interpolation)
    """
    df_clean = df.copy()
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        null_count = df_clean[col].isnull().sum()
        if null_count > 0:
            print(f"[Preprocess] พบค่าว่างในคอลัมน์ {col} จำนวน {null_count} แถว จัดการด้วยวิธี {method}...")
            
            if method == 'bfill':
                df_clean[col] = df_clean[col].bfill()
            elif method == 'ffill':
                df_clean[col] = df_clean[col].ffill()
            elif method == 'interpolate':
                df_clean[col] = df_clean[col].interpolate(method='linear')
            else:
                raise ValueError("ไม่รองรับวิธีล้างค่าว่างนี้ เลือก 'bfill', 'ffill', หรือ 'interpolate'")
                
    # เก็บตกกรณีค่าแรกสุดหรือท้ายสุดยังว่างอยู่
    df_clean[numeric_cols] = df_clean[numeric_cols].bfill().ffill()
    return df_clean

def handle_turbidity_zeros(df):
    """
    ตรวจหาค่า Turbidity ที่เป็น 0.0 ผิดปกติ แล้วทำการแทนที่และ Interpolate
    เนื่องจากข้อมูลดิบมีค่าเป็น 0 บ่อย ซึ่งมักเกิดจากเซนเซอร์เออร์เรอร์
    """
    df = df.copy()
    if 'turbidity' in df.columns:
        zero_count = (df['turbidity'] == 0).sum()
        if zero_count > 0:
            print(f"[Preprocess] พบ Turbidity = 0 จำนวน {zero_count} แถว ทำการแทนที่ด้วยการ Interpolate")
            df.loc[df['turbidity'] == 0, 'turbidity'] = np.nan
            df['turbidity'] = df['turbidity'].interpolate(method='linear').ffill().bfill()
    return df

def winsorize_outliers(df, cols, iqr_factor=3.0):
    """
    จัดการ Outliers ด้วยวิธี Winsorization โดยการ Clip ค่าที่อยู่นอกช่วง IQR
    ใช้ iqr_factor=3.0 เพื่อคงความผันผวนทางชีวภาพของแบคทีเรียไว้
    """
    df = df.copy()
    for col in cols:
        if col in df.columns:
            Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
            IQR = Q3 - Q1
            low  = Q1 - iqr_factor * IQR
            high = Q3 + iqr_factor * IQR
            before = ((df[col] < low) | (df[col] > high)).sum()
            df[col] = df[col].clip(low, high)
            if before > 0:
                print(f"[Preprocess] {col:12s}: ทำ Winsorization ไป {before} แถว → ช่วง [{low:.4f}, {high:.4f}]")
    return df

def resample_data(df, interval='5min'):
    """
    ดาวน์แซมพลิงค่าความละเอียด 30 วินาที ให้เป็นช่วงเวลาที่ยาวขึ้น (เช่น 5 นาที)
    เพื่อช่วยลด Noise และทำให้ Model เรียนรู้ทิศทางเวลาได้ดีขึ้น
    """
    df = df.copy()
    if 'datetime' in df.columns:
        df.set_index('datetime', inplace=True)
        
    # เลือกเฉพาะฟีเจอร์หลักที่จะรันใน Model
    agg_cols = [col for col in ['ph', 'tds', 'turbidity', 'temperature', 'co2', 'elapsed_days'] if col in df.columns]
    df_resampled = df[agg_cols].resample(interval).mean()
    
    # หากเกิดค่าว่างขึ้นหลัง resampling ให้ทำการ interpolate
    if df_resampled.isnull().sum().sum() > 0:
        df_resampled = df_resampled.interpolate(method='linear').bfill().ffill()
        
    df_resampled = df_resampled.reset_index()
    print(f"[Preprocess] Resampled เป็น {interval}: {len(df):,} แถว → {len(df_resampled):,} แถว")
    return df_resampled
