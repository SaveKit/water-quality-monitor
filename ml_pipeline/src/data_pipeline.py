import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Add parent directory of src to sys.path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preprocess import load_data, handle_missing_values, handle_turbidity_zeros, winsorize_outliers, resample_data
from features import (compute_cumulative_co2, compute_yield_coefficient, compute_fdei,
                       validate_fdei_against_lab, create_sequences_1step, prepare_dataset,
                       process_single_run, prepare_multi_run_dataset)

def handle_outliers_clipping(df, limits=None):
    """
    จัดการ Outliers แบบจำกัดช่วงทางกายภาพ (Clipping)
    """
    df_clipped = df.copy()
    numeric_cols = df_clipped.select_dtypes(include=[np.number]).columns
    
    if limits is None:
        limits = {
            'ph': [0.0, 14.0],
            'tds': [0.0, 5000.0],
            'turbidity': [0.0, 4000.0],
            'temperature': [15.0, 45.0],
            'co2': [0.0, 5.0]
        }
        
    for col in numeric_cols:
        if col in limits:
            min_val, max_val = limits[col]
            outliers = ((df_clipped[col] < min_val) | (df_clipped[col] > max_val)).sum()
            if outliers > 0:
                print(f"คอลัมน์ {col}: ตรวจพบค่าที่อยู่นอกช่วงสมมติ [{min_val}, {max_val}] จำนวน {outliers} แถว ทำการทำ Clipping...")
                df_clipped[col] = np.clip(df_clipped[col], min_val, max_val)
                
    return df_clipped

def handle_outliers_winsorization(df, lower_quantile=0.01, upper_quantile=0.99):
    """
    จัดการ Outliers แบบ Winsorization ตามควอนไทล์
    """
    df_winsorized = df.copy()
    numeric_cols = df_winsorized.select_dtypes(include=[np.number]).columns
    cols_to_process = [col for col in numeric_cols if col not in ['timestamp', 'elapsed_days']]
    
    for col in cols_to_process:
        lower_bound = df_winsorized[col].quantile(lower_quantile)
        upper_bound = df_winsorized[col].quantile(upper_quantile)
        outliers = ((df_winsorized[col] < lower_bound) | (df_winsorized[col] > upper_bound)).sum()
        if outliers > 0:
            print(f"คอลัมน์ {col}: ทำ Winsorization ช่วงเปอร์เซ็นต์ไทล์ [{lower_quantile}, {upper_quantile}] (ขอบเขต [{lower_bound:.3f}, {upper_bound:.3f}]) จำนวน {outliers} แถว...")
            df_winsorized[col] = np.clip(df_winsorized[col], lower_bound, upper_bound)
            
    return df_winsorized

def downsample_data(df, interval='5min'):
    """
    ดาวน์แซมพลิงข้อมูลเฉลี่ย (เวอร์ชันเดิม)
    """
    print(f"กำลังดาวน์แซมพลิงข้อมูลเฉลี่ยทุกๆ {interval}...")
    numeric_df = df.select_dtypes(include=[np.number])
    resampled_df = numeric_df.resample(interval).mean()
    
    if resampled_df.isnull().sum().sum() > 0:
        resampled_df = resampled_df.interpolate(method='linear')
        
    return resampled_df

def feature_engineering_co2(df, co2_col='co2', interval_minutes=5):
    """
    คำนวณฟีเจอร์ก๊าซ CO2 สะสมเชิงชั่วโมง (%-hour)
    """
    df_feat = df.copy()
    time_delta_hours = interval_minutes / 60.0
    df_feat['co2_cumulative'] = (df_feat[co2_col] * time_delta_hours).cumsum()
    print("คำนวณคอลัมน์ 'co2_cumulative' สำเร็จ")
    return df_feat

def scale_features(df, feature_cols, method='minmax'):
    """
    สเกลข้อมูลฟีเจอร์ด้วย MinMax หรือ Standard Scaler
    """
    df_scaled = df.copy()
    if method == 'minmax':
        scaler = MinMaxScaler()
    elif method == 'standard':
        scaler = StandardScaler()
    else:
        raise ValueError("ไม่รองรับวิธีสเกลนี้ เลือก 'minmax' หรือ 'standard'")
        
    df_scaled[feature_cols] = scaler.fit_transform(df_scaled[feature_cols])
    print(f"สเกลข้อมูลฟีเจอร์ {feature_cols} สำเร็จด้วยวิธี: {method}")
    return df_scaled, scaler

def create_sequences(df, input_steps, forecast_steps, feature_cols, target_col):
    """
    สร้างชุดข้อมูลแบบ Sequence (Lookback/Forecast) สำหรับโมเดล SVR/GRU ทั่วไป
    """
    print(f"กำลังจัดเตรียมชุดข้อมูล Sequence (Lookback={input_steps} จุดเวลา, Forecast={forecast_steps} จุดเวลา)...")
    X_data = df[feature_cols].values
    y_data = df[target_col].values
    
    X, y = [], []
    total_len = len(df)
    for i in range(total_len - input_steps - forecast_steps + 1):
        X.append(X_data[i : i + input_steps])
        y.append(y_data[i + input_steps : i + input_steps + forecast_steps])
        
    X_arr = np.array(X)
    y_arr = np.array(y)
    
    print(f"จัดเตรียมสำเร็จ - X shape: {X_arr.shape}, y shape: {y_arr.shape}")
    return X_arr, y_arr

def eda_report(df, features):
    """
    แสดงรายงาน EDA ของตัวแปร
    """
    print('=======================================================')
    print('EDA REPORT')
    print('=======================================================')
    print(f"Rows: {len(df):,},  |  Cols: {df.shape[1]}")
    
    if isinstance(df.index, pd.DatetimeIndex):
        start_time = df.index.min()
        end_time = df.index.max()
    else:
        start_time = df['datetime'].min()
        end_time = df['datetime'].max()
        
    print(f"Start: {start_time}")
    print(f"End  : {end_time}")
    
    if isinstance(df.index, pd.DatetimeIndex):
        diffs = df.index.to_series().diff().dropna().dt.total_seconds()
    else:
        diffs = df['datetime'].diff().dropna().dt.total_seconds()
        
    print('\nSampling interval:')
    print(f"  Median: {diffs.median():.0f}s  |  Min: {diffs.min():.0f}s  |  Max: {diffs.max():.0f}s")
    print(f"  Gaps > 5 min: {(diffs > 300).sum()}")
    
    print(f"\nMissing values: {df[features].isnull().sum().sum()}")
    
    if 'turbidity' in df.columns:
        zero_count = (df['turbidity'] == 0).sum()
        zero_mean = (df['turbidity'] == 0).mean() * 100
        print(f"Turbidity = 0  : {zero_count} ({zero_mean:.1f}%)")
        
    print('\nDescriptive stats:')
    print(df[features].describe().round(4).to_string())
    
    print('\nOutliers (IQR × 1.5):')
    for col in features:
        if col in df.columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            low = Q1 - 1.5 * IQR
            high = Q3 + 1.5 * IQR
            n = ((df[col] < low) | (df[col] > high)).sum()
            print(f"  {col:12s}: {n:5d} ({n / len(df) * 100:.1f}%)")
            
    df_copy = df.copy()
    if 'elapsed_days' in df_copy.columns:
        df_copy['day'] = df_copy['elapsed_days'].astype(int)
        print('\nDaily CO2 mean (Bacillus activity indicator):')
        print(df_copy.groupby('day')['co2'].agg(['mean', 'max']).round(4).to_string())
        
    print('=======================================================')
