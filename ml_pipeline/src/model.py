import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (
    Conv1D, MaxPooling1D, GRU, Dense, Input
)

def build_cnn_gru(input_shape: tuple, cfg: dict) -> Model:
    """
    สร้างและคอมไพล์แบบจำลองลูกผสม CNN-GRU
    CNN ทำหน้าที่ดึงข้อมูลท้องถิ่น (Local patterns)
    GRU ทำหน้าที่เรียนรู้ความสัมพันธ์ของเวลาในระยะยาว (Temporal dynamics)
    """
    inputs = Input(shape=input_shape, name='input')

    # ── CNN Block ──
    x = Conv1D(
        filters    = cfg.get('CNN_FILTERS', 64),
        kernel_size= cfg.get('KERNEL_SIZE', 5),
        activation = 'relu',
        padding    = 'causal',        # จำเป็นต้องใช้ causal padding เพื่อคงความยาว time steps
        name       = 'conv1d'
    )(inputs)
    x = MaxPooling1D(pool_size=cfg.get('MAXPOOL_SIZE', 2), name='maxpool')(x)

    # ── GRU Block ──
    x = GRU(
        units    = cfg.get('GRU_UNITS', 32),
        dropout  = cfg.get('DROPOUT', 0.2),
        name     = 'gru'
    )(x)

    # ── Feature Layer (เชื่อมไปรันร่วมกับ SVR ในภายหลัง) ──
    features = Dense(16, activation='relu', name='feature_layer')(x)

    # ── Prediction Head (ใช้ระหว่างการฝึกสอน CNN-GRU) ──
    output = Dense(1, name='output')(features)

    model = Model(inputs, output, name='CNN_GRU')
    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=cfg.get('LR', 0.0008)),
        loss      = 'mse',
        metrics   = ['mae']
    )
    return model

def get_feature_extractor(full_model: Model) -> Model:
    """
    ดึงโมเดลย่อย (Sub-model) ออกมาสำหรับสกัด Features จากข้อมูลนำเข้า
    เพื่อนำ Features นี้ส่งผ่านไปยังโมเดล SVR (Support Vector Regression)
    """
    return Model(
        inputs  = full_model.input,
        outputs = full_model.get_layer('feature_layer').output,
        name    = 'feature_extractor'
    )
