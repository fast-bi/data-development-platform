#!/usr/bin/env python3
"""
Helm Dependencies Analyzer v2 - Systematic Approach

This script follows a systematic approach to analyze Helm chart dependencies:
1. Load the collected Helm charts inventory
2. Update all Helm repositories
3. Download all charts as templates
4. Parse Chart.yaml files to find dependencies
5. Analyze dependencies for Bitnami usage

This is Phase 2 of the Helm charts analysis to prepare for Bitnami's closure in 2025-09.
"""

import os
import json
import yaml
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
import logging
from urllib.parse import urlparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HelmDependencyAnalyzerV2:
    def __init__(self, inventory_file: str = "helm_charts_inventory.json", keep_downloads: bool = False):
        self.inventory_file = Path(inventory_file)
        self.keep_downloads = keep_downloads
        
        if keep_downloads:
            # Use a persistent directory in current working directory
            self.temp_dir = Path("helm_charts_downloads")
            self.temp_dir.mkdir(exist_ok=True)
            logger.info(f"📁 Downloads will be stored in: {self.temp_dir.absolute()}")
        else:
            # Use temporary directory that gets cleaned up
            self.temp_dir = Path(tempfile.mkdtemp(prefix="helm_analysis_v2_"))
            logger.info(f"📁 Temporary downloads stored in: {self.temp_dir}")
        self.dependencies_data = {
            "charts_analyzed": {},
            "bitnami_dependencies": {
                "direct": [],
                "transitive": [],
                "all_affected_charts": set()
            },
            "summary": {
                "total_charts": 0,
                "total_dependencies": 0,
                "bitnami_dependencies_count": 0
            }
        }
        
    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete analysis following the systematic approach"""
        logger.info("Starting systematic Helm dependencies analysis...")
        
        try:
            # Step 1: Load the collected Helm charts inventory
            inventory = self._load_inventory()
            logger.info("✅ Step 1: Loaded Helm charts inventory")
            
            # Step 2: Update all Helm repositories
            self._update_all_repositories(inventory)
            logger.info("✅ Step 2: Updated all Helm repositories")
            
            # Step 3: Download all charts as templates
            unique_charts = self._collect_unique_charts(inventory)
            logger.info(f"✅ Step 3: Found {len(unique_charts)} unique charts to analyze")
            
            # Step 4: Download and analyze each chart
            for chart_info in unique_charts:
                self._analyze_single_chart(chart_info)
            
            # Step 5: Generate summary
            self._generate_summary()
            logger.info("✅ Step 5: Generated analysis summary")
            
            return self.dependencies_data
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            raise
    
    def _load_inventory(self) -> Dict[str, Any]:
        """Step 1: Load the Helm charts inventory"""
        try:
            with open(self.inventory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading inventory file: {str(e)}")
            raise
    
    def _update_all_repositories(self, inventory: Dict[str, Any]):
        """Step 2: Update all Helm repositories"""
        repositories = set()
        
        # Collect all unique repositories
        for service_category in ["data_services", "infra_services"]:
            for service_name, service_data in inventory.get(service_category, {}).items():
                for chart in service_data.get("charts", []):
                    repositories.add(chart["chart_repo"])
                for chart in service_data.get("extra_charts", []):
                    repositories.add(chart["chart_repo"])
        
        logger.info(f"Found {len(repositories)} unique repositories to update")
        
        # Update each repository
        for repo_url in repositories:
            try:
                repo_name = self._extract_repo_name(repo_url)
                self._add_and_update_repo(repo_name, repo_url)
            except Exception as e:
                logger.warning(f"Failed to update repository {repo_url}: {str(e)}")
        
        # Update all repositories
        try:
            subprocess.run(["helm", "repo", "update"], check=True, capture_output=True)
            logger.info("Updated all Helm repositories")
        except Exception as e:
            logger.warning(f"Failed to update all repositories: {str(e)}")
    
    def _collect_unique_charts(self, inventory: Dict[str, Any]) -> List[Dict[str, str]]:
        """Collect all unique charts from the inventory"""
        charts = set()
        unique_charts = []
        
        for service_category in ["data_services", "infra_services"]:
            for service_name, service_data in inventory.get(service_category, {}).items():
                for chart in service_data.get("charts", []):
                    chart_key = f"{chart['chart_repo']}:{chart['chart_name']}"
                    if chart_key not in charts:
                        charts.add(chart_key)
                        unique_charts.append({
                            "service": f"{service_category}/{service_name}",
                            "chart_repo": chart["chart_repo"],
                            "chart_name": chart["chart_name"],
                            "chart_repo_name": chart["chart_repo_name"]
                        })
                
                for chart in service_data.get("extra_charts", []):
                    chart_key = f"{chart['chart_repo']}:{chart['chart_name']}"
                    if chart_key not in charts:
                        charts.add(chart_key)
                        unique_charts.append({
                            "service": f"{service_category}/{service_name}",
                            "chart_repo": chart["chart_repo"],
                            "chart_name": chart["chart_name"],
                            "chart_repo_name": chart["chart_repo_name"],
                            "chart_type": chart.get("chart_type", "extra")
                        })
        
        return unique_charts
    
    def _analyze_single_chart(self, chart_info: Dict[str, str]):
        """Step 4: Download and analyze a single chart"""
        chart_name = chart_info["chart_name"]
        chart_repo = chart_info["chart_repo"]
        service = chart_info["service"]
        
        logger.info(f"Analyzing chart: {chart_name} from {service}")
        
        # Create temporary directory for this chart
        chart_temp_dir = self.temp_dir / f"chart_{chart_name.replace('/', '_').replace(':', '_')}"
        chart_temp_dir.mkdir(exist_ok=True)
        logger.info(f"📁 Chart download directory: {chart_temp_dir}")
        
        try:
            # Download the chart
            chart_path = self._download_chart(chart_name, chart_repo, chart_temp_dir)
            if not chart_path:
                logger.warning(f"Could not download chart {chart_name}")
                return
            
            # Parse Chart.yaml for dependencies
            dependencies = self._parse_chart_yaml(chart_path)
            
            # Find Bitnami dependencies
            bitnami_deps = self._find_bitnami_dependencies(dependencies)
            
            # Store results
            chart_key = f"{service}:{chart_name}"
            self.dependencies_data["charts_analyzed"][chart_key] = {
                "chart_info": chart_info,
                "dependencies": dependencies,
                "bitnami_dependencies": bitnami_deps,
                "chart_path": str(chart_path)
            }
            
            # Update Bitnami tracking
            if bitnami_deps:
                self.dependencies_data["bitnami_dependencies"]["direct"].append({
                    "chart": chart_key,
                    "dependencies": bitnami_deps
                })
                self.dependencies_data["bitnami_dependencies"]["all_affected_charts"].add(chart_key)
            
            logger.info(f"Found {len(dependencies)} dependencies, {len(bitnami_deps)} Bitnami dependencies")
            
        except Exception as e:
            logger.error(f"Error analyzing chart {chart_name}: {str(e)}")
        finally:
            # Clean up temporary directory only if not keeping downloads
            if not self.keep_downloads and chart_temp_dir.exists():
                shutil.rmtree(chart_temp_dir)
    
    def _download_chart(self, chart_name: str, chart_repo: str, temp_dir: Path) -> Optional[Path]:
        """Download a Helm chart to temporary directory"""
        try:
            if chart_repo.startswith("https://"):
                # Standard Helm repository
                cmd = [
                    "helm", "pull", chart_name,
                    "--untar",
                    "--untardir", str(temp_dir)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
                if result.returncode == 0:
                    # Find the extracted chart directory - look recursively
                    chart_dir = self._find_chart_directory(temp_dir)
                    if chart_dir:
                        return chart_dir
                else:
                    logger.error(f"Failed to download chart {chart_name}: {result.stderr}")
                    return None
            
            elif chart_repo.startswith("oci://"):
                # OCI registry chart
                oci_url = f"{chart_repo}/{chart_name}"
                cmd = [
                    "helm", "pull", oci_url,
                    "--untar",
                    "--untardir", str(temp_dir)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
                if result.returncode == 0:
                    chart_dir = self._find_chart_directory(temp_dir)
                    if chart_dir:
                        return chart_dir
                else:
                    logger.error(f"Failed to download OCI chart {oci_url}: {result.stderr}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading chart {chart_name}: {str(e)}")
            return None
    
    def _find_chart_directory(self, search_dir: Path) -> Optional[Path]:
        """Recursively find a directory containing Chart.yaml"""
        for item in search_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if this directory contains Chart.yaml
                if (item / "Chart.yaml").exists():
                    return item
                # Recursively search subdirectories
                sub_result = self._find_chart_directory(item)
                if sub_result:
                    return sub_result
        return None
    
    def _parse_chart_yaml(self, chart_path: Path) -> List[Dict[str, Any]]:
        """Parse Chart.yaml file to extract dependencies"""
        chart_yaml_path = chart_path / "Chart.yaml"
        
        if not chart_yaml_path.exists():
            logger.warning(f"Chart.yaml not found in {chart_path}")
            return []
        
        try:
            with open(chart_yaml_path, 'r', encoding='utf-8') as f:
                chart_data = yaml.safe_load(f)
            
            dependencies = chart_data.get("dependencies", [])
            logger.debug(f"Found {len(dependencies)} dependencies in {chart_path.name}")
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Error parsing Chart.yaml in {chart_path}: {str(e)}")
            return []
    
    def _find_bitnami_dependencies(self, dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find Bitnami dependencies in the dependencies list"""
        bitnami_deps = []
        
        for dep in dependencies:
            dep_name = dep.get("name", "")
            dep_repository = dep.get("repository", "")
            
            if self._is_bitnami_dependency(dep_name, dep_repository):
                bitnami_deps.append({
                    "name": dep_name,
                    "version": dep.get("version", "unknown"),
                    "repository": dep_repository,
                    "alias": dep.get("alias", "")
                })
        
        return bitnami_deps
    
    def _is_bitnami_dependency(self, name: str, repository: str) -> bool:
        """Check if a dependency is from Bitnami"""
        # Check repository URL
        if "bitnami" in repository.lower():
            return True
        
        # Check common Bitnami chart names
        bitnami_charts = [
            "redis", "postgresql", "mysql", "mongodb", "elasticsearch", "kibana",
            "keycloak", "nginx", "apache", "wordpress", "joomla", "drupal",
            "external-dns", "cert-manager", "sealed-secrets", "kafka", "zookeeper",
            "rabbitmq", "memcached", "cassandra", "influxdb", "grafana", "prometheus",
            "mariadb", "postgresql-ha", "redis-ha", "mongodb-sharded", "elasticsearch-curator"
        ]
        
        if name.lower() in bitnami_charts:
            return True
        
        return False
    
    def _add_and_update_repo(self, repo_name: str, repo_url: str):
        """Add and update a Helm repository"""
        try:
            # Check if repo already exists
            cmd = ["helm", "repo", "list", "--output", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                repos = json.loads(result.stdout)
                existing_repos = [repo.get("name", "") for repo in repos]
                
                if repo_name not in existing_repos:
                    cmd = ["helm", "repo", "add", repo_name, repo_url]
                    subprocess.run(cmd, check=True, capture_output=True)
                    logger.debug(f"Added Helm repository: {repo_name}")
                
                # Update the repository
                cmd = ["helm", "repo", "update", repo_name]
                subprocess.run(cmd, check=True, capture_output=True)
                
        except Exception as e:
            logger.warning(f"Error adding/updating Helm repository {repo_name}: {str(e)}")
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        parsed = urlparse(repo_url)
        return parsed.netloc.replace('.', '_').replace('-', '_')
    
    def _generate_summary(self):
        """Generate summary statistics"""
        total_charts = len(self.dependencies_data["charts_analyzed"])
        total_deps = sum(len(chart_data["dependencies"]) for chart_data in self.dependencies_data["charts_analyzed"].values())
        
        direct_bitnami_count = len(self.dependencies_data["bitnami_dependencies"]["direct"])
        transitive_bitnami_count = len(self.dependencies_data["bitnami_dependencies"]["transitive"])
        total_bitnami_count = direct_bitnami_count + transitive_bitnami_count
        
        self.dependencies_data["summary"] = {
            "total_charts": total_charts,
            "total_dependencies": total_deps,
            "bitnami_dependencies_count": total_bitnami_count,
            "direct_bitnami_dependencies": direct_bitnami_count,
            "transitive_bitnami_dependencies": transitive_bitnami_count,
            "affected_charts_count": len(self.dependencies_data["bitnami_dependencies"]["all_affected_charts"])
        }
    
    def save_to_json(self, output_file: str = "helm_dependencies_analysis.json"):
        """Save the dependencies analysis to a JSON file"""
        try:
            # Convert sets to lists for JSON serialization
            output_data = self.dependencies_data.copy()
            output_data["bitnami_dependencies"]["all_affected_charts"] = list(
                output_data["bitnami_dependencies"]["all_affected_charts"]
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Helm dependencies analysis saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")
            raise
    
    def save_to_markdown(self, output_file: str = "helm_dependencies_analysis_report.md"):
        """Save the dependencies analysis to a Markdown report"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(self._generate_markdown_report())
            logger.info(f"Helm dependencies analysis report saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving to Markdown: {str(e)}")
            raise
    
    def _generate_markdown_report(self) -> str:
        """Generate a comprehensive Markdown report"""
        summary = self.dependencies_data["summary"]
        
        report = f"""# Helm Dependencies Analysis Report
## Fast.bi Data Platform - Bitnami Migration Assessment

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Analysis Date:** {datetime.now().strftime("%Y-%m-%d")}  
**Bitnami Closure Date:** 2025-09-01  

---

## 📊 Executive Summary

This report analyzes Helm chart dependencies in the fast.bi data platform to identify services affected by Bitnami's planned closure in September 2025.

### Key Findings:
- **{summary['total_charts']} charts analyzed**
- **{summary['total_dependencies']} total dependencies found**
- **{summary['bitnami_dependencies_count']} Bitnami dependencies identified**
- **{summary['affected_charts_count']} charts affected by Bitnami closure**

### Risk Assessment:
⚠️ **HIGH RISK** - Multiple critical services depend on Bitnami charts that will become unavailable in September 2025.

---

## 🎯 Affected Services

### Direct Bitnami Dependencies

"""
        
        # Add direct Bitnami dependencies
        if self.dependencies_data["bitnami_dependencies"]["direct"]:
            for dep in self.dependencies_data["bitnami_dependencies"]["direct"]:
                chart_info = dep["chart"]
                report += f"#### {chart_info}\n\n"
                for bitnami_dep in dep["dependencies"]:
                    report += f"- **{bitnami_dep['name']}@{bitnami_dep['version']}**\n"
                    report += f"  - Repository: `{bitnami_dep['repository']}`\n"
                    if bitnami_dep.get('alias'):
                        report += f"  - Alias: `{bitnami_dep['alias']}`\n"
                    report += "\n"
        else:
            report += "No direct Bitnami dependencies found.\n\n"
        
        report += """
---

## 📋 Detailed Chart Analysis

### Charts with Dependencies

"""
        
        # Add detailed chart analysis for ALL charts (including those without dependencies)
        for chart_key, chart_data in self.dependencies_data["charts_analyzed"].items():
            chart_info = chart_data["chart_info"]
            dependencies = chart_data["dependencies"]
            bitnami_deps = chart_data["bitnami_dependencies"]
            
            report += f"#### {chart_key}\n\n"
            report += f"- **Chart:** `{chart_info['chart_name']}`\n"
            report += f"- **Repository:** `{chart_info['chart_repo']}`\n"
            report += f"- **Service:** `{chart_info['service']}`\n"
            report += f"- **Total Dependencies:** {len(dependencies)}\n"
            report += f"- **Bitnami Dependencies:** {len(bitnami_deps)}\n"
            
            if len(bitnami_deps) == 0:
                report += f"- **Status:** ✅ **SAFE** - No Bitnami dependencies\n"
            else:
                report += f"- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies\n"
            report += "\n"
            
            if dependencies:
                report += "**Dependencies:**\n"
                for dep in dependencies:
                    report += f"- `{dep.get('name', 'Unknown')}@{dep.get('version', 'Unknown')}`\n"
                    if dep.get('repository'):
                        report += f"  - Repository: `{dep.get('repository')}`\n"
                    if dep.get('alias'):
                        report += f"  - Alias: `{dep.get('alias')}`\n"
                    report += "\n"
            else:
                report += "**Dependencies:** None\n\n"
            
            if bitnami_deps:
                report += "**⚠️ Bitnami Dependencies (Require Migration):**\n"
                for dep in bitnami_deps:
                    report += f"- `{dep['name']}@{dep['version']}`\n"
                    report += f"  - Repository: `{dep['repository']}`\n"
                    if dep.get('alias'):
                        report += f"  - Alias: `{dep.get('alias')}`\n"
                    report += "\n"
            
            report += "---\n\n"
        
        report += """
---

## 🚨 Migration Priority Matrix

### High Priority (Critical Services)
Services that directly depend on Bitnami charts and are essential for platform operation:

"""
        
        # Identify high priority services
        high_priority = []
        for dep in self.dependencies_data["bitnami_dependencies"]["direct"]:
            chart_info = dep["chart"]
            if "postgresql" in chart_info.lower() or "redis" in chart_info.lower():
                high_priority.append(chart_info)
        
        if high_priority:
            for service in high_priority:
                report += f"- **{service}** - Database/Storage dependency\n"
        else:
            report += "- No high priority services identified\n"
        
        report += """
### Medium Priority (Service Dependencies)
Services that depend on other charts that use Bitnami:

"""
        
        # Identify medium priority services
        medium_priority = []
        for dep in self.dependencies_data["bitnami_dependencies"]["direct"]:
            chart_info = dep["chart"]
            if "postgresql" not in chart_info.lower() and "redis" not in chart_info.lower():
                medium_priority.append(chart_info)
        
        if medium_priority:
            for service in medium_priority:
                report += f"- **{service}** - Application dependency\n"
        else:
            report += "- No medium priority services identified\n"
        
        report += """
---

## 📋 Complete Chart Inventory

### All Charts with Status

"""
        
        # Add complete inventory with status
        safe_charts = []
        affected_charts = []
        
        for chart_key, chart_data in self.dependencies_data["charts_analyzed"].items():
            chart_info = chart_data["chart_info"]
            bitnami_deps = chart_data["bitnami_dependencies"]
            
            chart_entry = f"- **{chart_info['chart_name']}** (`{chart_info['service']}`)\n"
            
            if len(bitnami_deps) == 0:
                safe_charts.append(chart_entry)
            else:
                affected_charts.append(chart_entry)
        
        if safe_charts:
            report += "#### ✅ Safe Charts (No Bitnami Dependencies)\n\n"
            for chart in sorted(safe_charts):
                report += chart
            report += "\n"
        
        if affected_charts:
            report += "#### ⚠️ Affected Charts (Has Bitnami Dependencies)\n\n"
            for chart in sorted(affected_charts):
                report += chart
            report += "\n"
        
        report += f"""
**Summary:**
- **Total Charts:** {len(self.dependencies_data["charts_analyzed"])}
- **Safe Charts:** {len(safe_charts)}
- **Affected Charts:** {len(affected_charts)}
- **Risk Percentage:** {(len(affected_charts) / len(self.dependencies_data["charts_analyzed"]) * 100):.1f}%

---

## 🏗️ Deployment Structure Analysis

"""
        
        # Define all deployment files in the correct order
        all_data_services_deployments = [
            "1.0_cicd_workload_runner.py",
            "2.0_object_storage_operator.py", 
            "3.0_data-cicd-workflows.py",
            "4.0_data_replication.py",
            "5.0_data_orchestration.py",
            "6.0_data_modeling.py",
            "7.0_data_dcdq_meta_collect.py",
            "8.0_data_analysis.py",
            "9.0_data_governance.py",
            "10.0_user_console.py",
            "11.0_data_image_puller.py"
        ]
        
        all_infra_services_deployments = [
            "1.0_secret_operator.py",
            "2.0_cert_manager.py",
            "3.0_external_dns.py",
            "4.0_traefik_lb.py",
            "5.0_stackgres_postgresql.py",
            "6.0_log_collector.py",
            "7.0_services_monitoring.py",
            "8.0_cluster_cleaner.py",
            "9.0_idp_sso_manager.py",
            "10.0_cluster_pvc_autoscaller.py"
        ]
        
        # Group charts by deployment file and service type
        data_services_deployments = {}
        infra_services_deployments = {}
        
        for chart_key, chart_data in self.dependencies_data["charts_analyzed"].items():
            chart_info = chart_data["chart_info"]
            service = chart_info["service"]
            
            # Extract deployment file name from service path
            if "/" in service:
                service_type = service.split("/")[0]  # data_services or infra_services
                deployment_name = service.split("/")[-1]  # e.g., data_orchestration
            else:
                service_type = "unknown"
                deployment_name = service
            
            # Convert to numbered deployment file name
            deployment_mapping = {
                # Data Services
                "cicd_workload_runner": "1.0_cicd_workload_runner.py",
                "object_storage_operator": "2.0_object_storage_operator.py", 
                "data-cicd-workflows": "3.0_data-cicd-workflows.py",
                "data_replication": "4.0_data_replication.py",
                "data_orchestration": "5.0_data_orchestration.py",
                "data_modeling": "6.0_data_modeling.py",
                "data_dcdq_meta_collect": "7.0_data_dcdq_meta_collect.py",
                "data_analysis": "8.0_data_analysis.py",
                "data_governance": "9.0_data_governance.py",
                "user_console": "10.0_user_console.py",
                "data_image_puller": "11.0_data_image_puller.py",
                # Infra Services
                "secret_operator": "1.0_secret_operator.py",
                "cert_manager": "2.0_cert_manager.py",
                "external_dns": "3.0_external_dns.py",
                "traefik_lb": "4.0_traefik_lb.py",
                "stackgres_postgresql": "5.0_stackgres_postgresql.py",
                "log_collector": "6.0_log_collector.py",
                "services_monitoring": "7.0_services_monitoring.py",
                "cluster_cleaner": "8.0_cluster_cleaner.py",
                "idp_sso_manager": "9.0_idp_sso_manager.py",
                "cluster_pvc_autoscaller": "10.0_cluster_pvc_autoscaller.py"
            }
            
            deployment_file = deployment_mapping.get(deployment_name, f"{deployment_name}.py")
            
            chart_info_dict = {
                "chart_name": chart_info["chart_name"],
                "chart_repo": chart_info["chart_repo"],
                "bitnami_deps": len(chart_data["bitnami_dependencies"]),
                "total_deps": len(chart_data["dependencies"]),
                "status": "⚠️ AFFECTED" if len(chart_data["bitnami_dependencies"]) > 0 else "✅ SAFE"
            }
            
            if service_type == "data_services":
                if deployment_file not in data_services_deployments:
                    data_services_deployments[deployment_file] = []
                data_services_deployments[deployment_file].append(chart_info_dict)
            elif service_type == "infra_services":
                if deployment_file not in infra_services_deployments:
                    infra_services_deployments[deployment_file] = []
                infra_services_deployments[deployment_file].append(chart_info_dict)
        
        # Data Services Section - Show ALL deployments
        report += "### Data Services Deployments\n\n"
        for deployment_file in all_data_services_deployments:
            charts = data_services_deployments.get(deployment_file, [])
            report += f"#### {deployment_file}\n\n"
            
            if charts:
                for chart in charts:
                    report += f"- **{chart['chart_name']}** ({chart['status']})\n"
                    report += f"  - Repository: `{chart['chart_repo']}`\n"
                    report += f"  - Dependencies: {chart['total_deps']} total, {chart['bitnami_deps']} Bitnami\n\n"
            else:
                report += "*No Helm charts found in this deployment*\n\n"
            
            report += "---\n\n"
        
        # Infra Services Section - Show ALL deployments
        report += "### Infrastructure Services Deployments\n\n"
        for deployment_file in all_infra_services_deployments:
            charts = infra_services_deployments.get(deployment_file, [])
            report += f"#### {deployment_file}\n\n"
            
            if charts:
                for chart in charts:
                    report += f"- **{chart['chart_name']}** ({chart['status']})\n"
                    report += f"  - Repository: `{chart['chart_repo']}`\n"
                    report += f"  - Dependencies: {chart['total_deps']} total, {chart['bitnami_deps']} Bitnami\n\n"
            else:
                report += "*No Helm charts found in this deployment*\n\n"
            
            report += "---\n\n"
        
        report += """
---

## 📈 Repository Usage Statistics

### Chart Repositories Used

"""
        
        # Collect repository statistics
        repo_stats = {}
        for chart_data in self.dependencies_data["charts_analyzed"].values():
            chart_info = chart_data["chart_info"]
            repo = chart_info["chart_repo"]
            if repo not in repo_stats:
                repo_stats[repo] = 0
            repo_stats[repo] += 1
        
        for repo, count in sorted(repo_stats.items()):
            report += f"- **{repo}**: {count} charts\n"
        
        report += """
---

## 🔍 Technical Details

### Analysis Methodology
1. **Chart Collection**: Scanned all Python service files for Helm chart references
2. **Repository Update**: Updated all Helm repositories to latest versions
3. **Chart Download**: Downloaded all identified charts as templates
4. **Dependency Analysis**: Parsed Chart.yaml files to identify dependencies
5. **Bitnami Detection**: Identified dependencies from Bitnami repositories

### Files Analyzed
"""
        
        # List analyzed files
        files_analyzed = set()
        for chart_data in self.dependencies_data["charts_analyzed"].values():
            chart_info = chart_data["chart_info"]
            service = chart_info["service"]
            
            # Convert service path to deployment file name
            if "/" in service:
                deployment_file = service.split("/")[-1] + ".py"
            else:
                deployment_file = service + ".py"
            
            files_analyzed.add(deployment_file)
        
        for file in sorted(files_analyzed):
            report += f"- `{file}`\n"
        
        report += """
---

## 📝 Recommendations

### Immediate Actions (Next 30 Days)
1. **Inventory Review**: Verify all identified dependencies are accurate
2. **Impact Assessment**: Evaluate business impact of each affected service
3. **Alternative Research**: Begin research on alternative chart providers

### Short-term Actions (Next 3 Months)
1. **Migration Planning**: Create detailed migration plan for each service
2. **Testing Strategy**: Develop testing approach for new chart versions
3. **Team Training**: Ensure team is familiar with alternative chart providers

### Medium-term Actions (Next 6 Months)
1. **Pilot Migration**: Start with low-risk services
2. **Validation**: Test migrated services in staging environment
3. **Documentation**: Update deployment documentation

### Long-term Actions (Before September 2025)
1. **Complete Migration**: Migrate all remaining services
2. **Production Validation**: Ensure all services work in production
3. **Monitoring**: Implement monitoring for new chart versions

---

## 📚 Additional Resources

- [Bitnami Helm Charts Migration Guide](https://docs.bitnami.com/kubernetes/)
- [Helm Chart Dependencies Documentation](https://helm.sh/docs/chart_template_guide/dependencies/)
- [Alternative Chart Providers](https://artifacthub.io/)

---

*This report was generated automatically by the Helm Dependencies Analyzer v2.*
"""
        
        return report
    
    def print_summary(self):
        """Print a summary of the dependencies analysis"""
        summary = self.dependencies_data["summary"]
        
        print("\n" + "="*70)
        print("HELM DEPENDENCIES ANALYSIS V2 - SUMMARY")
        print("="*70)
        print(f"Total Charts Analyzed: {summary['total_charts']}")
        print(f"Total Dependencies Found: {summary['total_dependencies']}")
        print(f"Total Bitnami Dependencies: {summary['bitnami_dependencies_count']}")
        print(f"  - Direct: {summary['direct_bitnami_dependencies']}")
        print(f"  - Transitive: {summary['transitive_bitnami_dependencies']}")
        print(f"Charts Affected by Bitnami: {summary['affected_charts_count']}")
        
        if self.dependencies_data["bitnami_dependencies"]["direct"]:
            print(f"\n⚠️  DIRECT BITNAMI DEPENDENCIES:")
            for dep in self.dependencies_data["bitnami_dependencies"]["direct"]:
                print(f"   - {dep['chart']}")
                for bitnami_dep in dep['dependencies']:
                    print(f"     └── {bitnami_dep['name']}@{bitnami_dep['version']} ({bitnami_dep['repository']})")
        
        print("="*70)
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if not self.keep_downloads and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary files")
            elif self.keep_downloads:
                logger.info(f"📁 Downloads preserved in: {self.temp_dir.absolute()}")
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze Helm chart dependencies for Bitnami usage (Systematic Approach)"
    )
    parser.add_argument(
        "--inventory",
        default="helm_charts_inventory.json",
        help="Path to Helm charts inventory file"
    )
    parser.add_argument(
        "--output",
        default="helm_dependencies_analysis.json",
        help="Output JSON file for dependencies analysis"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip printing summary to console"
    )
    parser.add_argument(
        "--keep-downloads",
        action="store_true",
        help="Keep downloaded charts for inspection (stored in helm_charts_downloads/)"
    )
    parser.add_argument(
        "--markdown-report",
        action="store_true",
        help="Generate a comprehensive Markdown report"
    )
    
    args = parser.parse_args()
    
    analyzer = HelmDependencyAnalyzerV2(args.inventory, args.keep_downloads)
    
    try:
        # Run the complete analysis
        dependencies_data = analyzer.run_analysis()
        
        # Save to JSON
        analyzer.save_to_json(args.output)
        
        # Generate Markdown report if requested
        if args.markdown_report:
            markdown_file = args.output.replace('.json', '_report.md')
            analyzer.save_to_markdown(markdown_file)
            print(f"📋 Markdown report saved to: {markdown_file}")
        
        # Print summary
        if not args.no_summary:
            analyzer.print_summary()
        
        print(f"\n✅ Helm dependencies analysis completed successfully!")
        print(f"📄 Detailed analysis saved to: {args.output}")
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        return 1
    finally:
        analyzer.cleanup()
    
    return 0

if __name__ == "__main__":
    exit(main())
