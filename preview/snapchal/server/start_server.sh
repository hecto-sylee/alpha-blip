#!/bin/bash
echo "========================================"
echo "   스냅챌 서버 시작"
echo "========================================"
echo

# 가상환경 생성
if [ ! -d "venv" ]; then
    echo "[1/3] 가상환경 생성 중..."
    python3 -m venv venv
fi

echo "[2/3] 패키지 설치 중..."
source venv/bin/activate
pip install -r requirements.txt -q

echo "[3/3] 서버 시작!"
echo
echo " 주소: http://localhost:8000"
echo " (Ctrl+C 로 중지)"
echo

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
