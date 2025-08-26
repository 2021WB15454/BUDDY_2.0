@echo off
echo BUDDY 2.0 Mobile Environment Setup Verification
echo ================================================

echo.
echo Checking Node.js...
node --version
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js from https://nodejs.org/
    goto :error
)

echo.
echo Checking npm...
npm --version
if %errorlevel% neq 0 (
    echo ERROR: npm not found. Please install Node.js which includes npm.
    goto :error
)

echo.
echo Checking Java...
java -version
if %errorlevel% neq 0 (
    echo ERROR: Java not found. Please install JDK 11+ from https://www.oracle.com/java/technologies/downloads/
    goto :error
)

echo.
echo Checking JAVA_HOME...
if "%JAVA_HOME%"=="" (
    echo WARNING: JAVA_HOME not set. Please set JAVA_HOME environment variable.
) else (
    echo JAVA_HOME: %JAVA_HOME%
)

echo.
echo Checking Android SDK...
if "%ANDROID_HOME%"=="" (
    echo WARNING: ANDROID_HOME not set. Please install Android SDK and set ANDROID_HOME.
) else (
    echo ANDROID_HOME: %ANDROID_HOME%
)

echo.
echo Checking adb...
adb version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: adb not found. Please install Android SDK platform-tools.
) else (
    echo adb found in PATH
)

echo.
echo Checking Flutter...
flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Flutter not found. Please install Flutter SDK from https://docs.flutter.dev/get-started/install/windows
) else (
    echo Flutter found in PATH
    flutter --version
)

echo.
echo Checking React Native dependencies...
cd apps\mobile >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: apps\mobile directory not found
    goto :error
)

if not exist node_modules (
    echo Installing React Native dependencies...
    npm install
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install React Native dependencies
        goto :error
    )
)

echo.
echo Checking Flutter dependencies...
cd ..\mobile_flutter >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: apps\mobile_flutter directory not found
    cd ..
    goto :skip_flutter
)

if exist pubspec.yaml (
    echo Installing Flutter dependencies...
    flutter pub get >nul 2>&1
    if %errorlevel% neq 0 (
        echo WARNING: Failed to install Flutter dependencies
    )
)

cd ..

:skip_flutter
echo.
echo Environment Setup Summary:
echo ==========================
echo [✓] Node.js and npm available
if "%JAVA_HOME%"=="" (
    echo [!] JAVA_HOME needs to be set
) else (
    echo [✓] Java environment configured
)

if "%ANDROID_HOME%"=="" (
    echo [!] Android SDK needs to be installed and configured
) else (
    echo [✓] Android SDK configured
)

adb version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Android platform-tools need to be installed
) else (
    echo [✓] Android platform-tools available
)

flutter --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Flutter SDK needs to be installed (optional)
) else (
    echo [✓] Flutter SDK available
)

echo.
echo Next Steps:
echo -----------
echo 1. Install missing tools marked with [!]
echo 2. Connect Android device or start emulator
echo 3. Run: npm run android (in apps/mobile directory)
echo 4. Or run: flutter run (in apps/mobile_flutter directory)
echo.
echo For detailed setup instructions, see MOBILE_SETUP_GUIDE.md
echo.
pause
goto :end

:error
echo.
echo Setup verification failed. Please install missing tools and try again.
echo See MOBILE_SETUP_GUIDE.md for detailed installation instructions.
pause

:end
