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
# This file implements the pull protocol. The pull protocol requests
# updates from other nodes and receives these updates within the response
# to the request (i.e., within the same session).
# -------------------------------------------------------------------------

import random
import time
import uuid

import egess_api


def _mark_neighbor_unavailable(neighbor_port, config_json, node_state, state_lock, this_port, push_queue):
    neighbor_key = str(neighbor_port)
    attempts = int(node_state["surveying_targets"].get(neighbor_key, 0)) + 1
    node_state["surveying_targets"][neighbor_key] = attempts

    if not node_state["SURVEYING"]:
        node_state["SURVEYING"] = True
        node_state["NORMAL"] = False
        node_state["ALARMED"] = False
        egess_api.write_state_change_data_point(this_port, node_state, "SURVEYING")
        event_id = str(uuid.uuid4())[:8]
        for _neighbor in list(node_state["known_nodes"]):
            push_queue.put(
                {
                    "type": "alarmed_notification",
                    "from": this_port,
                    "forward_count": 0,
                    "event_id": event_id,
                    "origin_time": time.time(),
                }
            )

    if attempts >= int(config_json["surveying_failure_threshold"]):
        print("WARNING: Node {} considered DESTROYED after {} failed attempts".format(neighbor_port, attempts))
        node_state["neighbor_states"][neighbor_key] = {"DESTROYED": True}
        node_state["surveying_targets"].pop(neighbor_key, None)

    if not node_state["surveying_targets"]:
        node_state["SURVEYING"] = False
        node_state["NORMAL"] = True
        for _neighbor in list(node_state["known_nodes"]):
            push_queue.put({"type": "clear_alarmed", "from": this_port})


def request_state_from(neighbor_port, config_json, node_state, state_lock, this_port, push_queue):
    """
    Request the state of a node from another node.

    Args:
        neighbor_port (int): The port of the node to request the state from.
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of the current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        push_queue (queue.Queue): The queue for messages to be pushed to other node(s).
    """
    msg = {
        "type": "state_request",
        "from": this_port,
    }

    with state_lock:
        if node_state["DESTROYED"] or egess_api.effective_crash(node_state):
            return

    response = egess_api.send_msg(config_json, node_state, state_lock, this_port, msg, neighbor_port)
    neighbor_state = response.get("state") if isinstance(response, dict) else None

    if isinstance(neighbor_state, dict):
        with state_lock:
            node_state["neighbor_last_heartbeat"][str(neighbor_port)] = time.time()
            node_state["neighbor_states"][str(neighbor_port)] = neighbor_state
            node_state["surveying_targets"].pop(str(neighbor_port), None)
            if not node_state["surveying_targets"]:
                node_state["SURVEYING"] = False
                node_state["NORMAL"] = True
        return

    with state_lock:
        _mark_neighbor_unavailable(neighbor_port, config_json, node_state, state_lock, this_port, push_queue)


def pull_protocol(config_json, node_state, state_lock, this_port, number_of_nodes, push_queue):
    """
    Pull protocol implementation function.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        number_of_nodes (int): The total number of nodes in the network (if known).
        push_queue (queue.Queue): The queue for messages to be pushed to other node(s).
    """
    del number_of_nodes

    timeout = float(config_json["heartbeat_timeout"])
    now = time.time()

    with state_lock:
        if node_state["DESTROYED"] or egess_api.effective_crash(node_state):
            return
        known = list(node_state["known_nodes"])
        last_seen = dict(node_state["neighbor_last_heartbeat"])
        already_surveying = set(node_state["surveying_targets"].keys())

    for neighbor in known:
        last = last_seen.get(str(neighbor))
        if last is None or (now - last) > timeout:
            if str(neighbor) not in already_surveying:
                request_state_from(neighbor, config_json, node_state, state_lock, this_port, push_queue)

    for neighbor_key in already_surveying:
        with state_lock:
            current_targets = set(node_state["surveying_targets"].keys())
        if neighbor_key in current_targets:
            request_state_from(int(neighbor_key), config_json, node_state, state_lock, this_port, push_queue)

    msg = {
        "op": "pull",
        "from": this_port,
        "data": {},
        "metadata": {},
    }

    with state_lock:
        other_nodes = [neighbor for neighbor in node_state["known_nodes"] if neighbor != this_port]

    if not other_nodes:
        return

    node_sample = random.sample(other_nodes, 1)
    egess_api.send_msg(config_json, node_state, state_lock, this_port, msg, node_sample[0])
