# Docker Desktop Installation Guide for Windows

## 🐳 **Install Docker Desktop**

### Method 1: Direct Download (Recommended)

1. **Go to Docker's official website:**
   - Visit: https://www.docker.com/products/docker-desktop/

2. **Download Docker Desktop for Windows:**
   - Click "Download for Windows"
   - This will download `Docker Desktop Installer.exe`

3. **Run the installer:**
   - Double-click the downloaded file
   - Follow the installation wizard
   - Accept the license agreement
   - Choose installation location (default is fine)

4. **System Requirements Check:**
   - Windows 10 64-bit: Pro, Enterprise, or Education (Build 19041 or higher)
   - Windows 11 64-bit
   - WSL 2 feature enabled
   - Virtualization enabled in BIOS

### Method 2: Using Winget (Windows Package Manager)

```powershell
# Install using Windows Package Manager
winget install Docker.DockerDesktop
```

### Method 3: Using Chocolatey

```powershell
# If you have Chocolatey installed
choco install docker-desktop
```

## ⚙️ **Post-Installation Setup**

### 1. Start Docker Desktop
- Look for Docker Desktop in your Start menu
- Launch the application
- It may take a few minutes to start the first time

### 2. Enable WSL 2 (Required)
If WSL 2 isn't enabled, Docker will prompt you to install it:

```powershell
# Run as Administrator
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart your computer, then set WSL 2 as default
wsl --set-default-version 2
```

### 3. Verify Installation

```powershell
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Test Docker is running
docker run hello-world
```

Expected output:
```
Docker version 24.0.6, build ed223bc
Docker Compose version v2.21.0
Hello from Docker!
```

## 🚀 **Deploy BUDDY After Installation**

Once Docker Desktop is installed and running:

```cmd
cd c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\universal_deployment
deploy.bat deploy
```

## 🔧 **Docker Desktop Settings**

### Recommended Settings:
1. **Resources → Advanced:**
   - Memory: 8 GB (or at least 4 GB)
   - CPUs: 4 cores (or at least 2)
   - Disk space: 64 GB

2. **Features in Development:**
   - Enable "Use Docker Compose V2"

3. **General:**
   - ✅ Start Docker Desktop when you log in
   - ✅ Use WSL 2 based engine

## 🐛 **Troubleshooting**

### Issue: "Docker Desktop failed to start"
**Solution:**
1. Restart Windows
2. Check if Hyper-V is enabled
3. Ensure WSL 2 is properly installed

### Issue: "WSL 2 installation is incomplete"
**Solution:**
```powershell
# Download and install WSL 2 Linux kernel update
# Visit: https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
```

### Issue: "Virtualization not enabled"
**Solution:**
1. Restart computer
2. Enter BIOS/UEFI settings (usually F2, F12, or Delete during boot)
3. Enable "Intel VT-x" or "AMD-V" virtualization
4. Save and exit BIOS

### Issue: Port conflicts
**Solution:**
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill process if needed (replace PID with actual process ID)
taskkill /PID <PID> /F
```

## ✅ **Verification Steps**

After installation, verify everything works:

```powershell
# 1. Check Docker Desktop is running
docker info

# 2. Pull a test image
docker pull hello-world

# 3. Run a test container
docker run hello-world

# 4. Check Docker Compose
docker-compose version

# 5. Test BUDDY deployment
cd c:\Users\shrim\Documents\WASE_PROJECT\BUDDY_2.0\universal_deployment
deploy.bat deploy
```

## 🎯 **Next Steps**

1. ✅ Install Docker Desktop
2. ✅ Start Docker Desktop application
3. ✅ Verify installation with `docker --version`
4. ✅ Deploy BUDDY: `deploy.bat deploy`
5. ✅ Access BUDDY at http://localhost:8000/docs

---

**Once Docker Desktop is installed, your universal BUDDY system will be ready to deploy in one command!** 🚀
