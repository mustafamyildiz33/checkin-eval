# EGESS - Experimental Gear for Evaluation of Swarm Systems
# Copyright (C) 2026  Nick Ivanov and ACSUS Lab <ivanov@rowan.edu>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# -------------------------------------------------------------------------
# This file contains the background protocol of the node. The background
# protocol is running by itself and is not directly triggered by messages
# or queues.
# -------------------------------------------------------------------------

import time

import egess_api


def background_protocol(config_json, node_state, state_lock, this_port, number_of_nodes, push_queue):
    """
    Background protocol function. It is called with a certain frequency/period specified
    in the all-nodes configuration.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        number_of_nodes (int): The total number of nodes in the network (if known).
        push_queue (queue.Queue): The queue for messages to be pushed to other node(s).
    """
    del number_of_nodes

    with state_lock:
        if node_state["DESTROYED"] or egess_api.effective_crash(node_state):
            return

        node_state["heartbeat_counter"] = int(node_state.get("heartbeat_counter", 0)) + 1
        heartbeat_counter = int(node_state["heartbeat_counter"])
        lie_messages = []

        faults = egess_api.ensure_faults(node_state)
        runtime = node_state.get("fault_runtime", {})
        if not isinstance(runtime, dict):
            runtime = {}

        if faults.get("lie_sensor", False):
            period_sec = max(1, int(faults.get("period_sec", 4)))
            slot = int(time.time() // period_sec)
            if runtime.get("lie_sensor_slot") != slot:
                runtime["lie_sensor_slot"] = slot
                lie_event_id = "lie-{}-{}".format(this_port, slot)
                lie_messages.append(
                    {
                        "type": "alarmed_notification",
                        "from": this_port,
                        "forward_count": 0,
                        "event_id": lie_event_id,
                        "origin_time": time.time(),
                    }
                )
                egess_api.write_data_point(this_port, "lie_sensor_emit", lie_event_id)
                egess_api.append_recent_msg(node_state, "lie_sensor_emit:{}".format(lie_event_id))
        node_state["fault_runtime"] = runtime

        heartbeat_msg = {
            "type": "heartbeat",
            "from": this_port,
            "counter": heartbeat_counter,
            "state": {
                "ALARMED": node_state["ALARMED"],
                "SURVEYING": node_state["SURVEYING"],
                "DESTROYED": node_state["DESTROYED"],
                "NORMAL": node_state["NORMAL"],
            },
            "metadata": {
                "timestamp": time.time(),
            },
        }

    egess_api.log_current_node_state(this_port, node_state)
    push_queue.put(heartbeat_msg)
    for lie_msg in lie_messages:
        push_queue.put(lie_msg)
