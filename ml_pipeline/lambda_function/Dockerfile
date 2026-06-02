# ใช้ AWS Lambda base image สำหรับ Python 3.11
FROM public.ecr.aws/lambda/python:3.11

# ติดตั้ง System dependencies ที่จำเป็น (หากมี)
RUN yum install -y gcc gcc-c++ make

# คัดลอกและติดตั้ง Python dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# คัดลอกโฟลเดอร์โมเดลและโค้ดหลักเข้าไปใน container
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# คัดลอกไฟล์ Handler หลักของ Lambda
COPY app.py ${LAMBDA_TASK_ROOT}/app.py

# ตั้งค่า Handler เริ่มต้นในการเรียกใช้ Lambda
CMD [ "app.lambda_handler" ]
