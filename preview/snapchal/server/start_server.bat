@echo off
chcp 65001 > nul
echo.
echo ========================================
echo    스냅챌 서버 시작
echo ========================================
echo.

:: Python 가상환경 확인 및 설치
if not exist "venv" (
    echo [1/3] 가상환경 생성 중...
    python -m venv venv
)

echo [2/3] 패키지 설치 중...
call venv\Scripts\activate
pip install -r requirements.txt -q

echo [3/3] 서버 시작!
echo.
echo  주소: http://localhost:8000
echo  (Ctrl+C 로 중지)
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
