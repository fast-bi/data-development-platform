import psycopg2
import json
import logging
from psycopg2 import sql
from datetime import datetime, timedelta

class DeploymentMetadataCollector:
    def __init__(self, db_config):
        try:
            self.connection = psycopg2.connect(**db_config)
            self.connection.autocommit = True
            self.infra_service_table = 'infra_service_deployments'
            self.customer_table = 'customers_deployments'
            self.user_token_table = 'authentication_tokens'
            self.versions_table = 'helm_chart_versions'
            self.ensure_infra_service_table_exists()
            self.ensure_data_service_table_exists()
            self.ensure_tokens_table_exists()
            self.ensure_versions_table_exists()
            logging.info("Database connection established and tables ensured.")
        except psycopg2.Error as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    def ensure_infra_service_table_exists(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id SERIAL PRIMARY KEY,
                        customer VARCHAR(255) NOT NULL,
                        customer_main_domain VARCHAR(255),
                        customer_vault_slug VARCHAR(255),
                        deployment_environment VARCHAR(255),
                        deployment_name JSON,
                        chart_name JSON,
                        chart_version JSON,
                        app_name JSON,
                        app_version JSON,
                        deploy_date DATE
                    );
                """).format(table=sql.Identifier(self.infra_service_table))
                cur.execute(query)
                logging.info(f"Table {self.infra_service_table} ensured.")
        except psycopg2.Error as e:
            logging.error(f"Error ensuring infra_service_table: {e}")
            raise

    def ensure_data_service_table_exists(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id SERIAL PRIMARY KEY,
                        customer VARCHAR(255) NOT NULL,
                        stage_id INT,
                        stage VARCHAR(255),
                        session_data JSON NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """).format(table=sql.Identifier(self.customer_table))
                cur.execute(query)
                logging.info(f"Table {self.customer_table} ensured.")
        except psycopg2.Error as e:
            logging.error(f"Error ensuring data_service_table: {e}")
            raise

    def ensure_tokens_table_exists(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id SERIAL PRIMARY KEY,
                        token_key VARCHAR(255) UNIQUE NOT NULL,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        expiry BIGINT,
                        status VARCHAR(50) DEFAULT 'ACTIVE',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """).format(table=sql.Identifier(self.user_token_table))
                cur.execute(query)
                logging.info(f"Table {self.user_token_table} ensured with status column.")
        except psycopg2.Error as e:
            logging.error(f"Error ensuring tokens table: {e}")
            raise

    def ensure_versions_table_exists(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id SERIAL PRIMARY KEY,
                        category VARCHAR(50) NOT NULL,
                        chart_name VARCHAR(255) NOT NULL,
                        version VARCHAR(255) NOT NULL,
                        tag VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """).format(table=sql.Identifier(self.versions_table))
                cur.execute(query)
                logging.info(f"Table {self.versions_table} ensured.")
        except psycopg2.Error as e:
            logging.error(f"Error ensuring versions table: {e}")
            raise

    def add_deployment_record(self, record):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    INSERT INTO {table} (
                        customer, 
                        customer_main_domain, 
                        customer_vault_slug, 
                        deployment_environment, 
                        deployment_name, 
                        chart_name, 
                        chart_version, 
                        app_name, 
                        app_version, 
                        deploy_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """).format(table=sql.Identifier(self.infra_service_table))

                deployment_name_json = json.dumps({"single_service": record['deployment_name']}) if isinstance(record['deployment_name'], str) else json.dumps({"multi_services": record['deployment_name']})
                chart_name_json = json.dumps({"single_service": record['chart_name']}) if isinstance(record['chart_name'], str) else json.dumps({"multi_services": record['chart_name']})
                chart_version_json = json.dumps({"single_service": record['chart_version']}) if isinstance(record['chart_version'], str) else json.dumps({"multi_services": record['chart_version']})
                app_name_json = json.dumps({"single_service": record['app_name']}) if isinstance(record['app_name'], str) else json.dumps({"multi_services": record['app_name']})
                app_version_json = json.dumps({"single_service": record['app_version']}) if isinstance(record['app_version'], str) else json.dumps({"multi_services": record['app_version']})

                cur.execute(query, (
                    record['customer'],
                    record['customer_main_domain'],
                    record['customer_vault_slug'],
                    record['deployment_environment'],
                    deployment_name_json,
                    chart_name_json,
                    chart_version_json,
                    app_name_json,
                    app_version_json,
                    record['deploy_date']
                ))
                logging.info(f"Added deployment record for customer {record['customer']}.")
        except psycopg2.Error as e:
            logging.error(f"Error adding deployment record: {e}")
            raise  # Re-raise the exception to be caught by the Flask error handler

    def save_session_data(self, customer, stage_id, stage, session_data):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    INSERT INTO {table} (customer, stage_id, stage, session_data)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """).format(table=sql.Identifier(self.customer_table))
                cur.execute(query, (customer, stage_id, stage, json.dumps(session_data)))
                session_id = cur.fetchone()[0]
                logging.info(f"Saved session data for customer {customer}, session ID: {session_id}.")
                return session_id
        except psycopg2.Error as e:
            logging.error(f"Error saving session data: {e}")
            raise

    def retrieve_session_data(self, customer, stage_id):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    SELECT session_data FROM {table}
                    WHERE customer = %s AND stage_id = %s ORDER BY created_at DESC LIMIT 1;
                """).format(table=sql.Identifier(self.customer_table))
                cur.execute(query, (customer, stage_id))
                result = cur.fetchone()
                if result:
                    logging.info(f"Retrieved session data for customer {customer}, stage ID: {stage_id}.")
                    return json.loads(result[0]) if isinstance(result[0], str) else result[0]
                else:
                    logging.warning(f"No session data found for customer {customer}, stage ID: {stage_id}.")
                    return None
        except psycopg2.Error as e:
            logging.error(f"Error retrieving session data: {e}")
            raise

    def save_token(self, token_key, access_token, refresh_token, expiry):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    INSERT INTO {table} (token_key, access_token, refresh_token, expiry)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (token_key) DO UPDATE
                    SET access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        expiry = EXCLUDED.expiry,
                        created_at = CURRENT_TIMESTAMP
                """).format(table=sql.Identifier(self.user_token_table))
                cur.execute(query, (token_key, access_token, refresh_token, expiry))
            logging.info(f"Saved token with key: {token_key}")
        except psycopg2.Error as e:
            logging.error(f"Error saving token: {e}")
            raise

    def get_access_token(self, token_key):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    SELECT access_token, refresh_token, expiry FROM {table}
                    WHERE token_key = %s
                """).format(table=sql.Identifier(self.user_token_table))
                cur.execute(query, (token_key,))
                result = cur.fetchone()
                if result:
                    logging.info(f"Retrieved token data for key: {token_key}")
                    return result
                else:
                    logging.warning(f"No token data found for key: {token_key}")
                    return None
        except psycopg2.Error as e:
            logging.error(f"Error retrieving token data: {e}")
            raise

    def delete_old_tokens(self, days_old=1):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    DELETE FROM {table}
                    WHERE created_at < NOW() - INTERVAL %s DAY
                """).format(table=sql.Identifier(self.user_token_table))
                cur.execute(query, (days_old,))
                deleted_count = cur.rowcount
            logging.info(f"Deleted {deleted_count} tokens older than {days_old} days")
        except psycopg2.Error as e:
            logging.error(f"Error deleting old tokens: {e}")
            raise

    def mark_token_as_used(self, token_key):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    UPDATE {table}
                    SET access_token = 'USED',
                        refresh_token = 'USED',
                        status = 'USED',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE token_key = %s
                    RETURNING id
                """).format(table=sql.Identifier(self.user_token_table))
                cur.execute(query, (token_key,))
                result = cur.fetchone()
                
                if result:
                    logging.info(f"Token with key {token_key} marked as used.")
                    return result[0]  # Return the ID of the updated record
                else:
                    logging.warning(f"No token found with key: {token_key}")
                    return None
        except psycopg2.Error as e:
            logging.error(f"Error marking token as used: {e}")
            raise

    def update_current_helm_chart_service_versions(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    UPDATE {table}
                    SET tag = 'Previous'
                    WHERE tag = 'Latest';
                """).format(table=sql.Identifier(self.versions_table))
                cur.execute(query)
                updated_count = cur.rowcount
                logging.info(f"Updated {updated_count} records from Latest to Previous.")
                return True
        except psycopg2.Error as e:
            logging.error(f"Error updating current versions: {e}")
            return False

    def insert_latest_helm_chart_service_versions(self, versions_data):
        try:
            with self.connection.cursor() as cur:
                for category, services in versions_data.items():
                    for service, data in services.items():
                        query = sql.SQL("""
                            INSERT INTO {table} (category, chart_name, version, tag)
                            VALUES (%s, %s, %s, %s);
                        """).format(table=sql.Identifier(self.versions_table))
                        cur.execute(query, (category, data['name'], data['version'], 'Latest'))
                logging.info("Inserted new latest versions.")
                return True
        except psycopg2.Error as e:
            logging.error(f"Error inserting latest versions: {e}")
            return False

    def delete_old_versions(self):
        try:
            nine_months_ago = datetime.utcnow() - timedelta(days=270)
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    DELETE FROM {table}
                    WHERE created_at < %s;
                """).format(table=sql.Identifier(self.versions_table))
                cur.execute(query, (nine_months_ago,))
                deleted_count = cur.rowcount
                logging.info(f"Deleted {deleted_count} records older than 9 months.")
                return True
        except psycopg2.Error as e:
            logging.error(f"Error deleting old versions: {e}")
            return False

    def get_latest_versions(self):
        try:
            with self.connection.cursor() as cur:
                query = sql.SQL("""
                    SELECT category, chart_name, version, tag
                    FROM {table}
                    WHERE tag in ('Latest', 'Current', 'Previous')
                    ORDER BY category, chart_name, 
                        CASE 
                            WHEN tag = 'Current' THEN 1
                            WHEN tag = 'Latest' THEN 2
                            WHEN tag = 'Previous' THEN 3
                            ELSE 4
                        END;
                """).format(table=sql.Identifier(self.versions_table))
                cur.execute(query)
                results = cur.fetchall()
                
                versions_data = {
                    "system_infra_services": {},
                    "data_services": {},
                    "fastbi_data_services": {}
                }
                
                for category, chart_name, version, tag in results:
                    if category not in versions_data:
                        versions_data[category] = {}
                    if chart_name not in versions_data[category]:
                        versions_data[category][chart_name] = {
                            "name": chart_name,
                            "versions": []
                        }
                    versions_data[category][chart_name]["versions"].append({
                        "version": version,
                        "tag": tag
                    })
                
                return versions_data
        except psycopg2.Error as e:
            logging.error(f"Error retrieving latest versions: {e}")
            return None
