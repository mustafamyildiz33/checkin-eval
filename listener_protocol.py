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
# This file implements the listener protocol of the node. This protocol
# is triggered each time the node receives a message (in JSON format).
# -------------------------------------------------------------------------

import copy
import time

from flask import jsonify

import egess_api


def _touch_msg_telemetry(node_state):
    counters = node_state.get("msg_counters", {})
    if not isinstance(counters, dict):
        counters = {}
    defaults = {
        "pull_rx": 0,
        "push_rx": 0,
        "pull_tx": 0,
        "push_tx": 0,
        "pull_rx_bytes": 0,
        "push_rx_bytes": 0,
        "pull_tx_bytes": 0,
        "push_tx_bytes": 0,
        "rx_total_bytes": 0,
        "tx_total_bytes": 0,
        "tx_ok": 0,
        "tx_fail": 0,
        "tx_timeout": 0,
        "tx_conn_error": 0,
    }
    for key, value in defaults.items():
        try:
            counters[key] = int(counters.get(key, value))
        except Exception:
            counters[key] = int(value)
    node_state["msg_counters"] = counters

    events = node_state.get("recent_msgs", [])
    if not isinstance(events, list):
        events = []
    node_state["recent_msgs"] = events
    return counters, events


def _add_recent_msg(node_state, message):
    _, events = _touch_msg_telemetry(node_state)
    events.append("[{}] {}".format(time.strftime("%H:%M:%S"), str(message)))
    if len(events) > 60:
        del events[:-60]


def _is_observer_pull(msg):
    metadata = msg.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    origin = str(metadata.get("origin", msg.get("from", ""))).strip().lower()
    return origin in ("bootstrap", "paper_report", "paper_history", "paper_eval", "viz")


def _protocol_state_label(node_state):
    if node_state.get("DESTROYED", False):
        return "DESTROYED"
    if node_state.get("SURVEYING", False):
        return "SURVEYING"
    if node_state.get("ALARMED", False):
        return "ALARMED"
    if node_state.get("NORMAL", False):
        return "NORMAL"
    return "UNKNOWN"


def _record_inbound_msg(node_state, msg):
    if str(msg.get("op", "")).strip().lower() == "pull" and _is_observer_pull(msg):
        return
    msg_size_bytes = egess_api.serialized_size_bytes(msg)
    counters, _ = _touch_msg_telemetry(node_state)
    msg_kind = str(msg.get("op", ""))
    if msg_kind == "pull":
        counters["pull_rx"] = int(counters.get("pull_rx", 0)) + 1
        counters["pull_rx_bytes"] = int(counters.get("pull_rx_bytes", 0)) + int(msg_size_bytes)
    else:
        counters["push_rx"] = int(counters.get("push_rx", 0)) + 1
        counters["push_rx_bytes"] = int(counters.get("push_rx_bytes", 0)) + int(msg_size_bytes)
    counters["rx_total_bytes"] = int(counters.get("rx_total_bytes", 0)) + int(msg_size_bytes)

    label = str(msg.get("op", msg.get("type", "unknown")))
    source = msg.get("from", msg.get("metadata", {}).get("origin", "unknown"))
    _add_recent_msg(node_state, "rx:{} <- {} bytes={}".format(label, source, msg_size_bytes))


def _reset_runtime_state(node_state):
    node_state["ALARMED"] = False
    node_state["SURVEYING"] = False
    node_state["DESTROYED"] = False
    node_state["NORMAL"] = True
    node_state["ON_FIRE"] = False
    node_state["fire_arrival_time"] = None
    node_state["surveying_targets"] = {}
    node_state["neighbor_states"] = {}
    node_state["seen_alarm_events"] = []

    now = float(time.time())
    last_heartbeat = node_state.get("neighbor_last_heartbeat", {})
    if not isinstance(last_heartbeat, dict):
        last_heartbeat = {}
    for neighbor in node_state.get("known_nodes", []):
        last_heartbeat[str(neighbor)] = now
    node_state["neighbor_last_heartbeat"] = last_heartbeat

    faults = egess_api.ensure_faults(node_state)
    faults["crash_sim"] = False
    faults["lie_sensor"] = False
    faults["flap"] = False
    node_state["fault_runtime"] = {}


def _apply_injected_state(node_state, requested_state):
    state = str(requested_state).strip().upper()
    if state == "DESTROYED":
        node_state["DESTROYED"] = True
        node_state["NORMAL"] = False
        node_state["ALARMED"] = False
        node_state["SURVEYING"] = False
    elif state == "ALARMED":
        node_state["DESTROYED"] = False
        node_state["NORMAL"] = False
        node_state["ALARMED"] = True
        node_state["SURVEYING"] = False
    elif state == "SURVEYING":
        node_state["DESTROYED"] = False
        node_state["NORMAL"] = False
        node_state["ALARMED"] = False
        node_state["SURVEYING"] = True
    else:
        _reset_runtime_state(node_state)
        state = "NORMAL"

    if state != "DESTROYED":
        node_state["ON_FIRE"] = False
        node_state["fire_arrival_time"] = None
    return state


def _control_receipt(message, **extra):
    data = {"success": True, "message": message}
    data.update(extra)
    return {
        "op": "receipt",
        "data": data,
        "metadata": {},
    }


def listener_protocol(config_json, node_state, state_lock, this_port, number_of_nodes, push_queue, msg):
    """
    Listener protocol function.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        number_of_nodes (int): The total number of nodes in the network (if known).
        push_queue (queue.Queue): The queue for messages to be pushed to other node(s).
        msg (dict[str, Any]): JSON object received via POST protocol.
    """
    del number_of_nodes

    if not isinstance(msg, dict):
        return {
            "op": "receipt",
            "data": {"success": False, "message": "message_not_dict"},
            "metadata": {},
        }

    op = str(msg.get("op", "")).strip()

    # Control hooks are handled before DESTROYED/crash gates so the runner can
    # recover a node even while it is intentionally unavailable.
    if op == "inject_fault":
        data = msg.get("data", {})
        if not isinstance(data, dict):
            data = {}
        fault = str(data.get("fault", "")).strip().lower()
        enable = bool(data.get("enable", True))
        period_sec = int(data.get("period_sec", 4))
        with state_lock:
            faults = egess_api.ensure_faults(node_state)
            faults["period_sec"] = max(1, period_sec)
            if fault == "reset":
                _reset_runtime_state(node_state)
                _add_recent_msg(node_state, "control:reset")
                return _control_receipt("faults_reset", protocol_state=_protocol_state_label(node_state))
            if fault in ("crash_sim", "lie_sensor", "flap"):
                faults[fault] = enable
                node_state["fault_runtime"] = node_state.get("fault_runtime", {})
                _add_recent_msg(node_state, "control:{}={}".format(fault, enable))
                return _control_receipt("fault_updated", fault=fault, enabled=enable, protocol_state=_protocol_state_label(node_state))
        return {
            "op": "receipt",
            "data": {"success": False, "message": "unknown_fault"},
            "metadata": {},
        }

    if op == "inject_state":
        data = msg.get("data", {})
        if not isinstance(data, dict):
            data = {}
        with state_lock:
            applied = _apply_injected_state(node_state, data.get("sensor_state", "NORMAL"))
            _add_recent_msg(node_state, "control:state={}".format(applied))
        return _control_receipt("state_updated", protocol_state=applied)

    drop_for_fault = False
    with state_lock:
        if node_state.get("DESTROYED", False):
            return jsonify({"error": "Node is destroyed"}), 503
        if egess_api.effective_crash(node_state):
            _add_recent_msg(node_state, "drop:{} (crash_sim/flap)".format(op or msg.get("type", "message")))
            drop_for_fault = True
        else:
            _record_inbound_msg(node_state, msg)

    if drop_for_fault:
        time.sleep(min(1.1, float(config_json.get("request_timeout", 1.0))))
        return jsonify({"error": "Node unavailable"}), 503

    if msg.get("type") == "heartbeat":
        sender = str(msg.get("from"))
        with state_lock:
            node_state["neighbor_last_heartbeat"][sender] = time.time()
        return jsonify({"status": "ok"}), 200

    if msg.get("type") == "alarmed_notification":
        with state_lock:
            event_id = msg.get("event_id", "unknown")
            if not node_state["DESTROYED"] and not node_state["ALARMED"] and not node_state["SURVEYING"]:
                node_state["ALARMED"] = True
                node_state["NORMAL"] = False
                egess_api.write_state_change_data_point(this_port, node_state, "ALARMED")
                forward_count = int(msg.get("forward_count", 0)) + 1
                if forward_count < int(config_json["max_alarm_forwards"]):
                    push_queue.put(
                        {
                            "type": "alarm_wave",
                            "from": this_port,
                            "forward_count": forward_count,
                            "event_id": event_id,
                            "origin_time": msg.get("origin_time", 0),
                        }
                    )
        return jsonify({"status": "ok"}), 200

    if msg.get("type") == "alarm_wave":
        with state_lock:
            event_id = msg.get("event_id", "unknown")
            already_seen = event_id in node_state["seen_alarm_events"]
            if not node_state["DESTROYED"] and not already_seen:
                node_state["seen_alarm_events"].append(event_id)
                forward_count = int(msg.get("forward_count", 0)) + 1
                origin_time = msg.get("origin_time", 0)
                if not node_state["ALARMED"] and not node_state["SURVEYING"]:
                    delta = round(time.time() - origin_time, 4) if origin_time else -1
                    egess_api.write_data_point(this_port, "alarm_wave_received", "{}:delta={}s".format(event_id, delta))
                    egess_api.write_data_point(this_port, "alarm_wave_received", "{};from={}".format(event_id, str(msg.get("from", "unknown"))))
                    if forward_count < int(config_json["max_alarm_forwards"]):
                        push_queue.put(
                            {
                                "type": "alarm_wave",
                                "from": this_port,
                                "forward_count": forward_count,
                                "event_id": event_id,
                                "origin_time": origin_time,
                            }
                        )
        return jsonify({"status": "ok"}), 200

    if msg.get("type") == "clear_alarmed":
        with state_lock:
            if node_state["ALARMED"] and not node_state["DESTROYED"]:
                node_state["ALARMED"] = False
                node_state["NORMAL"] = not node_state["SURVEYING"] and not node_state.get("ON_FIRE", False)
                egess_api.write_state_change_data_point(this_port, node_state, _protocol_state_label(node_state))
        return jsonify({"status": "ok"}), 200

    if msg.get("type") == "fire_spread":
        with state_lock:
            if not node_state["DESTROYED"] and not node_state["ON_FIRE"]:
                node_state["ON_FIRE"] = True
                node_state["fire_arrival_time"] = time.time()
                egess_api.write_data_point(this_port, "fire_spread_received", str(msg.get("from", "unknown")))
        return jsonify({"status": "ok"}), 200

    if msg.get("type") == "state_request":
        with state_lock:
            snapshot = {
                "from": this_port,
                "counter": node_state["heartbeat_counter"],
                "ALARMED": node_state["ALARMED"],
                "SURVEYING": node_state["SURVEYING"],
                "DESTROYED": node_state["DESTROYED"],
                "NORMAL": node_state["NORMAL"],
                "protocol_state": _protocol_state_label(node_state),
                "faults": copy.deepcopy(node_state.get("faults", {})),
                "msg_counters": copy.deepcopy(node_state.get("msg_counters", {})),
            }
        return jsonify({"state": snapshot}), 200

    if op == "pull":
        if egess_api._log_enabled():
            print("PULL REQUEST RECEIVED\n")
            egess_api.write_data_point(this_port, "pull_request_received", str(msg.get("from", "unknown")))
        with state_lock:
            snapshot = copy.deepcopy(node_state)
            snapshot["protocol_state"] = _protocol_state_label(snapshot)
        return {
            "op": "receipt",
            "data": {
                "success": True,
                "message": "",
                "node_state": snapshot,
            },
            "metadata": {},
        }

    if op == "push":
        metadata = msg.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            msg["metadata"] = metadata

        try:
            forward_count = int(metadata.get("forward_count", 0))
        except Exception:
            forward_count = 0

        if forward_count >= int(config_json["max_forwards"]):
            return {
                "op": "receipt",
                "data": {"success": False, "message": "message is not enqueued"},
                "metadata": {},
            }

        with state_lock:
            node_state["accepted_messages"] = int(node_state.get("accepted_messages", 0)) + 1
            relay = metadata.get("relay", 0)
            if relay not in node_state["known_nodes"] and relay != 0:
                node_state["known_nodes"].append(relay)
            egess_api.write_state_change_data_point(this_port, node_state, "accepted_messages")
            egess_api.write_state_change_data_point(this_port, node_state, "known_nodes")

        msg["metadata"]["relay"] = this_port
        msg["metadata"]["forward_count"] = forward_count + 1
        push_queue.put(msg)

        return {
            "op": "receipt",
            "data": {"success": True, "message": "message enqueued"},
            "metadata": {},
        }

    print("ERROR: listener_protocol: unknown type of message: {}\n".format(op or msg.get("type")))
    return {
        "op": "receipt",
        "data": {"success": False, "message": "unknown operation"},
        "metadata": {},
    }
