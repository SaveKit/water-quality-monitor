import os
import sys
import numpy as np

# Add parent directory of src to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model import build_cnn_gru, get_feature_extractor
from train import train_cnn_gru, train_svr, full_train_pipeline, evaluate_model, plot_results

def predict_fdei_from_co2(co2_forecast, current_co2_cum, interval_seconds, fog_day0, Y):
    """
    คำนวณหา FDEI แบบพยากรณ์สะสมแบบต่อเนื่องโดยใช้ค่า CO2 พยากรณ์
    """
    future_cum = current_co2_cum + np.cumsum(co2_forecast) * interval_seconds
    fog_est = fog_day0 - (future_cum / Y)
    fog_est = np.clip(fog_est, 0, fog_day0)
    fdei_forecast = (fog_day0 - fog_est) / fog_day0 * 100
    return np.clip(fdei_forecast, 0, 100)
