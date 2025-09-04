@echo off
setlocal enabledelayedexpansion

set "STEAM_DIR=C:\Program Files (x86)\Steam"
set "DEPOTCACHE=%STEAM_DIR%\config\depotcache"
set "STPLUGIN=%STEAM_DIR%\config\stplug-in"
set "HID_DLL=%STEAM_DIR%\hid.dll"
set "LUAPACKA=%STPLUGIN%\luapacka.exe"
set "TEMP_EXTRACT=%TEMP%\steam_extract"
set "SEVEN_ZIP=C:\Program Files\7-Zip\7z.exe"

set "HID_URL=https://github.com/2backside/am/raw/refs/heads/main/Steam/hid.dll"
set "LUAPACKA_URL=https://github.com/2backside/am/raw/refs/heads/main/Steam/config/stplug-in/luapacka.exe"

if not exist "%HID_DLL%" (
    powershell -Command "Invoke-WebRequest -Uri '%HID_URL%' -OutFile '%HID_DLL%'"
)

if not exist "%DEPOTCACHE%" mkdir "%DEPOTCACHE%"
if not exist "%STPLUGIN%" mkdir "%STPLUGIN%"

if not exist "%LUAPACKA%" (
    powershell -Command "Invoke-WebRequest -Uri '%LUAPACKA_URL%' -OutFile '%LUAPACKA%'"
)

if exist "%TEMP_EXTRACT%" rd /s /q "%TEMP_EXTRACT%"
mkdir "%TEMP_EXTRACT%"

if not "%~1"=="" (
    for %%F in (%*) do (
        set "file=%%~fF"
        set "ext=%%~xF"

        if /I "!ext!"==".zip" (
            "%SEVEN_ZIP%" x -y "!file!" -o"%TEMP_EXTRACT%" >nul
        ) else if /I "!ext!"==".rar" (
            "%SEVEN_ZIP%" x -y "!file!" -o"%TEMP_EXTRACT%" >nul
        ) else if /I "!ext!"==".lua" (
            move "!file!" "!STPLUGIN!" >nul
        ) else if /I "!ext!"==".manifest" (
            move "!file!" "!DEPOTCACHE!" >nul
        )
    )
)

if exist "%TEMP_EXTRACT%" (
    for /r "%TEMP_EXTRACT%" %%F in (*) do (
        set "ext=%%~xF"
        if /I "!ext!"==".lua" (
            move "%%F" "!STPLUGIN!" >nul
        ) else if /I "!ext!"==".manifest" (
            move "%%F" "!DEPOTCACHE!" >nul
        )
    )
    rd /s /q "%TEMP_EXTRACT%"
)

cd /d "%STPLUGIN%"

for %%F in (*.lua) do (
    "%LUAPACKA%" "%%~F"
)

tasklist | find /i "steam.exe" >nul
if %errorlevel% == 0 (
    taskkill /F /IM steam.exe >nul
    timeout /t 3 /nobreak >nul
)

start "" "%STEAM_DIR%\Steam.exe"
exit
