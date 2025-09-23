# Helm Dependencies Analysis Report
## Fast.bi Data Platform - Bitnami Migration Assessment

**Generated:** 2025-08-24 21:26:20  
**Analysis Date:** 2025-08-24  
**Bitnami Closure Date:** 2025-09-01  

---

## 📊 Executive Summary

This report analyzes Helm chart dependencies in the fast.bi data platform to identify services affected by Bitnami's planned closure in September 2025.

### Key Findings:
- **20 charts analyzed**
- **40 total dependencies found**
- **9 Bitnami dependencies identified**
- **9 charts affected by Bitnami closure**

### Risk Assessment:
⚠️ **HIGH RISK** - Multiple critical services depend on Bitnami charts that will become unavailable in September 2025.

---

## 🎯 Affected Services

### Direct Bitnami Dependencies

#### data_services/data_orchestration:apache-airflow/airflow

- **postgresql@13.2.24**
  - Repository: `https://charts.bitnami.com/bitnami`

#### data_services/data_dcdq_meta_collect:bitnami/postgresql

- **common@2.x.x**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

#### data_services/data_dcdq_meta_collect:oauth2-proxy/oauth2-proxy

- **redis-ha@4.33.8**
  - Repository: `https://dandydeveloper.github.io/charts`
  - Alias: `redis`

#### data_services/data_replication:airbyte/airbyte

- **keycloak@1.8.1**
  - Repository: `https://airbytehq.github.io/helm-charts/`

#### data_services/data_governance:datahub/datahub-prerequisites

- **elasticsearch@7.17.3**
  - Repository: `https://helm.elastic.co`

- **mysql@9.4.9**
  - Repository: `https://charts.bitnami.com/bitnami`

- **postgresql@11.2.6**
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

- **kafka@26.11.2**
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

#### data_services/data_analysis:superset/superset

- **postgresql@13.4.4**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- **redis@17.9.4**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

#### data_services/data_analysis:lightdash/lightdash

- **common@1.x.x**
  - Repository: `https://charts.bitnami.com/bitnami`

- **postgresql@11.x.x**
  - Repository: `https://charts.bitnami.com/bitnami`

#### data_services/data_modeling:oci://registry-1.docker.io/bitnamicharts/postgresql

- **common@2.x.x**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

#### infra_services/idp_sso_manager:bitnami/keycloak

- **postgresql@16.x.x**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- **common@2.x.x**
  - Repository: `oci://registry-1.docker.io/bitnamicharts`


---

## 📋 Detailed Chart Analysis

### Charts with Dependencies

#### data_services/data_orchestration:apache-airflow/airflow

- **Chart:** `apache-airflow/airflow`
- **Repository:** `https://airflow.apache.org`
- **Service:** `data_services/data_orchestration`
- **Total Dependencies:** 1
- **Bitnami Dependencies:** 1
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `postgresql@13.2.24`
  - Repository: `https://charts.bitnami.com/bitnami`

**⚠️ Bitnami Dependencies (Require Migration):**
- `postgresql@13.2.24`
  - Repository: `https://charts.bitnami.com/bitnami`

---

#### data_services/data_orchestration:kube-core/raw

- **Chart:** `kube-core/raw`
- **Repository:** `https://kube-core.github.io/helm-charts`
- **Service:** `data_services/data_orchestration`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/data_dcdq_meta_collect:bitnami/postgresql

- **Chart:** `bitnami/postgresql`
- **Repository:** `https://charts.bitnami.com/bitnami`
- **Service:** `data_services/data_dcdq_meta_collect`
- **Total Dependencies:** 1
- **Bitnami Dependencies:** 1
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

**⚠️ Bitnami Dependencies (Require Migration):**
- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

---

#### data_services/data_dcdq_meta_collect:oauth2-proxy/oauth2-proxy

- **Chart:** `oauth2-proxy/oauth2-proxy`
- **Repository:** `https://oauth2-proxy.github.io/manifests`
- **Service:** `data_services/data_dcdq_meta_collect`
- **Total Dependencies:** 1
- **Bitnami Dependencies:** 1
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `redis-ha@4.33.8`
  - Repository: `https://dandydeveloper.github.io/charts`
  - Alias: `redis`

**⚠️ Bitnami Dependencies (Require Migration):**
- `redis-ha@4.33.8`
  - Repository: `https://dandydeveloper.github.io/charts`
  - Alias: `redis`

---

#### data_services/data_replication:airbyte/airbyte

- **Chart:** `airbyte/airbyte`
- **Repository:** `https://airbytehq.github.io/helm-charts`
- **Service:** `data_services/data_replication`
- **Total Dependencies:** 14
- **Bitnami Dependencies:** 1
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `airbyte-bootloader@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `temporal@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `temporal-ui@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `webapp@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `server@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `worker@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `workload-api-server@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `workload-launcher@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `metrics@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `cron@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `connector-builder-server@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `connector-rollout-worker@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `keycloak@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

- `keycloak-setup@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

**⚠️ Bitnami Dependencies (Require Migration):**
- `keycloak@1.8.1`
  - Repository: `https://airbytehq.github.io/helm-charts/`

---

#### data_services/data_governance:datahub/datahub

- **Chart:** `datahub/datahub`
- **Repository:** `https://helm.datahubproject.io/`
- **Service:** `data_services/data_governance`
- **Total Dependencies:** 6
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:**
- `datahub-gms@0.2.186`
  - Repository: `file://./subcharts/datahub-gms`

- `datahub-frontend@0.2.164`
  - Repository: `file://./subcharts/datahub-frontend`

- `datahub-mae-consumer@0.2.166`
  - Repository: `file://./subcharts/datahub-mae-consumer`

- `datahub-mce-consumer@0.2.170`
  - Repository: `file://./subcharts/datahub-mce-consumer`

- `datahub-ingestion-cron@0.2.148`
  - Repository: `file://./subcharts/datahub-ingestion-cron`

- `acryl-datahub-actions@0.2.153`
  - Repository: `file://./subcharts/acryl-datahub-actions`

---

#### data_services/data_governance:datahub/datahub-prerequisites

- **Chart:** `datahub/datahub-prerequisites`
- **Repository:** `https://helm.datahubproject.io/`
- **Service:** `data_services/data_governance`
- **Total Dependencies:** 8
- **Bitnami Dependencies:** 4
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `elasticsearch@7.17.3`
  - Repository: `https://helm.elastic.co`

- `opensearch@2.18.0`
  - Repository: `https://opensearch-project.github.io/helm-charts`

- `neo4j@5.11.0`
  - Repository: `https://helm.neo4j.com/neo4j`

- `mysql@9.4.9`
  - Repository: `https://charts.bitnami.com/bitnami`

- `postgresql@11.2.6`
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

- `gcloud-sqlproxy@0.24.1`
  - Repository: `https://charts.rimusz.net`

- `cp-helm-charts@0.6.0`
  - Repository: `https://confluentinc.github.io/cp-helm-charts/`

- `kafka@26.11.2`
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

**⚠️ Bitnami Dependencies (Require Migration):**
- `elasticsearch@7.17.3`
  - Repository: `https://helm.elastic.co`

- `mysql@9.4.9`
  - Repository: `https://charts.bitnami.com/bitnami`

- `postgresql@11.2.6`
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

- `kafka@26.11.2`
  - Repository: `https://raw.githubusercontent.com/bitnami/charts/archive-full-index/bitnami`

---

#### data_services/data_governance:elastic/eck-elasticsearch

- **Chart:** `elastic/eck-elasticsearch`
- **Repository:** `https://helm.elastic.co`
- **Service:** `data_services/data_governance`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/data_governance:elastic/eck-operator

- **Chart:** `elastic/eck-operator`
- **Repository:** `https://helm.elastic.co`
- **Service:** `data_services/data_governance`
- **Total Dependencies:** 1
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:**
- `eck-operator-crds@3.1.0`

---

#### data_services/data-cicd-workflows:argo/argo-workflows

- **Chart:** `argo/argo-workflows`
- **Repository:** `https://argoproj.github.io/argo-helm`
- **Service:** `data_services/data-cicd-workflows`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/data_analysis:superset/superset

- **Chart:** `superset/superset`
- **Repository:** `https://apache.github.io/superset`
- **Service:** `data_services/data_analysis`
- **Total Dependencies:** 2
- **Bitnami Dependencies:** 2
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `postgresql@13.4.4`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- `redis@17.9.4`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

**⚠️ Bitnami Dependencies (Require Migration):**
- `postgresql@13.4.4`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- `redis@17.9.4`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

---

#### data_services/data_analysis:lightdash/lightdash

- **Chart:** `lightdash/lightdash`
- **Repository:** `https://lightdash.github.io/helm-charts`
- **Service:** `data_services/data_analysis`
- **Total Dependencies:** 3
- **Bitnami Dependencies:** 2
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `common@1.x.x`
  - Repository: `https://charts.bitnami.com/bitnami`

- `postgresql@11.x.x`
  - Repository: `https://charts.bitnami.com/bitnami`

- `browserless-chrome@0.0.5`
  - Repository: `https://charts.sagikazarmark.dev`

**⚠️ Bitnami Dependencies (Require Migration):**
- `common@1.x.x`
  - Repository: `https://charts.bitnami.com/bitnami`

- `postgresql@11.x.x`
  - Repository: `https://charts.bitnami.com/bitnami`

---

#### data_services/data_analysis:metabase/metabase

- **Chart:** `metabase/metabase`
- **Repository:** `https://pmint93.github.io/helm-charts`
- **Service:** `data_services/data_analysis`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/cicd_workload_runner:gitlab/gitlab-runner

- **Chart:** `gitlab/gitlab-runner`
- **Repository:** `https://charts.gitlab.io/`
- **Service:** `data_services/cicd_workload_runner`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/cicd_workload_runner:actions-runner-controller/actions-runner-controller

- **Chart:** `actions-runner-controller/actions-runner-controller`
- **Repository:** `https://actions-runner-controller.github.io/actions-runner-controller`
- **Service:** `data_services/cicd_workload_runner`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/data_modeling:jupyterhub/jupyterhub

- **Chart:** `jupyterhub/jupyterhub`
- **Repository:** `https://jupyterhub.github.io/helm-chart/`
- **Service:** `data_services/data_modeling`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### data_services/data_modeling:oci://registry-1.docker.io/bitnamicharts/postgresql

- **Chart:** `oci://registry-1.docker.io/bitnamicharts/postgresql`
- **Repository:** `https://charts.bitnami.com/bitnami`
- **Service:** `data_services/data_modeling`
- **Total Dependencies:** 1
- **Bitnami Dependencies:** 1
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

**⚠️ Bitnami Dependencies (Require Migration):**
- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

---

#### data_services/object_storage_operator:minio/tenant

- **Chart:** `minio/tenant`
- **Repository:** `https://operator.min.io/`
- **Service:** `data_services/object_storage_operator`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---

#### infra_services/idp_sso_manager:bitnami/keycloak

- **Chart:** `bitnami/keycloak`
- **Repository:** `https://charts.bitnami.com/bitnami`
- **Service:** `infra_services/idp_sso_manager`
- **Total Dependencies:** 2
- **Bitnami Dependencies:** 2
- **Status:** ⚠️ **AFFECTED** - Has Bitnami dependencies

**Dependencies:**
- `postgresql@16.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

**⚠️ Bitnami Dependencies (Require Migration):**
- `postgresql@16.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

- `common@2.x.x`
  - Repository: `oci://registry-1.docker.io/bitnamicharts`

---

#### infra_services/traefik_lb:traefik/traefik

- **Chart:** `traefik/traefik`
- **Repository:** `https://helm.traefik.io/traefik`
- **Service:** `infra_services/traefik_lb`
- **Total Dependencies:** 0
- **Bitnami Dependencies:** 0
- **Status:** ✅ **SAFE** - No Bitnami dependencies

**Dependencies:** None

---


---

## 🚨 Migration Priority Matrix

### High Priority (Critical Services)
Services that directly depend on Bitnami charts and are essential for platform operation:

- **data_services/data_dcdq_meta_collect:bitnami/postgresql** - Database/Storage dependency
- **data_services/data_modeling:oci://registry-1.docker.io/bitnamicharts/postgresql** - Database/Storage dependency

### Medium Priority (Service Dependencies)
Services that depend on other charts that use Bitnami:

- **data_services/data_orchestration:apache-airflow/airflow** - Application dependency
- **data_services/data_dcdq_meta_collect:oauth2-proxy/oauth2-proxy** - Application dependency
- **data_services/data_replication:airbyte/airbyte** - Application dependency
- **data_services/data_governance:datahub/datahub-prerequisites** - Application dependency
- **data_services/data_analysis:superset/superset** - Application dependency
- **data_services/data_analysis:lightdash/lightdash** - Application dependency
- **infra_services/idp_sso_manager:bitnami/keycloak** - Application dependency

---

## 📋 Complete Chart Inventory

### All Charts with Status

#### ✅ Safe Charts (No Bitnami Dependencies)

- **actions-runner-controller/actions-runner-controller** (`data_services/cicd_workload_runner`)
- **argo/argo-workflows** (`data_services/data-cicd-workflows`)
- **datahub/datahub** (`data_services/data_governance`)
- **elastic/eck-elasticsearch** (`data_services/data_governance`)
- **elastic/eck-operator** (`data_services/data_governance`)
- **gitlab/gitlab-runner** (`data_services/cicd_workload_runner`)
- **jupyterhub/jupyterhub** (`data_services/data_modeling`)
- **kube-core/raw** (`data_services/data_orchestration`)
- **metabase/metabase** (`data_services/data_analysis`)
- **minio/tenant** (`data_services/object_storage_operator`)
- **traefik/traefik** (`infra_services/traefik_lb`)

#### ⚠️ Affected Charts (Has Bitnami Dependencies)

- **airbyte/airbyte** (`data_services/data_replication`)
- **apache-airflow/airflow** (`data_services/data_orchestration`)
- **bitnami/keycloak** (`infra_services/idp_sso_manager`)
- **bitnami/postgresql** (`data_services/data_dcdq_meta_collect`)
- **datahub/datahub-prerequisites** (`data_services/data_governance`)
- **lightdash/lightdash** (`data_services/data_analysis`)
- **oauth2-proxy/oauth2-proxy** (`data_services/data_dcdq_meta_collect`)
- **oci://registry-1.docker.io/bitnamicharts/postgresql** (`data_services/data_modeling`)
- **superset/superset** (`data_services/data_analysis`)


**Summary:**
- **Total Charts:** 20
- **Safe Charts:** 11
- **Affected Charts:** 9
- **Risk Percentage:** 45.0%

---

## 🏗️ Deployment Structure Analysis

### Data Services Deployments

#### 1.0_cicd_workload_runner.py

- **gitlab/gitlab-runner** (✅ SAFE)
  - Repository: `https://charts.gitlab.io/`
  - Dependencies: 0 total, 0 Bitnami

- **actions-runner-controller/actions-runner-controller** (✅ SAFE)
  - Repository: `https://actions-runner-controller.github.io/actions-runner-controller`
  - Dependencies: 0 total, 0 Bitnami

---

#### 2.0_object_storage_operator.py

- **minio/tenant** (✅ SAFE)
  - Repository: `https://operator.min.io/`
  - Dependencies: 0 total, 0 Bitnami

---

#### 3.0_data-cicd-workflows.py

- **argo/argo-workflows** (✅ SAFE)
  - Repository: `https://argoproj.github.io/argo-helm`
  - Dependencies: 0 total, 0 Bitnami

---

#### 4.0_data_replication.py

- **airbyte/airbyte** (⚠️ AFFECTED)
  - Repository: `https://airbytehq.github.io/helm-charts`
  - Dependencies: 14 total, 1 Bitnami

---

#### 5.0_data_orchestration.py

- **apache-airflow/airflow** (⚠️ AFFECTED)
  - Repository: `https://airflow.apache.org`
  - Dependencies: 1 total, 1 Bitnami

- **kube-core/raw** (✅ SAFE)
  - Repository: `https://kube-core.github.io/helm-charts`
  - Dependencies: 0 total, 0 Bitnami

---

#### 6.0_data_modeling.py

- **jupyterhub/jupyterhub** (✅ SAFE)
  - Repository: `https://jupyterhub.github.io/helm-chart/`
  - Dependencies: 0 total, 0 Bitnami

- **oci://registry-1.docker.io/bitnamicharts/postgresql** (⚠️ AFFECTED)
  - Repository: `https://charts.bitnami.com/bitnami`
  - Dependencies: 1 total, 1 Bitnami

---

#### 7.0_data_dcdq_meta_collect.py

- **bitnami/postgresql** (⚠️ AFFECTED)
  - Repository: `https://charts.bitnami.com/bitnami`
  - Dependencies: 1 total, 1 Bitnami

- **oauth2-proxy/oauth2-proxy** (⚠️ AFFECTED)
  - Repository: `https://oauth2-proxy.github.io/manifests`
  - Dependencies: 1 total, 1 Bitnami

---

#### 8.0_data_analysis.py

- **superset/superset** (⚠️ AFFECTED)
  - Repository: `https://apache.github.io/superset`
  - Dependencies: 2 total, 2 Bitnami

- **lightdash/lightdash** (⚠️ AFFECTED)
  - Repository: `https://lightdash.github.io/helm-charts`
  - Dependencies: 3 total, 2 Bitnami

- **metabase/metabase** (✅ SAFE)
  - Repository: `https://pmint93.github.io/helm-charts`
  - Dependencies: 0 total, 0 Bitnami

---

#### 9.0_data_governance.py

- **datahub/datahub** (✅ SAFE)
  - Repository: `https://helm.datahubproject.io/`
  - Dependencies: 6 total, 0 Bitnami

- **datahub/datahub-prerequisites** (⚠️ AFFECTED)
  - Repository: `https://helm.datahubproject.io/`
  - Dependencies: 8 total, 4 Bitnami

- **elastic/eck-elasticsearch** (✅ SAFE)
  - Repository: `https://helm.elastic.co`
  - Dependencies: 0 total, 0 Bitnami

- **elastic/eck-operator** (✅ SAFE)
  - Repository: `https://helm.elastic.co`
  - Dependencies: 1 total, 0 Bitnami

---

#### 10.0_user_console.py

*No Helm charts found in this deployment*

---

#### 11.0_data_image_puller.py

*No Helm charts found in this deployment*

---

### Infrastructure Services Deployments

#### 1.0_secret_operator.py

*No Helm charts found in this deployment*

---

#### 2.0_cert_manager.py

*No Helm charts found in this deployment*

---

#### 3.0_external_dns.py

*No Helm charts found in this deployment*

---

#### 4.0_traefik_lb.py

- **traefik/traefik** (✅ SAFE)
  - Repository: `https://helm.traefik.io/traefik`
  - Dependencies: 0 total, 0 Bitnami

---

#### 5.0_stackgres_postgresql.py

*No Helm charts found in this deployment*

---

#### 6.0_log_collector.py

*No Helm charts found in this deployment*

---

#### 7.0_services_monitoring.py

*No Helm charts found in this deployment*

---

#### 8.0_cluster_cleaner.py

*No Helm charts found in this deployment*

---

#### 9.0_idp_sso_manager.py

- **bitnami/keycloak** (⚠️ AFFECTED)
  - Repository: `https://charts.bitnami.com/bitnami`
  - Dependencies: 2 total, 2 Bitnami

---

#### 10.0_cluster_pvc_autoscaller.py

*No Helm charts found in this deployment*

---


---

## 📈 Repository Usage Statistics

### Chart Repositories Used

- **https://actions-runner-controller.github.io/actions-runner-controller**: 1 charts
- **https://airbytehq.github.io/helm-charts**: 1 charts
- **https://airflow.apache.org**: 1 charts
- **https://apache.github.io/superset**: 1 charts
- **https://argoproj.github.io/argo-helm**: 1 charts
- **https://charts.bitnami.com/bitnami**: 3 charts
- **https://charts.gitlab.io/**: 1 charts
- **https://helm.datahubproject.io/**: 2 charts
- **https://helm.elastic.co**: 2 charts
- **https://helm.traefik.io/traefik**: 1 charts
- **https://jupyterhub.github.io/helm-chart/**: 1 charts
- **https://kube-core.github.io/helm-charts**: 1 charts
- **https://lightdash.github.io/helm-charts**: 1 charts
- **https://oauth2-proxy.github.io/manifests**: 1 charts
- **https://operator.min.io/**: 1 charts
- **https://pmint93.github.io/helm-charts**: 1 charts

---

## 🔍 Technical Details

### Analysis Methodology
1. **Chart Collection**: Scanned all Python service files for Helm chart references
2. **Repository Update**: Updated all Helm repositories to latest versions
3. **Chart Download**: Downloaded all identified charts as templates
4. **Dependency Analysis**: Parsed Chart.yaml files to identify dependencies
5. **Bitnami Detection**: Identified dependencies from Bitnami repositories

### Files Analyzed
- `cicd_workload_runner.py`
- `data-cicd-workflows.py`
- `data_analysis.py`
- `data_dcdq_meta_collect.py`
- `data_governance.py`
- `data_modeling.py`
- `data_orchestration.py`
- `data_replication.py`
- `idp_sso_manager.py`
- `object_storage_operator.py`
- `traefik_lb.py`

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
