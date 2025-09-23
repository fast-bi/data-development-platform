import subprocess
import json

class InfraDataServicesLatestVersions:
    def __init__(self):
        self.system_infra_services = [
            "infisical/secrets-operator",
            "jetstack/cert-manager",
            "bitnami/external-dns",
            "traefik/traefik",
            "bitnami/keycloak",
            "minio/operator",
            "minio/tenant",
            "prometheus-community/prometheus",
            "grafana/grafana",
            "lwolf-charts/kube-cleanup-operator"
        ]

        self.data_services = [
            "oauth2-proxy/oauth2-proxy",
            "gitlab/gitlab-runner",
            "airbyte/airbyte",
            "apache-airflow/airflow",
            "datahub/datahub",
            "datahub/datahub-prerequisites",
            "elastic/eck-elasticsearch",
            "elastic/eck-operator",
            "jupyterhub/jupyterhub",
            "superset/superset",
            "lightdash/lightdash",
            "metabase/metabase"
        ]


        self.fastbi_data_service = json.loads("""{
            "fastbi_data_services": {
                "fastbi/tsb_fastbi_web_core_image_version": {
                    "name": "bi-platform/tsb-fastbi-web-core",
                    "tag": "Latest",
                    "version": "v0.2.0"
                },
                "fastbi/tsb_dbt_init_core_image_version": {
                    "name": "bi-platform/tsb-dbt-init-core",
                    "tag": "Latest",
                    "version": "v0.3.4"
                },
                "fastbi/dcdq_metacollect_app_version": {
                    "name": "bi-platform/tsb-fastbi-meta-api-core",
                    "tag": "Latest",
                    "version": "v1.0.0"
                },
                "fastbi/data_orchestration_app": {
                    "name": "airflow/app",
                    "tag": "Latest",
                    "version": "2.9.3"
                },
                "fastbi/data_replication_app": {
                    "name": "airbyte/app",
                    "tag": "Latest",
                    "version": "v0.64.1"
                },
                "fastbi/data_analysis_lightdash_app": {
                    "name": "lightdash/app",
                    "tag": "Latest",
                    "version": "0.1237.0"
                },
                "fastbi/data_analysis_superset_app": {
                    "name": "superset/app",
                    "tag": "Latest",
                    "version": "4.0.2"
                },
                "fastbi/data_analysis_metabase_app": {
                    "name": "metabase/app",
                    "tag": "Latest",
                    "version": "v0.50.21"
                },
                "fastbi/tsb_ide_coder_server_core": {
                    "name": "jupyterhub/app",
                    "tag": "Latest",
                    "version": "v4.92.2-focal"
                }
            }
        }""")

        self.deployment_info = {}
        self.repo_urls = {
            "infisical": "https://dl.cloudsmith.io/public/infisical/helm-charts/helm/charts/",
            "jetstack": "https://charts.jetstack.io",
            "bitnami": "https://charts.bitnami.com/bitnami",
            "traefik": "https://helm.traefik.io/traefik",
            "minio": "https://operator.min.io/",
            "prometheus-community": "https://prometheus-community.github.io/helm-charts/",
            "grafana": "https://grafana.github.io/helm-charts",
            "lwolf-charts": "http://charts.lwolf.org",
            "oauth2-proxy": "https://oauth2-proxy.github.io/manifests",
            "gitlab": "https://charts.gitlab.io/",
            "airbyte": "https://airbytehq.github.io/helm-charts",
            "apache-airflow": "https://airflow.apache.org",
            "datahub": "https://helm.datahubproject.io/",
            "elastic": "https://helm.elastic.co",
            "jupyterhub": "https://jupyterhub.github.io/helm-chart/",
            "superset": "https://apache.github.io/superset",
            "lightdash": "https://lightdash.github.io/helm-charts",
            "metabase": "https://pmint93.github.io/helm-charts"
        }

    def add_required_repos(self):
        """Add only the required repositories if they're not already present."""
        current_repos = self.get_current_repos()
        
        for chart in self.system_infra_services + self.data_services:
            repo_name = chart.split('/')[0]
            if repo_name not in current_repos and repo_name in self.repo_urls:
                self.add_repo(repo_name, self.repo_urls[repo_name])

    def get_current_repos(self):
        """Get the list of currently added repositories."""
        result = subprocess.run(["helm", "repo", "list", "-o", "json"], capture_output=True, text=True)
        if result.returncode == 0:
            repos = json.loads(result.stdout)
            return {repo['name'] for repo in repos}
        return set()

    def add_repo(self, name, url):
        """Add a repository to Helm."""
        subprocess.run(["helm", "repo", "add", name, url], check=True)

    def get_deployment_latest_versions(self, helm_chart):
        """Get the latest version of a Helm chart."""
        try:
            repo_name = helm_chart.split('/')[0]
            subprocess.run(["helm", "repo", "update", repo_name], check=True, capture_output=True)
            result = subprocess.run(
                ["helm", "search", "repo", helm_chart, "-o", "json"],
                capture_output=True, text=True, check=True
            )
            chart_info = json.loads(result.stdout)
            if chart_info:
                latest_chart = chart_info[0]
                return {
                    "name": latest_chart["name"],
                    "tag": "Latest",
                    "version": latest_chart["version"]
                }
            else:
                return None
        except subprocess.CalledProcessError as e:
            print(f"Failed to run helm command: {e}")
            return None
        except json.JSONDecodeError:
            print("Failed to parse JSON output from helm command.")
            return None

    def get_latest_versions_for_charts(self, charts):
        return {chart: self.get_deployment_latest_versions(chart) for chart in charts}

    def update(self):
        self.add_required_repos()
        self.deployment_info = {
            "system_infra_services": self.get_latest_versions_for_charts(self.system_infra_services),
            "data_services": self.get_latest_versions_for_charts(self.data_services)
        }
        # Merge the fastbi_data_service into the deployment_info
        self.deployment_info.update(self.fastbi_data_service)
        return self.deployment_info