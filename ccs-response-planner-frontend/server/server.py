import logging
import os
import time

import ccs_response_planner_backend.rest_api.rest_api as rest_api
from ccs_response_planner_backend.db.database_facade import DatabaseFacade

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_folder_path = os.path.join(script_dir, "..", "build")
    host = os.environ.get("HOST", "127.0.0.1")

    max_retries = 20
    for attempt in range(1, max_retries + 1):
        try:
            DatabaseFacade.create_tables()
            logger.info("Database tables created successfully")
            break
        except Exception as e:
            if attempt == max_retries:
                raise
            logger.warning(
                "Database not ready (attempt %d/%d): %s",
                attempt, max_retries, e,
            )
            time.sleep(2)

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
    DatabaseFacade.save_user(admin_username, admin_password)
    logger.info("Admin user ensured: %s", admin_username)

    rest_api.start_server(static_folder=static_folder_path, port=8888, num_threads=100, host=host,
                          https=False)
