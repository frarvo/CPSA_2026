#!/bin/bash
sudo xmutil unloadapp
sleep 2
sudo xmutil loadapp kv260-benchmark-b4096
sleep 2
sudo xmutil listapps
sleep 2
export XLNX_VART_FIRMWARE=/home/ubuntu/Desktop/PROJECT_CPSA_2026/DPU_FIRMWARE/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
sleep 2 
echo $XLNX_VART_FIRMWARE
sleep 2
