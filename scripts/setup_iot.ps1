# scripts/setup_iot.ps1

Write-Host "Starting AWS IoT Setup..."

# 1. สร้าง Thing
aws iot create-thing --thing-name "Node01"
aws iot create-thing --thing-name "Node02"

# 2. สร้าง Keys และ Certificate (Node01)
# PowerShell สามารถรับ JSON และแปลงเป็น Object ได้เลย ไม่ต้องใช้ jq
$cert01 = aws iot create-keys-and-certificate `
    --set-as-active `
    --certificate-pem-outfile "firmware/Node01/Node01.cert.pem" `
    --public-key-outfile "firmware/Node01/Node01.public.key" `
    --private-key-outfile "firmware/Node01/Node01.private.key" `
    | ConvertFrom-Json

# ทำซ้ำสำหรับ Node02
$cert02 = aws iot create-keys-and-certificate `
    --set-as-active `
    --certificate-pem-outfile "firmware/Node02/Node02.cert.pem" `
    --public-key-outfile "firmware/Node02/Node02.public.key" `
    --private-key-outfile "firmware/Node02/Node02.private.key" `
    | ConvertFrom-Json

# 3. สร้าง Policy
$policyDoc = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = "iot:*"
            Resource = "*"
        }
    )
} | ConvertTo-Json -Depth 4

aws iot create-policy `
    --policy-name "WaterQualityPolicy" `
    --policy-document $policyDoc

# 4. Attach Policy และ Thing เข้ากับ Certificate
# Node 01
aws iot attach-thing-principal --thing-name "Node01" --principal $cert01.certificateArn
aws iot attach-policy --policy-name "WaterQualityPolicy" --target $cert01.certificateArn

# Node 02
aws iot attach-thing-principal --thing-name "Node02" --principal $cert02.certificateArn
aws iot attach-policy --policy-name "WaterQualityPolicy" --target $cert02.certificateArn

Write-Host "Done! Keys are saved in firmware/Node01/ and firmware/Node02/"