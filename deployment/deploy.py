#!/usr/bin/env python3
"""
BUDDY Cross-Platform Deployment Manager
Manages deployment across all supported platforms
"""

import os
import sys
import json
import yaml
import shutil
import subprocess
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DeploymentTarget:
    """Represents a deployment target platform"""
    name: str
    platform: str
    architecture: str
    package_format: str
    distribution_channel: str
    build_command: str
    requirements: List[str]
    metadata: Dict[str, str]

class PlatformDetector:
    """Detects current platform and architecture"""
    
    @staticmethod
    def get_platform() -> str:
        """Get the current platform"""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        else:
            return system
    
    @staticmethod
    def get_architecture() -> str:
        """Get the current architecture"""
        machine = platform.machine().lower()
        if machine in ["x86_64", "amd64"]:
            return "x64"
        elif machine in ["aarch64", "arm64"]:
            return "arm64"
        elif machine.startswith("arm"):
            return "arm"
        else:
            return machine

class DeploymentManager:
    """Manages cross-platform deployment of BUDDY"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "deployment/deployment-config.yml"
        self.config = self._load_config()
        self.targets = self._initialize_targets()
        self.current_platform = PlatformDetector.get_platform()
        self.current_arch = PlatformDetector.get_architecture()
    
    def _load_config(self) -> Dict:
        """Load deployment configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Deployment config not found: {self.config_path}")
            return {}
    
    def _initialize_targets(self) -> List[DeploymentTarget]:
        """Initialize deployment targets from config"""
        targets = []
        
        if not self.config:
            return targets
        
        # Mobile platforms
        for mobile in self.config.get('deployment', {}).get('mobile', []):
            targets.append(DeploymentTarget(
                name=mobile['platform'],
                platform=mobile['platform'].lower(),
                architecture="universal" if mobile['platform'] == 'iOS' else "multi",
                package_format=mobile.get('package_format', 'app'),
                distribution_channel=mobile.get('distribution_channel', 'store'),
                build_command=mobile.get('build_command', ''),
                requirements=mobile.get('requirements', []),
                metadata=mobile.get('metadata', {})
            ))
        
        # Desktop platforms
        for desktop in self.config.get('deployment', {}).get('desktop', []):
            for arch in desktop.get('architectures', ['x64']):
                targets.append(DeploymentTarget(
                    name=f"{desktop['platform']}-{arch}",
                    platform=desktop['platform'].lower(),
                    architecture=arch,
                    package_format=desktop.get('package_format', 'installer'),
                    distribution_channel=desktop.get('distribution_channel', 'direct'),
                    build_command=desktop.get('build_command', ''),
                    requirements=desktop.get('requirements', []),
                    metadata=desktop.get('metadata', {})
                ))
        
        # Web platform
        web_config = self.config.get('deployment', {}).get('web', {})
        if web_config:
            targets.append(DeploymentTarget(
                name="web-pwa",
                platform="web",
                architecture="universal",
                package_format="pwa",
                distribution_channel=web_config.get('distribution_channel', 'direct'),
                build_command=web_config.get('build_command', ''),
                requirements=web_config.get('requirements', []),
                metadata=web_config.get('metadata', {})
            ))
        
        return targets
    
    def list_targets(self) -> List[DeploymentTarget]:
        """List all available deployment targets"""
        return self.targets
    
    def get_target(self, name: str) -> Optional[DeploymentTarget]:
        """Get a specific deployment target"""
        for target in self.targets:
            if target.name == name:
                return target
        return None
    
    def get_compatible_targets(self) -> List[DeploymentTarget]:
        """Get targets compatible with current platform"""
        compatible = []
        for target in self.targets:
            if (target.platform == self.current_platform or 
                target.platform == "web" or
                (target.platform == "linux" and self.current_platform in ["linux", "macos"])):
                compatible.append(target)
        return compatible
    
    def prepare_build_environment(self, target: DeploymentTarget) -> bool:
        """Prepare build environment for target platform"""
        logger.info(f"Preparing build environment for {target.name}")
        
        # Check requirements
        for req in target.requirements:
            if not self._check_requirement(req):
                logger.error(f"Missing requirement: {req}")
                return False
        
        # Create build directory
        build_dir = Path("build") / target.name
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy source files
        self._copy_source_files(target, build_dir)
        
        logger.info(f"Build environment prepared at {build_dir}")
        return True
    
    def _check_requirement(self, requirement: str) -> bool:
        """Check if a requirement is met"""
        try:
            # Check if it's a command
            result = subprocess.run(
                ["which", requirement] if self.current_platform != "windows" else ["where", requirement],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _copy_source_files(self, target: DeploymentTarget, build_dir: Path):
        """Copy source files to build directory"""
        source_dirs = [
            "packages/core",
            "apps/desktop/src" if target.platform in ["windows", "macos", "linux"] else None,
            "packages/voice" if "voice" in target.requirements else None
        ]
        
        for source_dir in filter(None, source_dirs):
            if os.path.exists(source_dir):
                dest_dir = build_dir / Path(source_dir).name
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                shutil.copytree(source_dir, dest_dir)
    
    def build_target(self, target: DeploymentTarget) -> bool:
        """Build for specific target platform"""
        logger.info(f"Building for {target.name}")
        
        if not self.prepare_build_environment(target):
            return False
        
        build_dir = Path("build") / target.name
        
        try:
            # Execute build command
            if target.build_command:
                result = subprocess.run(
                    target.build_command,
                    shell=True,
                    cwd=build_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Build failed: {result.stderr}")
                    return False
            
            # Platform-specific build steps
            if target.platform == "windows":
                return self._build_windows(target, build_dir)
            elif target.platform == "macos":
                return self._build_macos(target, build_dir)
            elif target.platform == "linux":
                return self._build_linux(target, build_dir)
            elif target.platform == "ios":
                return self._build_ios(target, build_dir)
            elif target.platform == "android":
                return self._build_android(target, build_dir)
            elif target.platform == "web":
                return self._build_web(target, build_dir)
            
            logger.info(f"Build completed for {target.name}")
            return True
            
        except Exception as e:
            logger.error(f"Build error for {target.name}: {e}")
            return False
    
    def _build_windows(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build Windows package"""
        logger.info("Building Windows package...")
        
        # Create Windows installer using NSIS or similar
        installer_script = build_dir / "installer.nsi"
        if installer_script.exists():
            subprocess.run(["makensis", str(installer_script)], cwd=build_dir)
        
        # Create portable version
        self._create_portable_package(target, build_dir, "zip")
        
        return True
    
    def _build_macos(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build macOS package"""
        logger.info("Building macOS package...")
        
        # Create .app bundle
        app_dir = build_dir / "BUDDY.app"
        contents_dir = app_dir / "Contents"
        macos_dir = contents_dir / "MacOS"
        resources_dir = contents_dir / "Resources"
        
        for dir_path in [app_dir, contents_dir, macos_dir, resources_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create Info.plist
        info_plist = {
            "CFBundleName": "BUDDY",
            "CFBundleDisplayName": "BUDDY AI Assistant",
            "CFBundleIdentifier": "com.buddy.ai",
            "CFBundleVersion": "1.0.0",
            "CFBundleExecutable": "buddy",
            "LSMinimumSystemVersion": "10.15"
        }
        
        with open(contents_dir / "Info.plist", 'w') as f:
            import plistlib
            plistlib.dump(info_plist, f)
        
        # Create DMG
        if shutil.which("hdiutil"):
            subprocess.run([
                "hdiutil", "create", 
                "-srcfolder", str(app_dir),
                "-volname", "BUDDY",
                str(build_dir / "BUDDY.dmg")
            ])
        
        return True
    
    def _build_linux(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build Linux package"""
        logger.info("Building Linux package...")
        
        # Create .deb package
        if target.package_format == "deb":
            self._create_deb_package(target, build_dir)
        
        # Create .rpm package
        elif target.package_format == "rpm":
            self._create_rpm_package(target, build_dir)
        
        # Create AppImage
        elif target.package_format == "appimage":
            self._create_appimage(target, build_dir)
        
        # Create tarball
        self._create_portable_package(target, build_dir, "tar.gz")
        
        return True
    
    def _build_ios(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build iOS package"""
        logger.info("Building iOS package...")
        
        # Build using Xcode
        if shutil.which("xcodebuild"):
            subprocess.run([
                "xcodebuild",
                "-workspace", "ios/BUDDY.xcworkspace",
                "-scheme", "BUDDY",
                "-configuration", "Release",
                "-destination", "generic/platform=iOS",
                "archive"
            ], cwd=build_dir)
        
        return True
    
    def _build_android(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build Android package"""
        logger.info("Building Android package...")
        
        # Build using Gradle
        if (build_dir / "android" / "gradlew").exists():
            subprocess.run([
                "./gradlew", "assembleRelease"
            ], cwd=build_dir / "android")
        
        return True
    
    def _build_web(self, target: DeploymentTarget, build_dir: Path) -> bool:
        """Build web PWA"""
        logger.info("Building web PWA...")
        
        # Build React app for production
        if (build_dir / "package.json").exists():
            subprocess.run(["npm", "run", "build"], cwd=build_dir)
        
        return True
    
    def _create_deb_package(self, target: DeploymentTarget, build_dir: Path):
        """Create Debian package"""
        debian_dir = build_dir / "debian"
        debian_dir.mkdir(exist_ok=True)
        
        # Create control file
        control_content = f"""Package: buddy-ai
Version: 1.0.0
Section: utils
Priority: optional
Architecture: {target.architecture}
Maintainer: BUDDY Team <contact@buddy.ai>
Description: BUDDY AI Assistant
 Advanced AI assistant with conversation management
"""
        with open(debian_dir / "control", 'w') as f:
            f.write(control_content)
        
        # Build package
        subprocess.run(["dpkg-deb", "--build", str(build_dir)], capture_output=True)
    
    def _create_rpm_package(self, target: DeploymentTarget, build_dir: Path):
        """Create RPM package"""
        # Implementation for RPM package creation
        pass
    
    def _create_appimage(self, target: DeploymentTarget, build_dir: Path):
        """Create AppImage"""
        # Implementation for AppImage creation
        pass
    
    def _create_portable_package(self, target: DeploymentTarget, build_dir: Path, format: str):
        """Create portable package (zip/tar.gz)"""
        package_name = f"buddy-{target.name}"
        
        if format == "zip":
            shutil.make_archive(
                str(build_dir.parent / package_name),
                'zip',
                build_dir
            )
        elif format == "tar.gz":
            shutil.make_archive(
                str(build_dir.parent / package_name),
                'gztar',
                build_dir
            )
    
    def deploy_target(self, target: DeploymentTarget) -> bool:
        """Deploy built package to distribution channel"""
        logger.info(f"Deploying {target.name} to {target.distribution_channel}")
        
        if target.distribution_channel == "appstore":
            return self._deploy_to_appstore(target)
        elif target.distribution_channel == "playstore":
            return self._deploy_to_playstore(target)
        elif target.distribution_channel == "microsoft_store":
            return self._deploy_to_microsoft_store(target)
        elif target.distribution_channel == "package_manager":
            return self._deploy_to_package_manager(target)
        elif target.distribution_channel == "direct":
            return self._deploy_direct(target)
        
        return False
    
    def _deploy_to_appstore(self, target: DeploymentTarget) -> bool:
        """Deploy to Apple App Store"""
        # Implementation for App Store deployment
        logger.info("App Store deployment requires manual submission")
        return True
    
    def _deploy_to_playstore(self, target: DeploymentTarget) -> bool:
        """Deploy to Google Play Store"""
        # Implementation for Play Store deployment
        logger.info("Play Store deployment requires manual submission")
        return True
    
    def _deploy_to_microsoft_store(self, target: DeploymentTarget) -> bool:
        """Deploy to Microsoft Store"""
        # Implementation for Microsoft Store deployment
        logger.info("Microsoft Store deployment requires manual submission")
        return True
    
    def _deploy_to_package_manager(self, target: DeploymentTarget) -> bool:
        """Deploy to package manager (apt, yum, brew, etc.)"""
        # Implementation for package manager deployment
        logger.info("Package manager deployment configured")
        return True
    
    def _deploy_direct(self, target: DeploymentTarget) -> bool:
        """Deploy for direct download"""
        # Copy to distribution directory
        dist_dir = Path("dist") / target.name
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        build_dir = Path("build") / target.name
        if build_dir.exists():
            for item in build_dir.iterdir():
                if item.is_file() and item.suffix in ['.zip', '.tar.gz', '.dmg', '.exe', '.deb', '.rpm']:
                    shutil.copy2(item, dist_dir)
        
        logger.info(f"Direct deployment completed to {dist_dir}")
        return True
    
    def build_all_compatible(self) -> Dict[str, bool]:
        """Build all compatible targets"""
        results = {}
        compatible_targets = self.get_compatible_targets()
        
        for target in compatible_targets:
            logger.info(f"Building {target.name}...")
            results[target.name] = self.build_target(target)
        
        return results
    
    def deploy_all_built(self) -> Dict[str, bool]:
        """Deploy all built targets"""
        results = {}
        
        for target in self.targets:
            build_dir = Path("build") / target.name
            if build_dir.exists():
                logger.info(f"Deploying {target.name}...")
                results[target.name] = self.deploy_target(target)
        
        return results

def main():
    """Main deployment script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BUDDY Cross-Platform Deployment Manager")
    parser.add_argument("--list-targets", action="store_true", help="List all deployment targets")
    parser.add_argument("--build", type=str, help="Build specific target")
    parser.add_argument("--build-all", action="store_true", help="Build all compatible targets")
    parser.add_argument("--deploy", type=str, help="Deploy specific target")
    parser.add_argument("--deploy-all", action="store_true", help="Deploy all built targets")
    parser.add_argument("--config", type=str, help="Path to deployment config file")
    
    args = parser.parse_args()
    
    # Initialize deployment manager
    deployment_manager = DeploymentManager(args.config)
    
    if args.list_targets:
        targets = deployment_manager.list_targets()
        print("\nAvailable deployment targets:")
        for target in targets:
            print(f"  {target.name} ({target.platform}-{target.architecture})")
        
        compatible = deployment_manager.get_compatible_targets()
        print(f"\nCompatible with current platform ({deployment_manager.current_platform}-{deployment_manager.current_arch}):")
        for target in compatible:
            print(f"  {target.name}")
    
    elif args.build:
        target = deployment_manager.get_target(args.build)
        if target:
            success = deployment_manager.build_target(target)
            print(f"Build {'succeeded' if success else 'failed'} for {args.build}")
        else:
            print(f"Target '{args.build}' not found")
    
    elif args.build_all:
        results = deployment_manager.build_all_compatible()
        print("\nBuild results:")
        for target_name, success in results.items():
            print(f"  {target_name}: {'✓' if success else '✗'}")
    
    elif args.deploy:
        target = deployment_manager.get_target(args.deploy)
        if target:
            success = deployment_manager.deploy_target(target)
            print(f"Deployment {'succeeded' if success else 'failed'} for {args.deploy}")
        else:
            print(f"Target '{args.deploy}' not found")
    
    elif args.deploy_all:
        results = deployment_manager.deploy_all_built()
        print("\nDeployment results:")
        for target_name, success in results.items():
            print(f"  {target_name}: {'✓' if success else '✗'}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
