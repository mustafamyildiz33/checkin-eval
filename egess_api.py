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
# This file provides a set of commonly used functions (the EGESS API),
# which are likely to be used by several different modules of EGESS.
# -------------------------------------------------------------------------

import json
import os
import time

import requests
from requests.adapters import HTTPAdapter


RECENT_MSG_MAX = 60
_HTTP_SESSION = None


def _http_session():
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        session = requests.Session()
        session.trust_env = False
        adapter = HTTPAdapter(pool_connections=128, pool_maxsize=128, max_retries=0, pool_block=False)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _HTTP_SESSION = session
    return _HTTP_SESSION


def _demo_mode():
    return os.environ.get("DEMO_MODE", "0") == "1"


def _log_enabled():
    if _demo_mode():
        return os.environ.get("EGESS_LOG", "0") == "1"
    return True


def _data_path():
    base = os.environ.get("EGESS_LOG_DIR", ".")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, "data.csv")


def log_new_node_state(this_port, apriori_node_state, aposteriori_node_state):
    """
    Add to the log a record of a node state transition in a uniform format.

    Args:
        this_port (int): The port this node listens.
        apriori_node_state (dict[str, Any]): The state of the node (JSON) before the transition.
        aposteriori_node_state (dict[str, Any]): The state of the node (JSON) after the transition.
    """
    if not _log_enabled():
        return
    print(
        "NODE STATE CHANGED (NODE {}):\nAPRIORI: {}\nAPOSTERIORI: {}\n".format(
            this_port,
            json.dumps(apriori_node_state),
            json.dumps(aposteriori_node_state),
        )
    )


def log_current_node_state(this_port, node_state):
    """
    Add to the log a record of the current state of the node in a uniform format.

    Args:
        this_port (int): The port this node listens.
        node_state (dict[str, Any]): The state of the node (JSON).
    """
    if not _log_enabled():
        return
    print(
        "NODE STATE (NODE {}):\nSTATE: {}\n".format(
            this_port,
            json.dumps(node_state),
        )
    )


def write_data_point(this_port, logtype, message):
    """
    Write a data point to data.csv file with semicolon as a delimiter.

    Args:
        this_port (int): The port this node listens.
        logtype (str): A unique key for specific type of log.
        message (str): This is the data to be logged at the last column.
    """
    data_file = _data_path()
    with open(data_file, "a", encoding="utf-8") as handle:
        handle.write("{};{};{};{}\n".format(this_port, time.time(), logtype, message))


def write_state_change_data_point(this_port, node_state, state_key):
    """
    Write a data point to data.csv file indicating the change of a state.

    Args:
        this_port (int): The port this node listens.
        node_state (dict[str, Any]): The state of this current node.
        state_key (str): The state key which value has changed.
    """
    write_data_point(this_port, "state_change", "{}={}".format(state_key, node_state.get(state_key)))


def serialized_size_bytes(payload):
    """
    Estimate the UTF-8 payload size used for protocol accounting.

    Args:
        payload: JSON-serializable payload object.

    Returns:
        int: Byte length of a compact JSON serialization.
    """
    try:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    except Exception:
        body = json.dumps(str(payload))
    return int(len(body.encode("utf-8")))


def ensure_faults(node_state):
    faults = node_state.get("faults", {})
    if not isinstance(faults, dict):
        faults = {}
    faults["crash_sim"] = bool(faults.get("crash_sim", False))
    faults["lie_sensor"] = bool(faults.get("lie_sensor", False))
    faults["flap"] = bool(faults.get("flap", False))
    faults["period_sec"] = int(faults.get("period_sec", 4))
    node_state["faults"] = faults
    return faults


def effective_crash(node_state, now=None):
    faults = ensure_faults(node_state)
    if faults.get("crash_sim", False):
        return True
    if not faults.get("flap", False):
        return False
    period_sec = max(1, int(faults.get("period_sec", 4)))
    current_time = float(time.time()) if now is None else float(now)
    slot = int(current_time // period_sec)
    return bool(slot % 2 == 0)


def _ensure_msg_counters(node_state):
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
    return counters


def append_recent_msg(node_state, message):
    events = node_state.get("recent_msgs", [])
    if not isinstance(events, list):
        events = []
    events.append("[{}] {}".format(time.strftime("%H:%M:%S"), str(message)))
    if len(events) > RECENT_MSG_MAX:
        events = events[-RECENT_MSG_MAX:]
    node_state["recent_msgs"] = events


def _message_kind(msg):
    if isinstance(msg, dict) and str(msg.get("op", "")).strip():
        return str(msg.get("op"))
    if isinstance(msg, dict) and str(msg.get("type", "")).strip():
        return str(msg.get("type"))
    return "unknown"


def send_msg(config_json, node_state, state_lock, this_port, msg, target_port):
    """
    Send a POST request with JSON to the node with the specified port.

    Args:
        config_json (dict[str, Any]): JSON object with all-nodes configuration.
        node_state (dict[str, Any]): The state of this current node.
        state_lock (threading.Lock): The lock object for thread-safety of the state.
        this_port (int): The port this node listens.
        msg (dict[str, Any]): The JSON object to be sent.
        target_port (int): The port (i.e., node ID) of the recipient node.

    Returns:
        dict[str, Any]: Response JSON when available, otherwise a synthetic receipt.
    """
    msg_kind = _message_kind(msg)
    msg_size_bytes = serialized_size_bytes(msg)

    state_lock.acquire()
    try:
        counters = _ensure_msg_counters(node_state)
        if msg_kind == "pull":
            counters["pull_tx"] = int(counters.get("pull_tx", 0)) + 1
            counters["pull_tx_bytes"] = int(counters.get("pull_tx_bytes", 0)) + int(msg_size_bytes)
        else:
            counters["push_tx"] = int(counters.get("push_tx", 0)) + 1
            counters["push_tx_bytes"] = int(counters.get("push_tx_bytes", 0)) + int(msg_size_bytes)
        counters["tx_total_bytes"] = int(counters.get("tx_total_bytes", 0)) + int(msg_size_bytes)
        append_recent_msg(node_state, "tx:{} -> {} bytes={}".format(msg_kind, target_port, msg_size_bytes))
    finally:
        state_lock.release()

    i = this_port - config_json["base_port"]
    j = target_port - config_json["base_port"]
    try:
        time.sleep(node_state["latency_matrix"][i][j])
    except Exception:
        time.sleep(config_json.get("default_latency", 0.0))

    try:
        host_url = "http://" + config_json["base_host"]
        resp = _http_session().post(
            "{}:{}/".format(host_url, target_port),
            json=msg,
            timeout=(
                float(config_json.get("request_timeout", 1.0)),
                float(config_json.get("request_timeout", 1.0)),
            ),
        )
        try:
            if resp.status_code == 200:
                try:
                    resp_json = resp.json()
                except Exception:
                    resp_json = {
                        "op": "receipt",
                        "data": {
                            "success": False,
                            "message": "invalid_json_response",
                        },
                        "metadata": {},
                    }
                if _log_enabled():
                    print(
                        "send_msg: MESSAGE SENT ({} -> {}): {}; RESPONSE: {}\n".format(
                            this_port, target_port, msg, resp_json
                        )
                    )
                with state_lock:
                    counters = _ensure_msg_counters(node_state)
                    counters["tx_ok"] = int(counters.get("tx_ok", 0)) + 1
                    append_recent_msg(node_state, "tx_ok:{} -> {}".format(msg_kind, target_port))
                return resp_json

            if _log_enabled():
                print("ERROR: send_msg: return code is not 200.\n")
            with state_lock:
                counters = _ensure_msg_counters(node_state)
                counters["tx_fail"] = int(counters.get("tx_fail", 0)) + 1
                append_recent_msg(node_state, "tx_fail:{} -> {} status={}".format(msg_kind, target_port, resp.status_code))
            return {
                "op": "receipt",
                "data": {
                    "success": False,
                    "message": "http_status_{}".format(resp.status_code),
                },
                "metadata": {},
            }
        finally:
            resp.close()

    except requests.exceptions.Timeout:
        if _log_enabled():
            print("ERROR: send_msg: Timeout.\n")
        with state_lock:
            counters = _ensure_msg_counters(node_state)
            counters["tx_timeout"] = int(counters.get("tx_timeout", 0)) + 1
            counters["tx_fail"] = int(counters.get("tx_fail", 0)) + 1
            append_recent_msg(node_state, "tx_timeout:{} -> {}".format(msg_kind, target_port))
        return {
            "op": "receipt",
            "data": {
                "success": False,
                "message": "timeout",
            },
            "metadata": {},
        }

    except requests.exceptions.ConnectionError:
        if _log_enabled():
            print("ERROR: send_msg: Connection error.\n")
        with state_lock:
            counters = _ensure_msg_counters(node_state)
            counters["tx_conn_error"] = int(counters.get("tx_conn_error", 0)) + 1
            counters["tx_fail"] = int(counters.get("tx_fail", 0)) + 1
            append_recent_msg(node_state, "tx_conn_error:{} -> {}".format(msg_kind, target_port))
        return {
            "op": "receipt",
            "data": {
                "success": False,
                "message": "connection_error",
            },
            "metadata": {},
        }
    except requests.exceptions.RequestException:
        if _log_enabled():
            print("ERROR: send_msg: HTTP request error.\n")
        with state_lock:
            counters = _ensure_msg_counters(node_state)
            counters["tx_fail"] = int(counters.get("tx_fail", 0)) + 1
            append_recent_msg(node_state, "tx_request_error:{} -> {}".format(msg_kind, target_port))
        return {
            "op": "receipt",
            "data": {
                "success": False,
                "message": "request_error",
            },
            "metadata": {},
        }
