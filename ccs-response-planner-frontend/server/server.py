import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)

import ccs_response_planner_backend.rest_api.rest_api as rest_api
from ccs_response_planner_backend.constants.constants import (
    DIGITAL_TWIN,
    EXAMPLES,
    EXAMPLES_2,
)
from ccs_response_planner_backend.db.database_facade import DatabaseFacade

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_folder_path = os.path.join(script_dir, "..", "build")

    env_file = os.path.join(script_dir, "..", "..", ".env")
    if os.path.isfile(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
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
    DatabaseFacade.reset_users()
    DatabaseFacade.save_user(admin_username, admin_password)
    logger.info("Admin user ensured: %s", admin_username)

    DatabaseFacade.seed_example_incident(
        name="Incident 1",
        data={
            "system_description": EXAMPLES.SYSTEM_DESCRIPTION,
            "system_description_image": EXAMPLES.SYSTEM_DESCRIPTION_IMAGE,
            "security_alerts": EXAMPLES.SECURITY_ALERTS,
            "operator_feedback": EXAMPLES.OPERATOR_FEEDBACK,
            "specification": EXAMPLES.SPECIFICATION,
            "incident_report": EXAMPLES.INCIDENT_REPORT,
            "response_plan": EXAMPLES.RESPONSE_PLAN,
        },
        dt_config=DIGITAL_TWIN.DEFAULT_CONFIG,
    )
    DatabaseFacade.seed_example_incident(
        name="Incident 2",
        data={
            "system_description": EXAMPLES_2.SYSTEM_DESCRIPTION,
            "system_description_image":
                EXAMPLES_2.SYSTEM_DESCRIPTION_IMAGE,
            "security_alerts": EXAMPLES_2.SECURITY_ALERTS,
            "operator_feedback": EXAMPLES_2.OPERATOR_FEEDBACK,
            "specification": EXAMPLES_2.SPECIFICATION,
            "incident_report": EXAMPLES_2.INCIDENT_REPORT,
            "response_plan": EXAMPLES_2.RESPONSE_PLAN,
        },
        dt_config=DIGITAL_TWIN.INCIDENT_2_CONFIG,
    )
    logger.info("Example incidents seeded")

    rest_api.start_server(
        static_folder=static_folder_path,
        port=8888, num_threads=100,
        host=host, https=False,
    )
