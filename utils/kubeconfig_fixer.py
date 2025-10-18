#!/usr/bin/env python3
"""
Kubeconfig Fixer Utility

This utility automatically detects and fixes the gke-gcloud-auth-plugin path
in kubeconfig files across different platforms (macOS, Linux, Windows WSL).
"""

import os
import sys
import json
import yaml
import subprocess
import platform


class KubeconfigFixer:
    """Utility to fix gke-gcloud-auth-plugin paths in kubeconfig files"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.architecture = platform.machine().lower()
    
    def find_gke_auth_plugin(self) -> str | None:
        """
        Find the gke-gcloud-auth-plugin executable across different platforms
        Returns the full path to the plugin or None if not found
        """
        # Common paths to check based on platform
        potential_paths = self._get_potential_paths()
        
        for path in potential_paths:
            if self._is_valid_plugin_path(path):
                return path
        
        # Try to find using which/where command
        return self._find_using_system_command()
    
    def _get_potential_paths(self) -> list[str]:
        """Get potential paths based on platform and common installation methods"""
        paths = []
        
        if self.platform == "darwin":  # macOS
            # Homebrew paths
            paths.extend([
                "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/opt/homebrew/share/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/opt/homebrew/bin/gke-gcloud-auth-plugin",
                "/usr/local/bin/gke-gcloud-auth-plugin",
                # Intel Mac paths
                "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
            ])
            
            # Check for different Homebrew architectures
            if self.architecture == "arm64":  # Apple Silicon
                paths.extend([
                    "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                ])
            else:  # Intel
                paths.extend([
                    "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                ])
        
        elif self.platform == "linux":
            # Linux paths (including WSL)
            paths.extend([
                "/usr/bin/gke-gcloud-auth-plugin",
                "/usr/local/bin/gke-gcloud-auth-plugin",
                "/snap/bin/gke-gcloud-auth-plugin",
                "/opt/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/usr/lib/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                # WSL specific paths
                "/mnt/c/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
                "/mnt/c/Program Files/Google/Cloud SDK/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
            ])
        
        elif self.platform == "windows":
            # Windows paths
            paths.extend([
                "C:\\Program Files (x86)\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gke-gcloud-auth-plugin.exe",
                "C:\\Program Files\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gke-gcloud-auth-plugin.exe",
                "C:\\Users\\{username}\\AppData\\Local\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gke-gcloud-auth-plugin.exe",
            ])
        
        # Add PATH-based search
        paths.extend([
            "gke-gcloud-auth-plugin",  # In PATH
            "./gke-gcloud-auth-plugin",  # Current directory
        ])
        
        return paths
    
    def _is_valid_plugin_path(self, path: str) -> bool:
        """Check if the path is a valid gke-gcloud-auth-plugin executable"""
        try:
            # Check if file exists and is executable
            if not os.path.exists(path):
                return False
            
            # Check if it's executable
            if not os.access(path, os.X_OK):
                return False
            
            # Try to run the plugin with --help to verify it's the right tool
            try:
                result = subprocess.run(
                    [path, "--help"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                # If it runs and shows help (exit code 0 or 2), it's likely the right plugin
                # Check for either the plugin name or "Usage of" in stdout or stderr
                combined_output = result.stdout + result.stderr
                return result.returncode in [0, 2] and ("gke-gcloud-auth-plugin" in combined_output or "Usage of" in combined_output)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                # If it fails, it might still be the right plugin but with different args
                # Check if the file name matches
                return "gke-gcloud-auth-plugin" in os.path.basename(path)
                
        except Exception:
            return False
    
    def _find_using_system_command(self) -> str | None:
        """Try to find the plugin using system commands (which/where)"""
        try:
            if self.platform == "windows":
                # Use where command on Windows
                result = subprocess.run(
                    ["where", "gke-gcloud-auth-plugin"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
            else:
                # Use which command on Unix-like systems
                result = subprocess.run(
                    ["which", "gke-gcloud-auth-plugin"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
            
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if self._is_valid_plugin_path(path):
                    return path
                    
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return None
    
    def fix_kubeconfig(self, kubeconfig_path: str) -> bool:
        """
        Fix the gke-gcloud-auth-plugin path in a kubeconfig file
        
        Args:
            kubeconfig_path: Path to the kubeconfig file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Find the correct plugin path
            plugin_path = self.find_gke_auth_plugin()
            
            if not plugin_path:
                print("❌ Could not find gke-gcloud-auth-plugin")
                return False
            
            print(f"✅ Found gke-gcloud-auth-plugin at: {plugin_path}")
            
            # Read the kubeconfig file (try YAML first, then JSON)
            with open(kubeconfig_path, 'r') as f:
                content = f.read()
            
            try:
                # Try YAML first
                kubeconfig = yaml.safe_load(content)
            except yaml.YAMLError:
                try:
                    # Fall back to JSON
                    kubeconfig = json.loads(content)
                except json.JSONDecodeError:
                    print("❌ Could not parse kubeconfig file as YAML or JSON")
                    return False
            
            # Check if we need to fix the command
            if 'users' in kubeconfig and len(kubeconfig['users']) > 0:
                user = kubeconfig['users'][0]
                if 'user' in user and 'exec' in user['user']:
                    exec_config = user['user']['exec']
                    if exec_config.get('command') == 'gke-gcloud-auth-plugin':
                        # Update the command with the full path
                        exec_config['command'] = plugin_path
                        print(f"✅ Updated kubeconfig with plugin path: {plugin_path}")
                        
                        # Write the updated kubeconfig back (try YAML first, then JSON)
                        with open(kubeconfig_path, 'w') as f:
                            try:
                                # Try to write as YAML
                                yaml.dump(kubeconfig, f, default_flow_style=False, sort_keys=False)
                            except Exception:
                                # Fall back to JSON
                                json.dump(kubeconfig, f, indent=2)
                        
                        return True
                    else:
                        print(f"ℹ️  Kubeconfig already has custom command: {exec_config.get('command')}")
                        return True
                else:
                    print("ℹ️  No exec configuration found in kubeconfig")
                    return True
            else:
                print("ℹ️  No users configuration found in kubeconfig")
                return True
                
        except Exception as e:
            print(f"❌ Error fixing kubeconfig: {str(e)}")
            return False
    
    def test_plugin(self, plugin_path: str) -> bool:
        """Test if the plugin works correctly"""
        try:
            result = subprocess.run(
                [plugin_path, "--help"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False


def main():
    """Main function for command line usage"""
    if len(sys.argv) != 2:
        print("Usage: python kubeconfig_fixer.py <kubeconfig_path>")
        sys.exit(1)
    
    kubeconfig_path = sys.argv[1]
    
    if not os.path.exists(kubeconfig_path):
        print(f"❌ Kubeconfig file not found: {kubeconfig_path}")
        sys.exit(1)
    
    fixer = KubeconfigFixer()
    
    print(f"🔧 Fixing kubeconfig: {kubeconfig_path}")
    print(f"🖥️  Platform: {fixer.platform} ({fixer.architecture})")
    
    if fixer.fix_kubeconfig(kubeconfig_path):
        print("✅ Kubeconfig fixed successfully")
        sys.exit(0)
    else:
        print("❌ Failed to fix kubeconfig")
        sys.exit(1)


if __name__ == "__main__":
    main()
