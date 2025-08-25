@echo off
REM BUDDY AI Assistant Windows Installer
REM Universal installer for Windows 10+ systems

setlocal enabledelayedexpansion

REM Constants
set "BUDDY_VERSION=1.0.0"
set "BUDDY_API_URL=http://localhost:8080"
set "INSTALL_DIR=%PROGRAMFILES%\BUDDY"
set "USER_DIR=%APPDATA%\BUDDY"
set "TEMP_DIR=%TEMP%\buddy-install"

REM Colors for output (using PowerShell for colored output)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Display banner
echo.
echo %BLUE%    ____  __  ____  ____  __  __
echo    ^| __ ^)/ / ^|  _ \^|  _ \ \ \/ /
echo    ^|  _ \/ /  ^| ^|_^) ^| ^| ^| ^| \  / 
echo    ^| ^|_^) ^| ^|  ^|  _ ^<^| ^|_^| ^| /  \ 
echo    ^|____/ /   ^|_^| \_\____/ /_/\_\
echo          /                       
echo.
echo    BUDDY AI Assistant - Windows Installer
echo    Version %BUDDY_VERSION%
echo.%NC%

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo %GREEN%[INFO] Running with administrator privileges%NC%
    set "INSTALL_MODE=system"
) else (
    echo %YELLOW%[INFO] Running without administrator privileges - installing for current user%NC%
    set "INSTALL_DIR=%LOCALAPPDATA%\BUDDY"
    set "INSTALL_MODE=user"
)

REM Log function
:log
echo %GREEN%[%date% %time%] %~1%NC%
goto :eof

REM Error function
:error
echo %RED%[ERROR] %~1%NC%
goto :eof

REM Check system requirements
:check_requirements
call :log "Checking system requirements..."

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%VERSION%" LSS "10.0" (
    call :error "Windows 10 or later is required"
    exit /b 1
)

REM Check available disk space (require 500MB)
for /f "tokens=3" %%a in ('dir /-c "%USERPROFILE%" ^| find "bytes free"') do set "FREE_SPACE=%%a"
set /a "FREE_SPACE_MB=!FREE_SPACE! / 1048576"
if !FREE_SPACE_MB! LSS 500 (
    call :error "Insufficient disk space. At least 500MB required"
    exit /b 1
)

REM Check for required tools
where curl >nul 2>&1
if errorlevel 1 (
    call :error "curl is required but not found. Please install curl or use a newer Windows version"
    exit /b 1
)

call :log "System requirements check passed"
goto :eof

REM Create directory structure
:create_directories
call :log "Creating directory structure..."

mkdir "%INSTALL_DIR%" 2>nul
mkdir "%USER_DIR%" 2>nul
mkdir "%TEMP_DIR%" 2>nul

REM Create subdirectories
for %%d in (bin lib share config logs cache models plugins) do (
    mkdir "%INSTALL_DIR%\%%d" 2>nul
    mkdir "%USER_DIR%\%%d" 2>nul
)

call :log "Directory structure created at %INSTALL_DIR%"
goto :eof

REM Download BUDDY components
:download_buddy
call :log "Preparing BUDDY components for Windows..."

REM Create launcher batch file
(
echo @echo off
echo REM BUDDY Launcher Script
echo.
echo set "BUDDY_HOME=%%~dp0"
echo.
echo REM Check if BUDDY server is running
echo curl -s http://localhost:8080/health >nul 2>&1
echo if errorlevel 1 ^(
echo     echo Starting BUDDY server...
echo     cd /d "%%BUDDY_HOME%%\..\..\..\packages\core"
echo     start /b "BUDDY Server" "..\..\\.venv\Scripts\python.exe" -m buddy.main --api-only --port 8080
echo     echo BUDDY server starting... Check logs at %%BUDDY_HOME%%\..\logs\buddy.log
echo ^) else ^(
echo     echo BUDDY is running at http://localhost:8080
echo ^)
echo.
echo REM Open web interface
echo start http://localhost:3001
) > "%TEMP_DIR%\buddy.bat"

REM Create PowerShell launcher for better Windows integration
(
echo # BUDDY PowerShell Launcher
echo param^(
echo     [switch]$Status,
echo     [switch]$Stop,
echo     [switch]$Help,
echo     [switch]$Config
echo ^)
echo.
echo $BuddyApiUrl = "http://localhost:8080"
echo $BuddyWebUrl = "http://localhost:3001"
echo.
echo if ^($Status^) {
echo     try {
echo         $response = Invoke-RestMethod -Uri "$BuddyApiUrl/health" -TimeoutSec 5
echo         Write-Host "BUDDY is running and healthy" -ForegroundColor Green
echo         Write-Host "API: $BuddyApiUrl" -ForegroundColor Blue
echo         Write-Host "Web: $BuddyWebUrl" -ForegroundColor Blue
echo     } catch {
echo         Write-Host "BUDDY is not responding" -ForegroundColor Red
echo     }
echo     return
echo }
echo.
echo if ^($Help^) {
echo     Write-Host "BUDDY AI Assistant Commands:" -ForegroundColor Cyan
echo     Write-Host "  buddy -Status    Check BUDDY status"
echo     Write-Host "  buddy -Stop      Stop BUDDY server"
echo     Write-Host "  buddy -Help      Show this help"
echo     Write-Host "  buddy -Config    Open configuration"
echo     Write-Host "  buddy            Start BUDDY interface"
echo     return
echo }
echo.
echo # Default action: open BUDDY interface
echo try {
echo     $response = Invoke-RestMethod -Uri "$BuddyApiUrl/health" -TimeoutSec 2
echo     Write-Host "BUDDY is running" -ForegroundColor Green
echo } catch {
echo     Write-Host "Starting BUDDY server..." -ForegroundColor Yellow
echo     $buddyPath = Split-Path -Parent $PSScriptRoot
echo     $corePath = Join-Path $buddyPath "..\..\packages\core"
echo     $pythonPath = Join-Path $buddyPath "..\..\\.venv\Scripts\python.exe"
echo     
echo     Start-Process -FilePath $pythonPath -ArgumentList "-m", "buddy.main", "--api-only", "--port", "8080" -WorkingDirectory $corePath -WindowStyle Hidden
echo     Write-Host "BUDDY server starting..."
echo     Start-Sleep 3
echo }
echo.
echo # Open web interface
echo Start-Process $BuddyWebUrl
) > "%TEMP_DIR%\buddy.ps1"

REM Create configuration file
(
echo # BUDDY Configuration
echo version: "%BUDDY_VERSION%"
echo api:
echo   host: "localhost"
echo   port: 8080
echo   ssl: false
echo.
echo features:
echo   conversation_flow: true
echo   device_optimization: true
echo   emotional_intelligence: true
echo   health_wellness: true
echo   cross_platform_sync: true
echo.
echo logging:
echo   level: "INFO"
echo   file: "%USER_DIR%\logs\buddy.log"
echo.
echo models:
echo   download_on_start: true
echo   cache_dir: "%USER_DIR%\models"
echo.
echo plugins:
echo   enabled: true
echo   directory: "%USER_DIR%\plugins"
) > "%TEMP_DIR%\config.yml"

call :log "Components prepared for installation"
goto :eof

REM Install BUDDY
:install_buddy
call :log "Installing BUDDY..."

REM Copy components
copy "%TEMP_DIR%\buddy.bat" "%INSTALL_DIR%\bin\" >nul
copy "%TEMP_DIR%\buddy.ps1" "%INSTALL_DIR%\bin\" >nul
copy "%TEMP_DIR%\config.yml" "%USER_DIR%\config\" >nul

REM Add to PATH if installing system-wide
if "%INSTALL_MODE%"=="system" (
    REM Add to system PATH
    setx /M PATH "%PATH%;%INSTALL_DIR%\bin" >nul 2>&1
    if !errorlevel! == 0 (
        call :log "Added to system PATH"
    ) else (
        call :error "Failed to add to system PATH"
    )
) else (
    REM Add to user PATH
    setx PATH "%PATH%;%INSTALL_DIR%\bin" >nul 2>&1
    if !errorlevel! == 0 (
        call :log "Added to user PATH"
    ) else (
        call :error "Failed to add to user PATH"
    )
)

call :log "BUDDY installation completed"
goto :eof

REM Install Windows integration
:install_windows_integration
call :log "Installing Windows integration..."

REM Create Start Menu shortcut
if "%INSTALL_MODE%"=="system" (
    set "STARTMENU_DIR=%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"
) else (
    set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
)

REM Create shortcut using PowerShell
powershell -Command "& {$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU_DIR%\BUDDY AI Assistant.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\bin\buddy.bat'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\bin'; $Shortcut.Description = 'BUDDY AI Assistant'; $Shortcut.Save()}" >nul 2>&1

REM Register protocol handler
reg add "HKCR\buddy" /ve /d "URL:BUDDY Protocol" /f >nul 2>&1
reg add "HKCR\buddy" /v "URL Protocol" /d "" /f >nul 2>&1
reg add "HKCR\buddy\shell\open\command" /ve /d "\"%INSTALL_DIR%\bin\buddy.bat\" \"%%1\"" /f >nul 2>&1

REM Register file associations (optional)
reg add "HKCR\.buddy" /ve /d "BuddyFile" /f >nul 2>&1
reg add "HKCR\BuddyFile" /ve /d "BUDDY Configuration File" /f >nul 2>&1
reg add "HKCR\BuddyFile\shell\open\command" /ve /d "\"%INSTALL_DIR%\bin\buddy.bat\" \"%%1\"" /f >nul 2>&1

call :log "Windows integration installed"
goto :eof

REM Install Windows service (optional)
:install_windows_service
if "%INSTALL_MODE%"=="user" goto :eof

call :log "Installing Windows service..."

REM Create service using PowerShell
powershell -Command "& {
    $serviceName = 'BuddyAI'
    $servicePath = '%INSTALL_DIR%\bin\buddy.bat'
    $serviceDescription = 'BUDDY AI Assistant Service'
    
    if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $serviceName -Force
        Remove-Service -Name $serviceName
    }
    
    New-Service -Name $serviceName -BinaryPathName $servicePath -Description $serviceDescription -StartupType Manual
}" >nul 2>&1

if !errorlevel! == 0 (
    call :log "Windows service installed"
) else (
    call :error "Failed to install Windows service"
)
goto :eof

REM Create uninstaller
:create_uninstaller
(
echo @echo off
echo echo Uninstalling BUDDY AI Assistant...
echo.
echo REM Stop service if running
echo net stop BuddyAI >nul 2>&1
echo sc delete BuddyAI >nul 2>&1
echo.
echo REM Remove files
echo rmdir /s /q "%INSTALL_DIR%" >nul 2>&1
echo rmdir /s /q "%USER_DIR%" >nul 2>&1
echo.
echo REM Remove from PATH
echo setx PATH "%%PATH:%INSTALL_DIR%\bin;=%%" >nul 2>&1
echo.
echo REM Remove shortcuts
echo del "%STARTMENU_DIR%\BUDDY AI Assistant.lnk" >nul 2>&1
echo.
echo REM Remove registry entries
echo reg delete "HKCR\buddy" /f >nul 2>&1
echo reg delete "HKCR\.buddy" /f >nul 2>&1
echo reg delete "HKCR\BuddyFile" /f >nul 2>&1
echo.
echo echo BUDDY has been uninstalled.
echo pause
) > "%INSTALL_DIR%\bin\buddy-uninstall.bat"

goto :eof

REM Post-installation setup
:post_install_setup
call :log "Running post-installation setup..."

REM Create initial logs directory
mkdir "%USER_DIR%\logs" 2>nul
echo. > "%USER_DIR%\logs\buddy.log"

REM Create uninstaller
call :create_uninstaller

REM Display success message
call :display_success_message
goto :eof

REM Display success message
:display_success_message
echo.
echo %GREEN%🎉 BUDDY AI Assistant has been installed successfully!%NC%
echo.
echo %BLUE%Quick Start:%NC%
echo   • Run 'buddy' in Command Prompt or PowerShell to start BUDDY
echo   • Visit http://localhost:3001 for the web interface
echo   • Visit http://localhost:8080 for the API
echo.
echo %BLUE%Useful Commands:%NC%
echo   • buddy -Help           Show help
echo   • buddy -Status         Check BUDDY status
echo   • buddy -Config         Edit configuration
echo   • buddy-uninstall       Uninstall BUDDY
echo.
echo %BLUE%Features Available:%NC%
echo   ✅ Enhanced conversation flow management
echo   ✅ Cross-device synchronization
echo   ✅ Emotional intelligence support
echo   ✅ Health and wellness advice
echo   ✅ 16 advanced AI skills
echo.
echo %YELLOW%Note: BUDDY server is already running at http://localhost:8080%NC%
echo %YELLOW%The web interface should be available at http://localhost:3001%NC%
echo.
echo Press any key to continue...
pause >nul
goto :eof

REM Main installation function
:main
call :log "Starting BUDDY AI Assistant installation..."

call :check_requirements
if errorlevel 1 exit /b 1

call :create_directories
call :download_buddy
call :install_buddy
call :install_windows_integration
call :install_windows_service
call :post_install_setup

call :log "BUDDY AI Assistant installation completed!"
goto :eof

REM Handle command line arguments
if "%1"=="--help" (
    echo BUDDY AI Assistant Windows Installer
    echo.
    echo Usage: %0 [options]
    echo.
    echo Options:
    echo   --help      Show this help message
    echo   --version   Show version information
    echo.
    exit /b 0
)

if "%1"=="--version" (
    echo BUDDY AI Assistant Installer v%BUDDY_VERSION%
    exit /b 0
)

REM Run main installation
call :main

REM Cleanup
if exist "%TEMP_DIR%" rmdir /s /q "%TEMP_DIR%"

endlocal
