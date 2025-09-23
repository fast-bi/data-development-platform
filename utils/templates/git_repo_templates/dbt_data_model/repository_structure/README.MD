# dbt Data Repository for Fast.BI

## Introduction

Welcome to the dbt Data Repository, an integral component of Fast.BI's "One Data Analysis Platform". This repository serves as the central hub for all dbt projects within the Fast.BI ecosystem, facilitating effective data transformation workflows essential for advanced data modeling and insight extraction.

Fast.BI leverages a suite of powerful open-source tools, integrated through a streamlined microservices architecture, enabling users to quickly engage in data modeling without the complexities of infrastructure management.

## Repository Structure

Each dbt project is organized within its own directory in the `dbt_projects` folder, ensuring clear separation and systematic organization of data modeling projects designed to meet specific business requirements.

```log
.
dbt-data-models/
├── README.md
├── dbt_project_a
│   ├── README.md
│   ├── analyses
│   ├── dbt_airflow_variables.yml
│   ├── dbt_project.yml
│   ├── macros
│   │   └── generate_columns_from_airbyte_yml.sql
│   ├── models
│   │   ├── marts
│   │   │   ├── marts_a
│   │   │   │   ├── mart_model_aa.sql
│   │   │   │   └── mart_model_aa.yml
│   │   │   └── marts_b
│   │   │       ├── mart_model_ab.sql
│   │   │       └── mart_model_ab.yml
│   │   ├── source.yml
│   │   └── staging
│   │       ├── sta_a_model.sql
│   │       └── sta_a_model.sql
│   ├── packages.yml
│   ├── profiles.yml
│   ├── seeds
│   ├── snapshots
│   ├── tests
│   └── yamllint-config.yaml
├── dbt_project_b
│   ├── README.md
│   ├── analyses
│   ├── dbt_airflow_variables.yml
│   ├── dbt_project.yml
│   ├── macros
│   │   └── generate_columns_from_airbyte_yml.sql
│   ├── models
│   │   ├── marts
│   │   │   ├── marts_a
│   │   │   │   ├── mart_model_bb.sql
│   │   │   │   └── mart_model_bb.yml
│   │   │   └── marts_b
│   │   │       ├── mart_model_bc.sql
│   │   │       └── mart_model_bc.yml
│   │   ├── source.yml
│   │   └── staging
│   │       ├── sta_b_model.sql
│   │       └── sta_b_model.sql
│   ├── packages.yml
│   ├── profiles.yml
│   ├── seeds
│   ├── snapshots
│   ├── tests
│   └── yamllint-config.yaml
├── .gitignore
└── .gitlab-ci.yml
```

## Project Configuration

Each project directory contains a `dbt_airflow_variables.yml` configuration file. This file sets up the project for orchestration using operators, tailored for Google Kubernetes Engine (GKE), dedicated DBT API Server Operator (API), or native Kubernetes operator (k8s).

### Configuration

#### Navigate User Console - Data Project Initialization

Choose one of the following operators for project initialization:

- **Kubernetes Pod Operator**
- **Google Kubernetes Pod Operator**
- **API Server Operator**

### Supported Variables Documentation

All supported variables for dbt projects are documented comprehensively on our wiki at [Fast.BI Wiki - Data Model CI/CD Variables](https://wiki.fast.bi/en/User-Guide/data_model_cicd_variables).

## CI/CD Integration

This repository integrates with CI/CD pipelines to automate the compilation and deployment of dbt projects via Data Orchestrator DAGs.

**Important:** Do not update the `.gitlab-ci.yml` file as it is essential for running the pipelines.

## Contributing

Contributions to the dbt Data Repository are encouraged. Please adhere to the guidelines and configuration requirements specified above to ensure consistency and functionality across all dbt projects.

For more information on contributing to this repository or general inquiries about Fast.BI's data capabilities, please contact [support@fast.bi](mailto:support@fast.bi).

2025 (c)