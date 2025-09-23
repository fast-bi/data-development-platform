#!/usr/bin/env python3
"""
Helm Charts Collector for fast.bi Data Platform

This script scans through the deployers/services directory and extracts all Helm chart
information including chart repositories, chart names, and versions from the Python
service deployment files.

Output: JSON file with all discovered Helm charts organized by service category.
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HelmChartCollector:
    def __init__(self, services_dir: str = "../deployers/services"):
        self.services_dir = Path(services_dir)
        self.charts_data = {
            "data_services": {},
            "infra_services": {},
            "summary": {
                "total_services": 0,
                "total_charts": 0,
                "bitnami_dependencies": [],
                "chart_repositories": set()
            }
        }
        
    def collect_all_charts(self) -> Dict[str, Any]:
        """Collect all Helm charts from both data_services and infra_services directories"""
        logger.info("Starting Helm charts collection...")
        logger.info(f"Services directory: {self.services_dir}")
        logger.info(f"Services directory exists: {self.services_dir.exists()}")
        
        # Collect from data services
        data_services_dir = self.services_dir / "data_services"
        logger.info(f"Data services directory: {data_services_dir}")
        logger.info(f"Data services directory exists: {data_services_dir.exists()}")
        if data_services_dir.exists():
            logger.info(f"Scanning data services in: {data_services_dir}")
            self.charts_data["data_services"] = self._scan_service_directory(data_services_dir)
        else:
            logger.error(f"Data services directory not found: {data_services_dir}")
        
        # Collect from infra services
        infra_services_dir = self.services_dir / "infra_services"
        logger.info(f"Infra services directory: {infra_services_dir}")
        logger.info(f"Infra services directory exists: {infra_services_dir.exists()}")
        if infra_services_dir.exists():
            logger.info(f"Scanning infra services in: {infra_services_dir}")
            self.charts_data["infra_services"] = self._scan_service_directory(infra_services_dir)
        else:
            logger.error(f"Infra services directory not found: {infra_services_dir}")
        
        # Generate summary
        self._generate_summary()
        
        logger.info("Helm charts collection completed")
        return self.charts_data
    
    def _scan_service_directory(self, service_dir: Path) -> Dict[str, Any]:
        """Scan a service directory and extract chart information from Python files"""
        services = {}
        
        logger.info(f"Scanning directory: {service_dir}")
        py_files = list(service_dir.glob("*.py"))
        logger.info(f"Found {len(py_files)} Python files")
        
        for py_file in py_files:
            if py_file.name.startswith(".") or py_file.name == "__init__.py":
                continue
                
            logger.info(f"Processing file: {py_file.name}")
            service_name = self._extract_service_name(py_file.name)
            service_data = self._extract_charts_from_file(py_file)
            
            if service_data:
                services[service_name] = service_data
                logger.info(f"Found {len(service_data.get('charts', []))} charts in {service_name}")
            else:
                logger.info(f"No charts found in {service_name}")
        
        return services
    
    def _extract_service_name(self, filename: str) -> str:
        """Extract service name from filename"""
        # Remove numbering prefix and .py extension
        name = re.sub(r'^\d+\.\d+_', '', filename)
        name = name.replace('.py', '')
        return name
    
    def _extract_charts_from_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract chart information from a Python service file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            service_data = {
                "file": str(file_path),
                "charts": [],
                "extra_charts": []
            }
            
            # Extract chart information using regex patterns
            charts = self._extract_chart_patterns(content)
            service_data["charts"] = charts
            
            # Extract extra charts (like kube-core/raw)
            extra_charts = self._extract_extra_chart_patterns(content)
            service_data["extra_charts"] = extra_charts
            
            # Extract chart versions
            versions = self._extract_chart_versions(content)
            service_data["versions"] = versions
            
            # Extract deployment names
            deployment_names = self._extract_deployment_names(content)
            service_data["deployment_names"] = deployment_names
            
            # Debug output
            if charts or extra_charts:
                logger.info(f"Found {len(charts)} charts and {len(extra_charts)} extra charts in {file_path.name}")
                for chart in charts:
                    logger.debug(f"  Chart: {chart['chart_name']} from {chart['chart_repo']}")
                for chart in extra_charts:
                    logger.debug(f"  Extra Chart: {chart['chart_name']} from {chart['chart_repo']}")
            else:
                logger.debug(f"No charts found in {file_path.name}")
            
            return service_data if (charts or extra_charts) else None
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None
    
    def _extract_chart_patterns(self, content: str) -> List[Dict[str, str]]:
        """Extract chart repository and name patterns from content"""
        charts = []
        
        # Simple approach: find all chart_repo and chart_name assignments
        # Pattern to find all chart_repo assignments (including those in conditional blocks)
        repo_pattern = r'self\.(\w+_?chart_repo)\s*=\s*["\']([^"\']+)["\']'
        repo_matches = re.finditer(repo_pattern, content)
        
        for repo_match in repo_matches:
            repo_var_name = repo_match.group(1)  # e.g., "chart_repo", "data_replication_chart_repo"
            repo_url = repo_match.group(2)
            
            # Extract the base name (remove _chart_repo suffix)
            base_name = repo_var_name.replace('_chart_repo', '')
            
            # Look for corresponding chart_name
            if base_name == '':
                # Handle case where it's just "chart_repo"
                name_pattern = r'self\.chart_name\s*=\s*["\']([^"\']+)["\']'
            else:
                # Handle case where it's "something_chart_name"
                name_pattern = rf'self\.{base_name}_chart_name\s*=\s*["\']([^"\']+)["\']'
            
            name_match = re.search(name_pattern, content)
            if name_match:
                chart_name = name_match.group(1)
                charts.append({
                    "chart_repo": repo_url,
                    "chart_name": chart_name,
                    "chart_repo_name": self._extract_repo_name(repo_url)
                })
        
        # Handle special cases where chart_name is a dictionary
        dict_pattern = r'self\.chart_name\s*=\s*\{([^}]+)\}'
        dict_matches = re.finditer(dict_pattern, content, re.DOTALL)
        
        for match in dict_matches:
            dict_content = match.group(1)
            # Extract individual chart names from dictionary
            chart_name_matches = re.findall(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', dict_content)
            for key, chart_name in chart_name_matches:
                # Find corresponding repo for this chart
                repo_pattern = r'self\.chart_repo\s*=\s*["\']([^"\']+)["\']'
                repo_match = re.search(repo_pattern, content)
                if repo_match:
                    charts.append({
                        "chart_repo": repo_match.group(1),
                        "chart_name": chart_name,
                        "chart_repo_name": self._extract_repo_name(repo_match.group(1)),
                        "service_key": key
                    })
        
        # Handle conditional chart assignments (like in cicd_workload_runner.py)
        # Look for patterns like: if self.git_provider == "gitlab": self.chart_name = "gitlab/gitlab-runner"
        conditional_pattern = r'if\s+self\.\w+\s*==\s*["\']([^"\']+)["\']\s*:.*?self\.chart_name\s*=\s*["\']([^"\']+)["\']'
        conditional_matches = re.finditer(conditional_pattern, content, re.DOTALL)
        
        for match in conditional_matches:
            condition_value = match.group(1)  # e.g., "gitlab", "github"
            chart_name = match.group(2)  # e.g., "gitlab/gitlab-runner"
            
            # Find corresponding chart_repo for this condition
            # Look for the chart_repo assignment in the same conditional block
            conditional_block_pattern = rf'if\s+self\.\w+\s*==\s*["\']{re.escape(condition_value)}["\']\s*:.*?self\.chart_repo\s*=\s*["\']([^"\']+)["\']'
            repo_match = re.search(conditional_block_pattern, content, re.DOTALL)
            
            if repo_match:
                repo_url = repo_match.group(1)
                charts.append({
                    "chart_repo": repo_url,
                    "chart_name": chart_name,
                    "chart_repo_name": self._extract_repo_name(repo_url),
                    "condition": condition_value
                })
        
        # Handle method-based conditional chart assignments (like in data_analysis.py)
        # Look for patterns like: def _initialize_superset(self): self.chart_name = "superset/superset"
        method_pattern = r'def\s+_initialize_(\w+)\(self\):.*?self\.chart_name\s*=\s*["\']([^"\']+)["\']'
        method_matches = re.finditer(method_pattern, content, re.DOTALL)
        
        for match in method_matches:
            method_name = match.group(1)  # e.g., "superset", "lightdash"
            chart_name = match.group(2)  # e.g., "superset/superset"
            
            # Find corresponding chart_repo in the same method
            method_block_pattern = rf'def\s+_initialize_{re.escape(method_name)}\(self\):.*?self\.chart_repo\s*=\s*["\']([^"\']+)["\']'
            repo_match = re.search(method_block_pattern, content, re.DOTALL)
            
            if repo_match:
                repo_url = repo_match.group(1)
                charts.append({
                    "chart_repo": repo_url,
                    "chart_name": chart_name,
                    "chart_repo_name": self._extract_repo_name(repo_url),
                    "condition": method_name
                })
        
        return charts
    
    def _extract_extra_chart_patterns(self, content: str) -> List[Dict[str, str]]:
        """Extract extra chart patterns (like kube-core/raw)"""
        extra_charts = []
        
        # Find all chart_name assignments that might be extra charts
        # Look for patterns like extra_chart_name, bi_psql_chart_name, etc.
        extra_name_pattern = r'self\.(\w+_?chart_name)\s*=\s*["\']([^"\']+)["\']'
        name_matches = re.finditer(extra_name_pattern, content)
        
        for name_match in name_matches:
            name_var = name_match.group(1)  # e.g., "extra_chart_name", "bi_psql_chart_name"
            chart_name = name_match.group(2)
            
            # Extract base name (remove _chart_name suffix)
            base_name = name_var.replace('_chart_name', '')
            
            # Look for corresponding chart_repo
            if base_name == '':
                # Handle case where it's just "chart_name"
                repo_pattern = r'self\.chart_repo\s*=\s*["\']([^"\']+)["\']'
            else:
                # Handle case where it's "something_chart_repo"
                repo_pattern = rf'self\.{base_name}_chart_repo\s*=\s*["\']([^"\']+)["\']'
            
            repo_match = re.search(repo_pattern, content)
            if repo_match:
                extra_charts.append({
                    "chart_repo": repo_match.group(1),
                    "chart_name": chart_name,
                    "chart_repo_name": self._extract_repo_name(repo_match.group(1)),
                    "chart_type": "extra"
                })
        
        return extra_charts
    
    def _extract_chart_versions(self, content: str) -> Dict[str, str]:
        """Extract chart versions from content"""
        versions = {}
        
        # Pattern for chart version assignments
        version_patterns = [
            r'self\.chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.extra_chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.bi_psql_chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.data_replication_psql_chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.data_dcdq_metacollect_psql_chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.data_modeling_psql_chart_version\s*=\s*["\']([^"\']+)["\']',
            r'self\.user_console_psql_chart_version\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in version_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                version = match.group(1)
                # Extract the variable name
                var_name = re.search(r'self\.(\w+)_chart_version', pattern)
                if var_name:
                    versions[var_name.group(1)] = version
        
        return versions
    
    def _extract_deployment_names(self, content: str) -> Dict[str, str]:
        """Extract deployment names from content"""
        deployment_names = {}
        
        # Pattern for deployment name assignments
        deployment_patterns = [
            r'self\.deployment_name\s*=\s*["\']([^"\']+)["\']',
            r'self\.extra_deployment_name\s*=\s*["\']([^"\']+)["\']',
            r'self\.data_replication_deployment_name\s*=\s*["\']([^"\']+)["\']',
            r'self\.data_replication_oauth_deployment_name\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in deployment_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                deployment_name = match.group(1)
                # Extract the variable name
                var_name = re.search(r'self\.(\w+)_deployment_name', pattern)
                if var_name:
                    deployment_names[var_name.group(1)] = deployment_name
        
        return deployment_names
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        # Extract the last part of the URL path
        if '/' in repo_url:
            return repo_url.rstrip('/').split('/')[-1]
        return repo_url
    
    def _generate_summary(self):
        """Generate summary statistics"""
        total_services = 0
        total_charts = 0
        bitnami_dependencies = []
        chart_repositories = set()
        
        # Process data services
        for service_name, service_data in self.charts_data["data_services"].items():
            total_services += 1
            for chart in service_data.get("charts", []):
                total_charts += 1
                chart_repositories.add(chart["chart_repo"])
                if "bitnami" in chart["chart_repo"].lower():
                    bitnami_dependencies.append({
                        "service": f"data_services/{service_name}",
                        "chart": chart["chart_name"],
                        "repo": chart["chart_repo"]
                    })
            
            for chart in service_data.get("extra_charts", []):
                total_charts += 1
                chart_repositories.add(chart["chart_repo"])
                if "bitnami" in chart["chart_repo"].lower():
                    bitnami_dependencies.append({
                        "service": f"data_services/{service_name}",
                        "chart": chart["chart_name"],
                        "repo": chart["chart_repo"]
                    })
        
        # Process infra services
        for service_name, service_data in self.charts_data["infra_services"].items():
            total_services += 1
            for chart in service_data.get("charts", []):
                total_charts += 1
                chart_repositories.add(chart["chart_repo"])
                if "bitnami" in chart["chart_repo"].lower():
                    bitnami_dependencies.append({
                        "service": f"infra_services/{service_name}",
                        "chart": chart["chart_name"],
                        "repo": chart["chart_repo"]
                    })
            
            for chart in service_data.get("extra_charts", []):
                total_charts += 1
                chart_repositories.add(chart["chart_repo"])
                if "bitnami" in chart["chart_repo"].lower():
                    bitnami_dependencies.append({
                        "service": f"infra_services/{service_name}",
                        "chart": chart["chart_name"],
                        "repo": chart["chart_repo"]
                    })
        
        self.charts_data["summary"] = {
            "total_services": total_services,
            "total_charts": total_charts,
            "bitnami_dependencies": bitnami_dependencies,
            "chart_repositories": sorted(list(chart_repositories))
        }
    
    def save_to_json(self, output_file: str = "helm_charts_inventory.json"):
        """Save the collected data to a JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.charts_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Helm charts inventory saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")
            raise
    
    def print_summary(self):
        """Print a summary of the collected data"""
        summary = self.charts_data["summary"]
        
        print("\n" + "="*60)
        print("HELM CHARTS INVENTORY SUMMARY")
        print("="*60)
        print(f"Total Services: {summary['total_services']}")
        print(f"Total Charts: {summary['total_charts']}")
        print(f"Unique Chart Repositories: {len(summary['chart_repositories'])}")
        
        if summary['bitnami_dependencies']:
            print(f"\n⚠️  BITNAMI DEPENDENCIES FOUND ({len(summary['bitnami_dependencies'])}):")
            print("   (These will be affected by Bitnami's closure in 2025-09)")
            for dep in summary['bitnami_dependencies']:
                print(f"   - {dep['service']}: {dep['chart']}")
        else:
            print("\n✅ No Bitnami dependencies found")
        
        print(f"\nChart Repositories Used:")
        for repo in summary['chart_repositories']:
            print(f"   - {repo}")
        print("="*60)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect Helm charts from fast.bi data platform services"
    )
    parser.add_argument(
        "--services-dir",
        default="../deployers/services",
        help="Path to services directory (default: ../deployers/services)"
    )
    parser.add_argument(
        "--output",
        default="helm_charts_inventory.json",
        help="Output JSON file (default: helm_charts_inventory.json)"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip printing summary to console"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize collector
        collector = HelmChartCollector(args.services_dir)
        
        # Collect all charts
        charts_data = collector.collect_all_charts()
        
        # Save to JSON
        collector.save_to_json(args.output)
        
        # Print summary
        if not args.no_summary:
            collector.print_summary()
        
        print(f"\n✅ Helm charts inventory completed successfully!")
        print(f"📄 Detailed data saved to: {args.output}")
        
    except Exception as e:
        logger.error(f"Error during collection: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
