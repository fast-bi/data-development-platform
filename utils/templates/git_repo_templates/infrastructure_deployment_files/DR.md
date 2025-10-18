# 🚨 Fast.BI Disaster Recovery (DR)

A practical runbook to restore the Fast.BI Data Development Platform after a Kubernetes cluster loss.

This guide assumes familiarity with Kubernetes, Helm, Velero, and StackGres.

---

## ✅ Prerequisites

- Access to cloud project(s) and buckets that store backups (e.g., GCS or S3/MinIO)
- Access to Git repository with deployment manifests and Helm values
- Workstation with: kubectl, helm, velero, gcloud/gsutil (if GCS), yq/jq
- Cluster admin permissions on the new Kubernetes cluster
- Network access to External Secrets backends (e.g., Vault)

---

## 🔍 1) Verify Backups Were Enabled Before DR

Backups for the global PostgreSQL must be enabled and stored in external object storage. In `stackgres_postgres_db/values_extra.yaml` confirm:

- SGObjectStorage is configured for external storage (e.g., GCS)
- Backups schedule exists and retention is set
- Backups reference the external object storage

Example (already present):

```yaml
configurations:
  backups:
  - compression: lz4
    cronSchedule: 0 5 * * *
    fastVolumeSnapshot: false
    retention: 5
    sgObjectStorage: gcsbucket
    useVolumeSnapshot: false
```

Also ensure object storage credentials are valid and reachable (e.g., `gcsbucket` with service account JSON in a Secret, or MinIO/S3 credentials via ExternalSecrets).

If you used only in-cluster MinIO previously, move to external storage for resilience.

---

## 🧰 2) Velero Strategy (Kubernetes resources metadata)

Velero is not installed by default in this repo; manifests are provided under `k8s-data-platform-services-deployment/data_platform_backup/`. You must install Velero yourself in the new cluster and configure it to the same backup location used previously.

Purpose: restore namespaces and Kubernetes objects’ metadata (Deployments, Services, ConfigMaps, Secrets metadata, etc.). With Vault + External Secrets, restore Vault first to regain secrets, then restore or redeploy workloads.

### Install Velero (GCP example)

```bash
# Set these first
export VELERO_BUCKET=<your-velero-bucket>
export VELERO_PROJECT=<your-gcp-project>
export VELERO_SA_JSON=$(pwd)/credentials-velero

# credentials-velero is a GCP service account JSON with access to the bucket
velero install \
  --provider gcp \
  --plugins velero/velero-plugin-for-gcp:v1.12.2 \
  --bucket ${VELERO_BUCKET} \
  --secret-file ${VELERO_SA_JSON} \
  --backup-location-config bucket=${VELERO_BUCKET},project=${VELERO_PROJECT} \
  --use-volume-snapshots=false \
  -n platform-backup
```

### Install Velero (S3/MinIO example)

```bash
# Set these first
export VELERO_BUCKET=<your-bucket>
export VELERO_REGION=<your-region>
export VELERO_S3_URL=<http://minio.minio.svc.cluster.local:9000>
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Create credentials file
cat > credentials-velero <<EOF
[default]
aws_access_key_id=${AWS_ACCESS_KEY_ID}
aws_secret_access_key=${AWS_SECRET_ACCESS_KEY}
EOF

velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.12.2 \
  --bucket ${VELERO_BUCKET} \
  --backup-location-config region=${VELERO_REGION},s3ForcePathStyle=true,s3Url=${VELERO_S3_URL} \
  --secret-file ./credentials-velero \
  --use-volume-snapshots=false \
  -n platform-backup
```

### Restore Vault first (example)

```bash
velero restore create restore-vault \
  --from-backup <your_latest_backup> \
  --include-namespaces vault \
  -n platform-backup \
  --wait
```

After Vault is restored and External Secrets are functional, proceed to other namespaces as needed (see Section 7).

---

## 🧭 3) High-Level DR Flow

1. Provision a new Kubernetes cluster (same or compatible version/size)
2. Install cluster fundamentals (Ingress, DNS, storage classes, CNI, etc.)
3. Install Velero configured to the original backup storage
4. Restore the `vault` namespace via Velero and unseal/login as needed (Found in Secrets)
5. Install StackGres Operator (`stackgres_postgres_db/values.yaml`)
6. Restore the global PostgreSQL data using StackGres (metadata.json + restore manifest)
7. Restore critical namespaces (e.g., `minio`, `data-governance`, `data-modeling`) using Velero snapshots; redeploy others via GitOps/Helm
8. Validate: apps running, pipelines functional, users can login

---

## 🧱 4) Install StackGres Operator

Use the same chart and values you used initially, found in `stackgres_postgres_db/values.yaml`.

```bash
helm repo add stackgres https://stackgres.io/downloads/stackgres-k8s/stackgres/helm/
helm repo update
helm upgrade --install stackgres-operator stackgres/stackgres-operator \
  -n stackgres --create-namespace \
  -f stackgres_postgres_db/values.yaml
```

Wait until the operator, REST API, and Admin UI are ready.

---

## 📦 5) Locate and Prepare Postgres Backup Artifacts

In your backup bucket, locate the StackGres backup metadata (e.g., `metadata.json`). Two example files are present in `stackgres_postgres_db/` to guide you:

- `metadata.json_example`
- `restore_backup.yaml_example`

### Discover backups in GCS (example)

```bash
# List objects under your StackGres backup bucket/prefix
# Adjust BUCKET and PREFIX as per your environment
export BUCKET=gs://fastbi-terasky-global-backup
export PREFIX=stackgres/fastbi-global-psql

gsutil ls -r ${BUCKET}/${PREFIX}/ | sed 's#gs://##'

# Fetch a metadata.json locally
gsutil cp ${BUCKET}/${PREFIX}/<backup-id>/metadata.json ./metadata.json
```

Steps:
- Download the latest `metadata.json` from the bucket
- Fill `restore_backup.yaml` based on `metadata.json` (backup name/path)
- Apply the `restore_backup.yaml` to declare the backup in the cluster, if required by your workflow

---

## 🗃️ 6) Restore the Global PostgreSQL Cluster

Edit `stackgres_postgres_db/values_extra.yaml` before applying:

- Remove the `managedSql` section (if present)
- Add initial restore directives to SGCluster:

```yaml
initialData:
  restore:
    fromBackup:
      name: recovered-backup
```

Where `recovered-backup` is the resource name you define that references the backup located in object storage.

### Example: restore_backup.yaml (skeleton)

```yaml
apiVersion: stackgres.io/v1
kind: SGBackup
metadata:
  name: recovered-backup
  namespace: global-postgresql
spec:
  sgCluster: fastbi-global-psql
  storage:
    sgObjectStorage: gcsbucket
  # If your metadata requires additional fields (e.g., path), include them here based on metadata.json
```

Apply the restore resources and then the cluster values:

```bash
kubectl apply -f stackgres_postgres_db/restore_backup.yaml   # your filled file
kubectl apply -f stackgres_postgres_db/values_extra.yaml
```

Monitor the restore until the cluster becomes Ready. Confirm databases and roles exist as expected.

---

## ♻️ 7) Restore Namespaces with Velero

With Postgres ready and Vault/External Secrets working, restore additional namespaces:

- `minio` (object storage with user data)
- `data-governance`
- `data-modeling`

These namespaces may contain user data and should be restored from backups/snapshots if you need exact state.

Example (adjust backup names and namespaces):

```bash
velero restore create restore-minio \
  --from-backup <your_latest_backup> \
  --include-namespaces minio \
  -n platform-backup \
  --wait

velero restore create restore-data-governance \
  --from-backup <your_latest_backup> \
  --include-namespaces data-governance \
  -n platform-backup \
  --wait

velero restore create restore-data-modeling \
  --from-backup <your_latest_backup> \
  --include-namespaces data-modeling \
  -n platform-backup \
  --wait
```

Other namespaces that keep their state inside the global Postgres cluster can be redeployed from Git/Helm (or restored via Velero if you prefer an exact state restore).

---

## 🚀 8) Restore All Other Services

After restoring critical namespaces (`vault`, `minio`, `data-governance`, `data-modeling`), restore all remaining services using Velero:

```bash
velero restore create restore-all-except \
  --from-backup <your_latest_backup> \
  --exclude-namespaces vault,minio,data-governance,data-modeling \
  -n platform-backup \
  --wait
```

This will restore all other namespaces including:
- **Infrastructure Services:**
  - `cert-manager` - SSL certificate management
  - `external-dns` - DNS record management
  - `traefik` - Load balancer and ingress
  - `monitoring` - Prometheus, Grafana, logging
  - `cluster-cleaner` - Resource cleanup
  - `idp-sso-manager` - SSO management
  - `cluster-pvc-autoscaler` - Storage management

- **Data Platform Services:**
  - `cicd-workload-runner` - CI/CD pipeline runners
  - `data-cicd-workflows` - Workflow definitions
  - `data-replication` - Data replication services
  - `data-orchestration` - Apache Airflow
  - `data-dcdq-meta-collect` - Data quality and metadata
  - `data-analysis` - BI platform (Superset/Lightdash)
  - `user-console` - User interface

### Alternative: Selective Service Restoration

If you prefer to restore specific services individually:

```bash
# Restore infrastructure services
velero restore create restore-infrastructure \
  --from-backup <your_latest_backup> \
  --include-namespaces cert-manager,external-dns,traefik,stackgres,monitoring \
  -n platform-backup \
  --wait

# Restore data platform services
velero restore create restore-data-platform \
  --from-backup <your_latest_backup> \
  --include-namespaces cicd-workload-runner,object-storage-operator,data-cicd-workflows,data-replication,data-orchestration,data-analysis,user-console \
  -n platform-backup \
  --wait
```

### Manual Service Deployment (Alternative)

If Velero restore fails for some services, you can manually redeploy using Helm:

```bash
# Example for data orchestration (Airflow)
helm upgrade --install data-orchestration ./k8s-data-platform-services-deployment/data_orchestration \
  -n data-orchestration --create-namespace \
  -f ./k8s-data-platform-services-deployment/data_orchestration/values.yaml

# Example for data analysis (Superset)
helm upgrade --install data-analysis ./k8s-data-platform-services-deployment/data_analysis \
  -n data-analysis --create-namespace \
  -f ./k8s-data-platform-services-deployment/data_analysis/values.yaml
```

Ensure ExternalSecrets are synced and services can connect to global Postgres before proceeding to validation.

---

## 🔎 9) Validation & Smoke Tests

- Confirm Vault is unsealed and secrets are syncing
- Check `SGCluster` is Ready, and verify databases/roles
- Verify `minio`, `data-governance`, `data-modeling` applications are healthy
- Run smoke tests: login to UI(s), trigger a small pipeline in Airflow/Argo, test dbt, confirm DataHub connectivity

---

## 💡 10) Tips & Notes

- Prefer external object storage (e.g., GCS) over in-cluster MinIO for backups
- Keep service account keys for buckets in a separate DR project with limited IAM
- Periodically test restore steps in a staging cluster
- Record the exact backup name/time used for restore in your incident notes

---

## 📚 References

- Fast.BI Data Development Platform - GCP Deployment Guide: [wiki.fast.bi — Google Cloud Deployment Guide](https://wiki.fast.bi/en/User-Guide/Data-Platform-Deployment/Google-Cloud)
