import time
import random

import egess_api

def destruction_protocol(config_json, node_state, state_lock, this_port):
    """
    Destruction protocol function. It is called with a certain frequency/period specified
    in the all-nodes configuration.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
    """
    
    while True:
        time.sleep(config_json["destruction_check_period"])

        # If the node is already destroyed, it should not process any further and just return.
        with state_lock:
            if node_state["DESTROYED"]:
                return

            if random.random() < config_json["destruction_probability"]:
                print(f"Node {this_port} has been DESTROYED")
                node_state["DESTROYED"] = True
                node_state["SURVEYING"] = False
                node_state["ALARMED"] = False
                node_state["NORMAL"] = False
                egess_api.write_state_change_data_point(this_port, node_state, "DESTROYED")

       