import os

import ccs_response_planner_backend.rest_api.rest_api as rest_api

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    static_folder_path = os.path.join(script_dir, "..", "build")
    rest_api.start_server(static_folder=static_folder_path, port=8888, num_threads=100, host="127.0.0.1",
                          https=False)
