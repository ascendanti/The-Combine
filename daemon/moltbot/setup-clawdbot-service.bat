@echo off
REM Setup Clawdbot as Windows Service with NSSM
REM Run as Administrator

echo === Clawdbot Service Setup ===
echo.

REM Check for admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run this script as Administrator
    pause
    exit /b 1
)

set SERVICE_NAME=ClawdbotGateway
set CLAWDBOT_DIR=%USERPROFILE%\.clawdbot
set SCRIPT_DIR=%~dp0

REM Create directories
if not exist "%CLAWDBOT_DIR%" mkdir "%CLAWDBOT_DIR%"
if not exist "%CLAWDBOT_DIR%\logs" mkdir "%CLAWDBOT_DIR%\logs"

REM Copy startup script
copy "%SCRIPT_DIR%start-gateway.bat" "%CLAWDBOT_DIR%\start-gateway.bat"

REM Stop and remove existing service
echo Removing existing service (if any)...
nssm stop %SERVICE_NAME% 2>nul
nssm remove %SERVICE_NAME% confirm 2>nul

REM Install service
echo Installing service...
nssm install %SERVICE_NAME% "%COMSPEC%" "/c %CLAWDBOT_DIR%\start-gateway.bat"
nssm set %SERVICE_NAME% AppDirectory "%CLAWDBOT_DIR%"
nssm set %SERVICE_NAME% DisplayName "Clawdbot Gateway"
nssm set %SERVICE_NAME% Description "Clawdbot AI Gateway - localhost:8080, exposed via Tailscale"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START
nssm set %SERVICE_NAME% AppStdout "%CLAWDBOT_DIR%\logs\gateway.log"
nssm set %SERVICE_NAME% AppStderr "%CLAWDBOT_DIR%\logs\gateway-error.log"
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateBytes 10485760

echo.
echo === Service Installed ===
echo.
echo NEXT STEPS:
echo.
echo 1) First-time setup (run once):
echo    clawdbot onboard --install-daemon
echo.
echo 2) Start the service:
echo    nssm start %SERVICE_NAME%
echo.
echo 3) Expose via Tailscale (run once):
echo    tailscale serve 8080
echo.
echo 4) Access from any tailnet device:
echo    https://^<your-pc-name^>.^<tailnet^>.ts.net/
echo.
echo MANAGEMENT:
echo    nssm status %SERVICE_NAME%
echo    nssm stop %SERVICE_NAME%
echo    nssm restart %SERVICE_NAME%
echo    type "%CLAWDBOT_DIR%\logs\gateway.log"
echo.

pause
