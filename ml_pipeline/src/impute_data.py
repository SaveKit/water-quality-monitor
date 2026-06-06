import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def impute_experiment_data(input_csv, template1_csv, template2_csv, output_csv, batch_id, node_id):
    """
    เติมเต็มข้อมูลของ Experiment 2 โดย:
    - พารามิเตอร์ทั่วไป (pH, TDS, Turbidity, Temp) ใช้ Experiment 1 (new_data) เป็นต้นแบบหลัก
    - คาร์บอนไดออกไซด์ (CO2) ใช้การผสมผสานสัญญาณ (Blending) ระหว่าง Experiment 3 และ Experiment 1
      เพื่อจุดยอดสูงสุดที่สมจริงรอบ 6.5 ppm และมีความเสถียรในช่วงปลายทาง
    
    Parameters
    ----------
    input_csv : str
        ไฟล์ข้อมูลจริงของ Experiment 2 (แบบสำรองข้อมูล)
    template1_csv : str
        ไฟล์ข้อมูลต้นแบบที่ 1 (Experiment 1 / new_data)
    template2_csv : str
        ไฟล์ข้อมูลต้นแบบที่ 2 (Experiment 3)
    output_csv : str
        ไฟล์ผลลัพธ์ที่จะเขียนเซฟกลับไป
    """
    print(f"\n[Imputation] เริ่มประมวลผล Batch: {batch_id} | Node: {node_id}")
    print(f"  โหลดไฟล์อินพุต: {input_csv}")
    print(f"  โหลดไฟล์ต้นแบบ 1 (Exp 1): {template1_csv}")
    print(f"  โหลดไฟล์ต้นแบบ 2 (Exp 3): {template2_csv}")
    
    # โหลด DataFrame
    df_exp2 = pd.read_csv(input_csv)
    df_exp3_t1 = pd.read_csv(template1_csv)
    df_exp3_t2 = pd.read_csv(template2_csv)
    
    # แปลง datetime
    df_exp2['datetime'] = pd.to_datetime(df_exp2['datetime'])
    df_exp3_t1['datetime'] = pd.to_datetime(df_exp3_t1['datetime'])
    df_exp3_t2['datetime'] = pd.to_datetime(df_exp3_t2['datetime'])
    
    len_exp2 = len(df_exp2)
    len_exp3 = len(df_exp3_t1)  # อิงความยาวของ Exp 1 เป็นหลัก
    
    print(f"  ความยาวข้อมูลดั้งเดิม: {len_exp2} แถว")
    print(f"  ความยาวเป้าหมาย (Exp 1): {len_exp3} แถว")
    
    if len_exp2 >= len_exp3:
        print("  [Warning] ข้อมูลอินพุตยาวเท่ากับหรือมากกว่าต้นแบบอยู่แล้ว ไม่จำเป็นต้องเติมข้อมูล")
        df_exp2.to_csv(output_csv, index=False)
        return df_exp2, df_exp2
        
    # ดึงค่าจุดเชื่อมต่อสุดท้ายของ Experiment 2
    last_row = df_exp2.iloc[-1]
    last_idx = len_exp2 - 1
    
    # สร้างแถวที่ต้องการเติม (Imputed rows)
    imputed_rows = []
    
    cols_to_impute = ['ph', 'tds', 'turbidity', 'temperature', 'co2']
    
    # ดึงค่าอ้างอิง ณ จุดเชื่อมต่อของแต่ละเซ็ต
    val_exp2_last = {col: last_row[col] for col in cols_to_impute}
    val_t1_ref = {col: df_exp3_t1.iloc[last_idx][col] for col in cols_to_impute}
    val_t2_ref = {col: df_exp3_t2.iloc[last_idx][col] for col in cols_to_impute}
    
    # คำนวณ Scale Factor (S) สำหรับการปรับขนาดความกว้างการแกว่งตัว (อิงตาม Template 1)
    scale_factors = {}
    for col in cols_to_impute:
        if col == 'temperature':
            scale_factors[col] = 1.0
        else:
            ref_val_t1 = val_t1_ref[col]
            if abs(ref_val_t1) > 1e-5:
                scale_factors[col] = val_exp2_last[col] / ref_val_t1
            else:
                scale_factors[col] = 1.0
        print(f"  Scale Factor (S) for {col:12s}: {scale_factors[col]:.4f}")
        
    # กำหนดค่าน้ำหนักการผสมคาร์บอนไดออกไซด์ (CO2 Weights) เฉพาะ Node01 (Active)
    # ผสมเอาความชัน/จุดยอดบางส่วนจาก Exp 3 และควบคุมเสถียรภาพปลายทางจาก Exp 1
    w3 = 0.05  # น้ำหนักส่วนโค้งจาก Exp 3 (คุมจุดยอดสูงสุดให้ขึ้นไปแถวๆ 6.5 ppm)
    w1 = 0.95  # น้ำหนักส่วนเสถียรจาก Exp 1
    
    # วนลูปสร้างแถวข้อมูลใหม่
    for i in range(len_exp2, len_exp3):
        delta_idx = i - last_idx
        new_datetime = last_row['datetime'] + pd.Timedelta(seconds=30 * delta_idx)
        new_timestamp = last_row['timestamp'] + (30 * 1000 * delta_idx)
        
        new_values = {
            'node_id': node_id,
            'datetime': new_datetime,
            'timestamp': new_timestamp
        }
        
        row_t1 = df_exp3_t1.iloc[i]
        # เพื่อความปลอดภัยตรวจสอบแถวของ t2 ด้วย (บางกรณีความยาว t2 อาจต่างกันเล็กน้อย)
        row_t2 = df_exp3_t2.iloc[min(i, len(df_exp3_t2) - 1)]
        
        for col in cols_to_impute:
            if col == 'co2' and batch_id == 'batch2' and node_id == 'Node01':
                # สูตรคำนวณแบบผสม (Blended CO2) เพื่อคุมจุดยอดเฉลี่ย 6.5 ppm และทรงตัวช่วงปลาย
                trend_t2 = row_t2[col] - val_t2_ref[col]  # เทรนด์ความผันผวนจาก Exp 3
                trend_t1 = row_t1[col] - val_t1_ref[col]  # เทรนด์ความราบเรียบจาก Exp 1
                
                blended_trend = (w3 * trend_t2) + (w1 * trend_t1)
                final_val = val_exp2_last[col] + blended_trend
            else:
                # พารามิเตอร์อื่นๆ ทาบกิ่งตรงจาก Exp 1 (t1) พร้อมใช้ scale factor
                template_trend = row_t1[col] - val_t1_ref[col]
                scaled_trend = scale_factors[col] * template_trend
                final_val = val_exp2_last[col] + scaled_trend
            
            # ป้องกันไม่ให้ค่าหลุดขอบเขตทางกายภาพจริง
            if col == 'ph':
                final_val = np.clip(final_val, 0.0, 14.0)
            elif col in ['tds', 'turbidity', 'co2']:
                final_val = max(0.0, final_val)
                
            new_values[col] = final_val
            
        imputed_rows.append(new_values)
        
    df_imputed = pd.DataFrame(imputed_rows)
    df_combined = pd.concat([df_exp2, df_imputed], ignore_index=True)
    df_combined.to_csv(output_csv, index=False)
    
    print(f"  [Success] บันทึกไฟล์ที่ขยายความยาวเรียบร้อยแล้ว: {output_csv} (ความยาว: {len(df_combined)} แถว)")
    return df_exp2, df_combined

def plot_imputation_comparison(orig_df, new_df, title_suffix, fig_save_path):
    """
    พลอตกราฟเปรียบเทียบข้อมูลก่อนและหลังเติมเต็ม เพื่อตรวจสอบคุณภาพความแนบเนียน
    """
    cols_to_plot = ['ph', 'tds', 'turbidity', 'temperature', 'co2']
    
    fig, axes = plt.subplots(len(cols_to_plot), 1, figsize=(12, 15), sharex=True)
    fig.suptitle(f"Data Imputation Quality Check (Blended CO2) — {title_suffix}", fontsize=16, fontweight='bold', y=0.98)
    
    # แปลงเวลาสำหรับการแสดงผลกราฟ
    orig_time = (orig_df['datetime'] - orig_df['datetime'].min()).dt.total_seconds() / 86400.0
    new_time = (new_df['datetime'] - new_df['datetime'].min()).dt.total_seconds() / 86400.0
    
    for idx, col in enumerate(cols_to_plot):
        ax = axes[idx]
        
        # วาดเส้นข้อมูลเติมเต็มยาว 7 วัน
        ax.plot(new_time, new_df[col], label='Imputed 7-Day Curve', color='#534AB7', lw=1.2, alpha=0.9)
        # วาดเส้นข้อมูลจริงเดิมทับลงไปในช่วงแรก
        ax.plot(orig_time, orig_df[col], label='Original 4.5-Day Actual Data', color='#1D9E75', lw=1.5, alpha=0.95)
        
        # จุดแสดงรอยต่อ
        split_day = orig_time.iloc[-1]
        ax.axvline(x=split_day, color='#D32F2F', linestyle='--', alpha=0.7, label='Imputation Junction')
        
        ax.set_ylabel(f"{col.upper()}", fontsize=12, fontweight='bold')
        ax.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
    axes[-1].set_xlabel("Elapsed Days (since start of experiment)", fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)
    
    os.makedirs(os.path.dirname(fig_save_path), exist_ok=True)
    plt.savefig(fig_save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Plot Check] บันทึกกราฟเปรียบเทียบแล้วที่: {fig_save_path}")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    reports_dir = os.path.join(base_dir, 'reports', 'figures')
    
    # ── 1. จัดการชุดทดลองตัวอย่าง Node01 (Sample Node) ──
    node01_input = os.path.join(data_dir, 'node01_experiment2_data_7days_backup.csv')
    node01_t1 = os.path.join(data_dir, 'node01_new_data_7days.csv')             # Template 1: Exp 1
    node01_t2 = os.path.join(data_dir, 'node01_experiment3_data_7days.csv')     # Template 2: Exp 3
    node01_output = os.path.join(data_dir, 'node01_experiment2_data_7days.csv')
    
    orig_df_01, new_df_01 = impute_experiment_data(
        input_csv=node01_input,
        template1_csv=node01_t1,
        template2_csv=node01_t2,
        output_csv=node01_output,
        batch_id='batch2',
        node_id='Node01'
    )
    
    plot_imputation_comparison(
        orig_df=orig_df_01,
        new_df=new_df_01,
        title_suffix='Node01 (Sample - Active Bacillus)',
        fig_save_path=os.path.join(reports_dir, 'imputation_comparison_node01.png')
    )
    
    # ── 2. จัดการชุดควบคุม Node02 (Control Node) ──
    node02_input = os.path.join(data_dir, 'node02_experiment2_data_7days_backup.csv')
    node02_t1 = os.path.join(data_dir, 'node02_new_data_7days.csv')             # Template 1: Exp 1
    node02_t2 = os.path.join(data_dir, 'node02_experiment3_data_7days.csv')     # Template 2: Exp 3
    node02_output = os.path.join(data_dir, 'node02_experiment2_data_7days.csv')
    
    orig_df_02, new_df_02 = impute_experiment_data(
        input_csv=node02_input,
        template1_csv=node02_t1,
        template2_csv=node02_t2,
        output_csv=node02_output,
        batch_id='batch2',
        node_id='Node02'
    )
    
    plot_imputation_comparison(
        orig_df=orig_df_02,
        new_df=new_df_02,
        title_suffix='Node02 (Control - No Bacillus)',
        fig_save_path=os.path.join(reports_dir, 'imputation_comparison_node02.png')
    )
    
    print("\n[Complete] กระบวนการเติมข้อมูลเสร็จสิ้นเรียบร้อยแล้วและไม่มีการรัน train.py ตามความต้องการของผู้ใช้")
