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
# This file implements the push protocol of the node. The push protocol
# sends the message from the push queue to other nodes.
# -------------------------------------------------------------------------

import copy

import egess_api


def push_protocol(config_json, node_state, state_lock, this_port, number_of_nodes, push_queue, msg):
    """
    This function implements the push protocol for a message taken from the push queue.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        number_of_nodes (int): The total number of nodes in the network (if known).
        push_queue (queue.Queue): The queue for messages to be pushed to other node(s).
        msg (dict[str, Any]): The message (in JSON format) to be pushed.
    """
    del number_of_nodes, push_queue

    with state_lock:
        if node_state["DESTROYED"] or egess_api.effective_crash(node_state):
            egess_api.append_recent_msg(node_state, "drop:push local_unavailable")
            return
        node_sample = copy.copy(node_state["known_nodes"])

    for target_port in node_sample:
        egess_api.send_msg(config_json, node_state, state_lock, this_port, msg, target_port)
        print("MESSAGE FORWARDED {} {}\n".format(str(this_port), str(target_port)))

    with state_lock:
        if not node_state["SURVEYING"] and not node_state["DESTROYED"]:
            if not node_state["NORMAL"]:
                node_state["NORMAL"] = True
                egess_api.write_state_change_data_point(this_port, node_state, "NORMAL")
            else:
                node_state["NORMAL"] = True
