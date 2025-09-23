# DBT Projects Directory

## Overview
This directory contains [dbt (data build tool)](https://www.getdbt.com/) projects that are executed via Apache Airflow's BashOperator. DBT is a transformation workflow tool that enables analytics engineers to transform data in their warehouses by writing, documenting, and executing SQL.

## Directory Structure
```
dags/
└── dbt/
    ├── project-A/
    ├── project-B/
    └── ...
```

## About DBT
DBT (data build tool) is a modern data transformation tool that lets you:
- Write data transformations using SQL SELECT statements
- Version control your data transformations
- Test your data transformations
- Document your data pipeline
- Manage dependencies between data models
- Create a directed acyclic graph (DAG) of model dependencies

### Key Features
- **Modularity**: Write reusable SQL models
- **Version Control**: Track changes to your data transformations
- **Testing & Documentation**: Ensure data quality and maintain documentation
- **Incremental Models**: Efficiently update your models with only new data
- **Templating**: Use Jinja templating for dynamic SQL generation

## Usage
Each project folder should contain:
- `dbt_project.yml`: Project configuration file
- `models/`: Directory containing SQL transformation files
- `macros/`: (Optional) Custom macros for reusable SQL logic
- `tests/`: (Optional) Custom data tests
- `profiles.yml`: Connection configuration (usually stored outside the project)

## Best Practices
1. Keep each dbt project isolated and focused on a specific data domain
2. Use meaningful project names that reflect their purpose
3. Follow dbt's recommended project structure
4. Include appropriate documentation and tests
5. Maintain separate profiles for development and production

## Note
Ensure that dbt is properly installed and configured in your Airflow environment before running any dbt commands via BashOperator.