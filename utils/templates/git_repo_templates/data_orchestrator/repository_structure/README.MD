# Data Orchestration Repository for Fast.BI

## Introduction

This repository is an integral part of the fastbi platform, specifically designed for managing and orchestrating data pipelines using Apache Airflow. It includes all necessary Directed Acyclic Graphs (DAGs) that define workflows for efficient and reliable data processing and integration across various services and databases.

## Repository Structure

The repository is organized to ensure systematic arrangement of DAGs, each tailored to specific business needs:

```log
.
data-orchestration-dags/
├── README.md # Repository overview and documentation
├── dags
│   ├── dbt_project_a
│   │   ├── dtb_project_a_dbt_elt_manifest.json # dbt Labs project configuration manifest
│   │   └── k8s_operator_dtb_project_a_dbt_elt_dag.py # DAG for Kubernetes operations
│   ├── dbt_project_b
│   │   ├── dtb_project_b_dbt_elt_manifest.json
│   │   └── k8s_operator_dtb_project_b_dbt_elt_dag.py
│   └── fastbi_healthcheck.py
├── docs
│   └── dag_documentation.md # Detailed documentation for DAG's
└── .gitignore
```

## DAG Configuration

Each DAG directory contains a JSON manifest and a Python script, configuring the orchestration using operators suitable for environments such as Google Kubernetes Engine (GKE), dedicated DBT API Server Operator, or native Kubernetes.

### Automation

The infrastructure of these files supports full automation by FastBI. Configuration specifics are maintained in the dbt_airflow_variables.yml file, ensuring that the DAG setup meets predefined requirements without manual updates.

## Data Transformation (ELT) Technologies

 - **DBT (Data Build Tool):** This open-source tool uses Python and Jinja for data transformation, enabling effective and structured data modeling directly within data warehouses.
 - **Fast.BI Data Modeling Transformation Workload Moderator:** A Python package that visually moderates the DBT project data workload, extracting metadata to construct and present DAGs in real-time.
 - **Fast.BI Data Flow Visualization Packages:** Utilizes unique Fast.BI libraries to visualize the real-time DBT transformation process within the Open-Source Airflow orchestrator.
 - **Fast.BI Data Flow Visualization:** Leverages the open-source Airflow framework to automate the deployment and scheduling of DAGs.
 - **Fast.BI Internal DBT Workload Operator:** Implements the Python KubernetesPodOperator to run DBT project transformations on a shared infrastructure.
 - **Fast.BI External DBT Workload Operator:** Uses the Python Google GKEStartPodOperator to execute DBT project transformations on external infrastructures.
 - **Fast.BI API DBT Workload Operator (Default):** An OpenAPI-based Flask API that acts as an operator for DBT project transformations, with each DBT project having its dedicated API service running on backend machines.

## Contributing

We welcome new ideas and contributions to improve the repository. For more details on contributing or for any inquiries related to Fast.BI's data capabilities, please contact support@fast.bi.

2025 (c)