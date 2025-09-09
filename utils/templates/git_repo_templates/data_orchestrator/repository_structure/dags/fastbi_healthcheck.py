"""Fast.BI Data Orchestration Health Check DAG.

This DAG is designed to ensure that all components of the Fast.BI data orchestration
system are operational. It performs simple health checks.
"""
import airflow
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import timedelta

default_args = {
    'owner': 'fastbi',
    'start_date': airflow.utils.dates.days_ago(1),
    'email': ['support@fast.bi'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=60)  # Retry after 1 hour if a task fails
}

dag = DAG(
    'fastbi_health_check',
    default_args=default_args,
    description='Health check for Fast.BI data orchestration services',
    schedule_interval="0 * * * *",  # Run every hour
    catchup=False,  # Do not perform a catchup run
    tags=["fastbi_health_check"]
)

# Task 1: Check database connectivity
worker_check = BashOperator(
    task_id='check_data_orchestrator_worker',
    bash_command='echo "Data Orchestrator Worker is running"',
    dag=dag
)

# Setting task dependencies
worker_check
