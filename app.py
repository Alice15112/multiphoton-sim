
import copy
import math
import random

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Multiphoton Quantum Simulator", layout="wide")

st.title("Multiphoton Quantum Simulator")

st.markdown(
    """
Interactive simulator of the quantum communication scheme.

Click elements of the scheme to configure:
- source
- channels
- PR elements
- detectors
- beam splitters
- Eve interception
"""
)

# ============================================================
# Session state initialization
# ============================================================

if "selected_element" not in st.session_state:
    st.session_state.selected_element = None

if "scheme_params" not in st.session_state:
    st.session_state.scheme_params = {
        "source": {
            "message": "Hello Bob",
            "num_packets": 2000,
            "pair_generation_efficiency": 0.95,
            "mode": "manual",  # manual / article_state
            "article_state_label": "psi1",
            "selected_state_label": "manual",
            "state_angles": {
                "channel_1": 0.0,
                "channel_2": 0.0,
                "channel_3": 0.0,
                "channel_4": 0.0,
            },
        },
        "channels": {
            "channel_1": {"loss": 0.05, "eve": False, "eve_mode": "disturbance_only", "eve_disturbance": 0.15, "eve_delay": 0.0, "length": 10.0},
            "channel_2": {"loss": 0.05, "eve": False, "eve_mode": "disturbance_only", "eve_disturbance": 0.15, "eve_delay": 0.0, "length": 10.0},
            "channel_3": {"loss": 0.05, "eve": False, "eve_mode": "disturbance_only", "eve_disturbance": 0.15, "eve_delay": 0.0, "length": 10.0},
            "channel_4": {"loss": 0.05, "eve": False, "eve_mode": "disturbance_only", "eve_disturbance": 0.15, "eve_delay": 0.0, "length": 10.0},
        },
        "pr": {
            "pr_1": {"angle": 0.0, "error": 0.0},
            "pr_2": {"angle": 0.0, "error": 0.0},
            "pr_3": {"angle": 0.0, "error": 0.0},
            "pr_4": {"angle": 0.0, "error": 0.0},
        },
        "detectors": {
            "detector_1": {"eta": 0.85, "dark": 0.0},
            "detector_2": {"eta": 0.85, "dark": 0.0},
            "detector_3": {"eta": 0.85, "dark": 0.0},
            "detector_4": {"eta": 0.85, "dark": 0.0},
        },
        "beam_splitters": {
            "bs_left": {"loss": 0.02},
            "bs_right": {"loss": 0.02},
        },
        "simulation": {
            "detection_mode": "fourfold",
            "physics_model": "article_pr_standard_basis",
        },
        "timing": {
            "speed": 2e8,
            "coincidence_window": 2e-9,
            "detector_jitter": 0.2e-9,
        },
    }

params = st.session_state.scheme_params

if "last_debug_result" not in st.session_state:
    st.session_state.last_debug_result = None

if "last_debug_state_label" not in st.session_state:
    st.session_state.last_debug_state_label = None

if "last_message_result" not in st.session_state:
    st.session_state.last_message_result = None

if "last_simulation_result" not in st.session_state:
    st.session_state.last_simulation_result = None

if "last_self_test_result" not in st.session_state:
    st.session_state.last_self_test_result = None

if "last_physics_check_result" not in st.session_state:
    st.session_state.last_physics_check_result = None

if "last_validation_result" not in st.session_state:
    st.session_state.last_validation_result = None

if "last_sweep_result" not in st.session_state:
    st.session_state.last_sweep_result = None

# ============================================================
# Migration for older saved state
# ============================================================

if "state_angles" not in params["source"]:
    old_angle = params["source"].get("state_angle", 0.0)
    params["source"]["state_angles"] = {
        "channel_1": old_angle,
        "channel_2": old_angle,
        "channel_3": old_angle,
        "channel_4": old_angle,
    }
    if "state_angle" in params["source"]:
        del params["source"]["state_angle"]

if "mode" not in params["source"]:
    params["source"]["mode"] = "manual"

if "article_state_label" not in params["source"]:
    params["source"]["article_state_label"] = "psi1"

if "selected_state_label" not in params["source"]:
    params["source"]["selected_state_label"] = "manual"

if "simulation" not in params:
    params["simulation"] = {"detection_mode": "fourfold", "physics_model": "article_pr_standard_basis"}

if "physics_model" not in params["simulation"]:
    params["simulation"]["physics_model"] = "article_pr_standard_basis"

if "detection_mode" not in params["simulation"]:
    params["simulation"]["detection_mode"] = "fourfold"

if "timing" not in params:
    params["timing"] = {
        "speed": 2e8,
        "coincidence_window": 2e-9,
        "detector_jitter": 0.2e-9,
    }

for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
    if "length" not in params["channels"][channel_name]:
        params["channels"][channel_name]["length"] = 10.0
    if "eve_delay" not in params["channels"][channel_name]:
        params["channels"][channel_name]["eve_delay"] = 0.0

    if "eve_mode" not in params["channels"][channel_name]:
        params["channels"][channel_name]["eve_mode"] = "disturbance_only"

left_col, right_col = st.columns([2, 1])

# ============================================================
# Click zones on scheme
# ============================================================

CLICK_ZONES = {
    "channel_1": {"x1": 366, "x2": 630, "y1": 91, "y2": 129},
    "channel_2": {"x1": 582, "x2": 640, "y1": 205, "y2": 240},
    "channel_3": {"x1": 582, "x2": 640, "y1": 260, "y2": 303},
    "channel_4": {"x1": 366, "x2": 630, "y1": 367, "y2": 421},
    "detector_1": {"x1": 822, "x2": 918, "y1": 60, "y2": 150},
    "detector_2": {"x1": 822, "x2": 918, "y1": 150, "y2": 250},
    "detector_3": {"x1": 822, "x2": 918, "y1": 250, "y2": 340},
    "detector_4": {"x1": 822, "x2": 918, "y1": 350, "y2": 450},
    "pr_1": {"x1": 640, "x2": 670, "y1": 73, "y2": 134},
    "pr_2": {"x1": 640, "x2": 670, "y1": 181, "y2": 240},
    "pr_3": {"x1": 640, "x2": 670, "y1": 240, "y2": 300},
    "pr_4": {"x1": 640, "x2": 670, "y1": 367, "y2": 421},
    "bs_left": {"x1": 87, "x2": 140, "y1": 236, "y2": 265},
    "bs_right": {"x1": 526, "x2": 600, "y1": 239, "y2": 257},
    "source": {"x1": 38, "x2": 92, "y1": 161, "y2": 219},
}

# ============================================================
# Helpers
# ============================================================

@st.cache_data
def load_scheme_image():
    return Image.open("assets/scheme.png")


def detect_clicked_zone(coords, zones):
    if coords is None:
        return None

    x = coords["x"]
    y = coords["y"]

    for zone_name, zone in zones.items():
        if zone["x1"] <= x <= zone["x2"] and zone["y1"] <= y <= zone["y2"]:
            return zone_name

    return None


def draw_highlight_on_scheme(image: Image.Image, selected: str, zones: dict) -> Image.Image:
    highlighted = image.copy()
    draw = ImageDraw.Draw(highlighted)

    if selected in zones:
        zone = zones[selected]
        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
        draw.rectangle([x1, y1, x2, y2], outline="red", width=4)
        draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y2 - 2], outline="yellow", width=2)

    return highlighted


def polarization_label_to_angle(label: str) -> float:
    if label == "x":
        return 0.0
    if label == "y":
        return 90.0
    raise ValueError(f"Unknown polarization label: {label}")


def quantum_measurement_probability(state_angle_deg: float, pr_angle_deg: float, pr_error: float) -> float:
    effective_pr_angle = pr_angle_deg + random.uniform(-pr_error * 180.0, pr_error * 180.0)
    angle_diff_rad = math.radians(state_angle_deg - effective_pr_angle)
    probability = math.cos(angle_diff_rad) ** 2
    return max(0.0, min(1.0, probability))


def ket_index(bits):
    b1, b2, b3, b4 = bits
    return (b1 << 3) | (b2 << 2) | (b3 << 1) | b4


def basis_ket(bits):
    vec = np.zeros(16, dtype=float)
    vec[ket_index(bits)] = 1.0
    return vec


def normalize_state(vec):
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def build_article_state_vectors():
    x = 0
    y = 1

    psi1 = (
        basis_ket((y, x, y, x)) +
        basis_ket((x, y, x, y)) +
        basis_ket((x, x, y, y)) +
        basis_ket((y, y, x, x))
    ) / 2.0

    psi2 = (
        basis_ket((y, x, y, y)) +
        basis_ket((x, y, x, x)) +
        basis_ket((x, x, y, x)) +
        basis_ket((y, y, x, y))
    ) / 2.0

    psi3 = (
        basis_ket((y, y, y, y)) +
        basis_ket((x, x, x, x)) +
        basis_ket((x, y, y, x)) +
        basis_ket((y, x, x, y))
    ) / 2.0

    psi4 = (
        basis_ket((y, y, y, x)) +
        basis_ket((x, x, x, y)) +
        basis_ket((x, y, y, y)) +
        basis_ket((y, x, x, x))
    ) / 2.0

    return {
        "psi1": normalize_state(psi1),
        "psi2": normalize_state(psi2),
        "psi3": normalize_state(psi3),
        "psi4": normalize_state(psi4),
    }


ARTICLE_STATE_VECTORS = build_article_state_vectors()

ARTICLE_STATES = {
    "psi1": "ψ1 = 1/2 (|y1x2y3x4⟩ + |x1y2x3y4⟩ + |x1x2y3y4⟩ + |y1y2x3x4⟩) ≡ 00",
    "psi2": "ψ2 = 1/2 (|y1x2y3y4⟩ + |x1y2x3x4⟩ + |x1x2y3x4⟩ + |y1y2x3y4⟩) ≡ 01",
    "psi3": "ψ3 = 1/2 (|y1y2y3y4⟩ + |x1x2x3x4⟩ + |x1y2y3x4⟩ + |y1x2x3y4⟩) ≡ 10",
    "psi4": "ψ4 = 1/2 (|y1y2y3x4⟩ + |x1x2x3y4⟩ + |x1y2y3y4⟩ + |y1x2x3x4⟩) ≡ 11",
}

STATE_TO_BITS = {
    "psi1": "00",
    "psi2": "01",
    "psi3": "10",
    "psi4": "11",
}

BITS_TO_STATE = {bits: state for state, bits in STATE_TO_BITS.items()}


def text_to_bitstring(text: str) -> str:
    data = text.encode("utf-8")
    return "".join(f"{byte:08b}" for byte in data)


def bitstring_to_text(bitstring: str) -> str:
    if not bitstring:
        return ""

    usable_length = (len(bitstring) // 8) * 8
    trimmed = bitstring[:usable_length]

    if not trimmed:
        return ""

    byte_values = [
        int(trimmed[i:i + 8], 2)
        for i in range(0, len(trimmed), 8)
    ]

    try:
        return bytes(byte_values).decode("utf-8")
    except UnicodeDecodeError:
        return bytes(byte_values).decode("utf-8", errors="replace")


def split_bits_into_pairs(bitstring: str) -> list[str]:
    if len(bitstring) % 2 != 0:
        bitstring += "0"

    return [
        bitstring[i:i + 2]
        for i in range(0, len(bitstring), 2)
    ]


def bit_pairs_to_states(bit_pairs: list[str]) -> list[str]:
    states = []

    for pair in bit_pairs:
        if pair not in BITS_TO_STATE:
            raise ValueError(f"Unknown bit pair: {pair}")
        states.append(BITS_TO_STATE[pair])

    return states


def encode_text_to_states(text: str) -> dict:
    bitstring = text_to_bitstring(text)
    bit_pairs = split_bits_into_pairs(bitstring)
    states = bit_pairs_to_states(bit_pairs)

    return {
        "text": text,
        "bitstring": bitstring,
        "bit_pairs": bit_pairs,
        "states": states,
    }


def reduced_density_matrix_one_qubit(state_vector, qubit_index):
    psi_tensor = state_vector.reshape(2, 2, 2, 2)
    rho = np.tensordot(
        psi_tensor,
        psi_tensor,
        axes=(
            [q for q in range(4) if q != qubit_index],
            [q for q in range(4) if q != qubit_index],
        ),
    )
    return rho


def compute_bit_error_rate(original_bits: str, recovered_bits_raw: str) -> dict:
    recovered_bits = "".join(ch for ch in recovered_bits_raw if ch in "01")
    comparable_length = min(len(original_bits), len(recovered_bits))

    if comparable_length == 0:
        return {
            "bit_errors": 0,
            "compared_bits": 0,
            "ber": 0.0,
        }

    bit_errors = sum(
        1 for i in range(comparable_length)
        if original_bits[i] != recovered_bits[i]
    )

    ber = bit_errors / comparable_length

    return {
        "bit_errors": bit_errors,
        "compared_bits": comparable_length,
        "ber": ber,
    }


def compute_symbol_error_rate(results: list[dict]) -> dict:
    detected_results = [r for r in results if r["postselection_passed"]]

    if not detected_results:
        return {
            "symbol_errors": 0,
            "compared_symbols": 0,
            "ser": 0.0,
        }

    symbol_errors = sum(
        1 for r in detected_results
        if not r["is_correct"]
    )

    compared_symbols = len(detected_results)
    ser = symbol_errors / compared_symbols

    return {
        "symbol_errors": symbol_errors,
        "compared_symbols": compared_symbols,
        "ser": ser,
    }


def projector_for_angle(angle_deg, pr_error):
    effective_angle = angle_deg + random.uniform(-pr_error * 180.0, pr_error * 180.0)
    theta = math.radians(effective_angle)

    ket_theta = np.array([
        math.cos(theta),
        math.sin(theta),
    ], dtype=float)

    return np.outer(ket_theta, ket_theta)


def build_bit_comparison_table(bit_pairs: list[str], results: list[dict]) -> pd.DataFrame:
    rows = []

    for idx, (original_bits, result) in enumerate(zip(bit_pairs, results), start=1):
        recovered_bits = result["decoded_bits"] if result["decoded_bits"] is not None else "??"

        bit_errors = None
        if recovered_bits != "??":
            bit_errors = sum(
                1 for a, b in zip(original_bits, recovered_bits)
                if a != b
            )

        rows.append({
            "index": idx,
            "original_bits": original_bits,
            "sent_state": result["sent_state"],
            "observed_pattern": result["observed_pattern"],
            "detected_channels": result["detected_channels"],
            "postselection_passed": result["postselection_passed"],
            "decoded_state": result["decoded_state"],
            "recovered_bits": recovered_bits,
            "bit_errors_in_symbol": bit_errors,
            "symbol_correct": result["is_correct"],
            "rejection_reason": result["rejection_reason"],
        })

    return pd.DataFrame(rows)


def article_state_channel_probability_vector(state_label, channel_name, pr_angle_deg, pr_error):
    state_vector = ARTICLE_STATE_VECTORS[state_label]

    channel_to_qubit = {
        "channel_1": 0,
        "channel_2": 1,
        "channel_3": 2,
        "channel_4": 3,
    }

    qubit_index = channel_to_qubit[channel_name]
    rho_i = reduced_density_matrix_one_qubit(state_vector, qubit_index)
    projector = projector_for_angle(pr_angle_deg, pr_error)

    probability = float(np.trace(rho_i @ projector))
    return max(0.0, min(1.0, probability))


def orthogonal_ket_for_angle(angle_deg):
    theta = math.radians(angle_deg)
    return np.array([
        -math.sin(theta),
        math.cos(theta)
    ], dtype=float)


def ket_for_angle(angle_deg):
    theta = math.radians(angle_deg)
    return np.array([
        math.cos(theta),
        math.sin(theta)
    ], dtype=float)


def effective_pr_angles_for_packet(params):
    pr_names = ["pr_1", "pr_2", "pr_3", "pr_4"]
    effective_angles = {}

    for idx, pr_name in enumerate(pr_names, start=1):
        pr = params["pr"][pr_name]
        effective_angle = pr["angle"] + random.uniform(-pr["error"] * 180.0, pr["error"] * 180.0)
        effective_angles[f"channel_{idx}"] = effective_angle

    return effective_angles


def local_projector(angle_deg, click_value):
    if click_value == 1:
        ket = ket_for_angle(angle_deg)
    else:
        ket = orthogonal_ket_for_angle(angle_deg)

    return np.outer(ket, ket)


def kron4(a, b, c, d):
    return np.kron(np.kron(np.kron(a, b), c), d)


# ============================================================
# Main article-state path: PR as state rotation
# ============================================================

def rotation_matrix(angle_deg: float) -> np.ndarray:
    theta = math.radians(angle_deg)
    return np.array([
        [math.cos(theta), -math.sin(theta)],
        [math.sin(theta),  math.cos(theta)],
    ], dtype=float)


def kron_many(matrices: list[np.ndarray]) -> np.ndarray:
    result = matrices[0]
    for matrix in matrices[1:]:
        result = np.kron(result, matrix)
    return result


def sample_effective_pr_angles(params: dict) -> dict:
    effective_angles = {}

    for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
        pr = params["pr"][pr_name]
        effective_angles[pr_name] = (
            pr["angle"] + random.uniform(-pr["error"] * 180.0, pr["error"] * 180.0)
        )

    return effective_angles


def build_pr_rotation_operator_from_angles(effective_pr_angles: dict) -> np.ndarray:
    matrices = [
        rotation_matrix(effective_pr_angles["pr_1"]),
        rotation_matrix(effective_pr_angles["pr_2"]),
        rotation_matrix(effective_pr_angles["pr_3"]),
        rotation_matrix(effective_pr_angles["pr_4"]),
    ]
    return kron_many(matrices)


def apply_pr_rotations_to_state(state_vector: np.ndarray, effective_pr_angles: dict) -> np.ndarray:
    rotation_operator = build_pr_rotation_operator_from_angles(effective_pr_angles)
    rotated_state = rotation_operator @ state_vector
    return normalize_state(rotated_state)


def basis_projector(click_value: int) -> np.ndarray:
    if click_value == 0:
        ket = np.array([1.0, 0.0], dtype=float)  # |x>
    else:
        ket = np.array([0.0, 1.0], dtype=float)  # |y>
    return np.outer(ket, ket)


def joint_pattern_probabilities_in_standard_basis(state_vector: np.ndarray) -> dict:
    probs = {}
    rho = np.outer(state_vector, state_vector)

    for c1 in [0, 1]:
        for c2 in [0, 1]:
            for c3 in [0, 1]:
                for c4 in [0, 1]:
                    P1 = basis_projector(c1)
                    P2 = basis_projector(c2)
                    P3 = basis_projector(c3)
                    P4 = basis_projector(c4)

                    joint_projector = kron4(P1, P2, P3, P4)
                    prob = float(np.trace(rho @ joint_projector))
                    prob = max(0.0, prob)

                    probs[(c1, c2, c3, c4)] = prob

    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}

    return probs


def decode_state_from_pattern_with_pr(observed_pattern: tuple, effective_pr_angles: dict) -> tuple[str, float]:
    best_state = None
    best_prob = -1.0

    rotation_operator = build_pr_rotation_operator_from_angles(effective_pr_angles)

    for state_label, state_vector in ARTICLE_STATE_VECTORS.items():
        rotated_state = normalize_state(rotation_operator @ state_vector)
        probs = joint_pattern_probabilities_in_standard_basis(rotated_state)
        p = probs.get(tuple(observed_pattern), 0.0)

        if p > best_prob:
            best_prob = p
            best_state = state_label

    return best_state, best_prob


# ============================================================
# Legacy angle-based path kept for comparison / rollback
# ============================================================

def joint_pattern_probabilities(state_vector, effective_angles):
    probs = {}
    rho = np.outer(state_vector, state_vector)

    for c1 in [0, 1]:
        for c2 in [0, 1]:
            for c3 in [0, 1]:
                for c4 in [0, 1]:
                    P1 = local_projector(effective_angles["channel_1"], c1)
                    P2 = local_projector(effective_angles["channel_2"], c2)
                    P3 = local_projector(effective_angles["channel_3"], c3)
                    P4 = local_projector(effective_angles["channel_4"], c4)

                    joint_projector = kron4(P1, P2, P3, P4)
                    prob = float(np.trace(rho @ joint_projector))
                    prob = max(0.0, prob)

                    probs[(c1, c2, c3, c4)] = prob

    total = sum(probs.values())
    if total > 0:
        probs = {k: v / total for k, v in probs.items()}

    return probs


def sample_joint_pattern(prob_dict):
    patterns = list(prob_dict.keys())
    probabilities = list(prob_dict.values())
    index = np.random.choice(len(patterns), p=probabilities)
    return patterns[index]


def decode_state_from_pattern(observed_pattern, effective_angles):
    best_state = None
    best_prob = -1.0

    for state_label, state_vector in ARTICLE_STATE_VECTORS.items():
        probs = joint_pattern_probabilities(state_vector, effective_angles)
        p = probs.get(tuple(observed_pattern), 0.0)

        if p > best_prob:
            best_prob = p
            best_state = state_label

    return best_state, best_prob


def apply_channel_and_detector_effects(
    ideal_pattern: tuple,
    params: dict,
):
    """
    Apply channel loss, detector efficiency, dark counts, and Eve effects.

    Eve modes:
        - passive_monitor: Eve observes/logs the polarization but does not change it.
        - disturbance_only: Eve causes a simple polarization flip with probability eve_disturbance.
        - intercept_resend: simplified intercept-resend; Eve measures in the x/y basis and resends.
          The resend can be wrong with probability eve_disturbance.

    Returns:
        observed_pattern: tuple of 0/1 or None (polarization outcomes)
        detected_channels: tuple of bool
        channel_report: list of dicts (per channel diagnostics)
    """
    channel_names = ["channel_1", "channel_2", "channel_3", "channel_4"]

    observed_pattern = []
    detected_channels = []
    channel_report = []

    for idx, channel_name in enumerate(channel_names):
        ideal_pol = ideal_pattern[idx]

        channel = params["channels"][channel_name]
        loss_prob = channel["loss"]
        eve_flag = channel["eve"]
        eve_mode = channel.get("eve_mode", "disturbance_only")
        eve_disturbance = channel.get("eve_disturbance", 0.0)

        detector_name = f"detector_{idx + 1}"
        eta = params["detectors"][detector_name]["eta"]
        dark = params["detectors"][detector_name]["dark"]

        if channel_name in ["channel_2", "channel_3"]:
            loss_prob = min(1.0, loss_prob + params["beam_splitters"]["bs_right"]["loss"])
        else:
            loss_prob = min(1.0, loss_prob + params["beam_splitters"]["bs_left"]["loss"])

        lost_in_channel = random.random() < loss_prob

        eve_observed_polarization = None
        eve_resend_polarization = None
        eve_disturbed = False
        eve_action = "none"
        pol_after_eve = ideal_pol

        if eve_flag and not lost_in_channel:
            # In this simplified model Eve sees the x/y outcome represented by ideal_pol.
            eve_observed_polarization = ideal_pol

            if eve_mode == "passive_monitor":
                # Eve only observes/logs. No change to polarization.
                eve_action = "passive monitor"
                pol_after_eve = ideal_pol
                eve_resend_polarization = ideal_pol

            elif eve_mode == "disturbance_only":
                # Old simple model: Eve randomly flips the polarization.
                eve_action = "disturbance only"
                if random.random() < eve_disturbance:
                    pol_after_eve = 1 - ideal_pol
                    eve_disturbed = True
                eve_resend_polarization = pol_after_eve

            elif eve_mode == "intercept_resend":
                # Simplified intercept-resend: Eve measures and prepares a new signal.
                # eve_disturbance is interpreted as resend/preparation error probability.
                eve_action = "intercept-resend"
                resend_pol = eve_observed_polarization
                if random.random() < eve_disturbance:
                    resend_pol = 1 - eve_observed_polarization
                    eve_disturbed = True
                pol_after_eve = resend_pol
                eve_resend_polarization = resend_pol

            else:
                raise ValueError(f"Unknown Eve mode for {channel_name}: {eve_mode}")

        detected = False
        dark_used = False
        detector_miss = False
        observed_pol = None

        if not lost_in_channel:
            if random.random() < eta:
                detected = True
                observed_pol = pol_after_eve
            else:
                detector_miss = True

        if not detected and random.random() < dark:
            detected = True
            dark_used = True
            observed_pol = random.choice([0, 1])

        detected_channels.append(bool(detected))
        observed_pattern.append(observed_pol)

        channel_report.append({
            "channel": channel_name,
            "ideal_polarization": ideal_pol,
            "observed_polarization": observed_pol,
            "lost_in_channel": lost_in_channel,
            "detected": bool(detected),
            "detector_miss": detector_miss,
            "dark_count_used": dark_used,
            "eve_enabled": bool(eve_flag),
            "eve_mode": eve_mode if eve_flag else "off",
            "eve_action": eve_action,
            "eve_observed_polarization": eve_observed_polarization,
            "eve_resend_polarization": eve_resend_polarization,
            "eve_disturbed": eve_disturbed,
            "channel_length_m": channel["length"],
        })

    return tuple(observed_pattern), tuple(detected_channels), channel_report

def evaluate_detection_status(detected_channels: tuple, mode: str = "fourfold") -> dict:
    any_detected = any(detected_channels)
    all_detected = all(detected_channels)
    full_pattern_available = all_detected

    if mode == "any_click":
        packet_detected = any_detected
        fourfold_detected = all_detected
    elif mode == "fourfold":
        packet_detected = all_detected
        fourfold_detected = all_detected
    else:
        raise ValueError(f"Unknown detection mode: {mode}")

    if packet_detected:
        rejection_reason = None
    else:
        if not any_detected:
            rejection_reason = "no channels detected"
        elif not all_detected:
            rejection_reason = "not fourfold (missing channels)"
        else:
            rejection_reason = "unknown"

    return {
        "packet_detected": packet_detected,
        "fourfold_detected": fourfold_detected,
        "full_pattern_available": full_pattern_available,
        "rejection_reason": rejection_reason,
    }


def simulate_arrival_times(detected_channels: tuple, params: dict) -> dict:
    speed = params["timing"]["speed"]
    window = params["timing"]["coincidence_window"]
    jitter = params["timing"]["detector_jitter"]

    arrival_times = []

    for idx, detected in enumerate(detected_channels):
        channel_name = f"channel_{idx + 1}"
        channel = params["channels"][channel_name]

        if not detected:
            arrival_times.append(None)
            continue

        base_time = channel["length"] / speed

        if channel["eve"]:
            base_time += channel.get("eve_delay", 0.0)

        noise = random.uniform(-jitter, jitter)
        arrival_times.append(base_time + noise)

    valid_times = [time for time in arrival_times if time is not None]

    if len(valid_times) < 2:
        timing_spread = None
        coincidence_passed = False
        timing_anomaly = True
    else:
        timing_spread = max(valid_times) - min(valid_times)
        coincidence_passed = timing_spread <= window
        timing_anomaly = not coincidence_passed

    return {
        "arrival_times": arrival_times,
        "timing_spread": timing_spread,
        "coincidence_passed": coincidence_passed,
        "timing_anomaly": timing_anomaly,
        "coincidence_window": window,
    }


def infer_rejection_reason(channel_report: list[dict], base_reason: str | None, coincidence_passed: bool) -> str | None:
    if base_reason is not None:
        if any(row["lost_in_channel"] for row in channel_report):
            return "channel loss / not fourfold"
        if any(row["detector_miss"] for row in channel_report):
            return "detector miss / not fourfold"
        return base_reason

    if not coincidence_passed:
        return "failed coincidence window"

    return None


def classify_packet_event(
    *,
    postselection_passed: bool,
    fourfold_detected: bool,
    coincidence_passed: bool,
    detected_channels: tuple,
    channel_report: list[dict],
) -> dict:
    """
    Separate real losses from postselection rejection.

    Polarization pattern can be fully measured, but the event may still be rejected
    by the coincidence/time window. This should not be shown as 'lost'.
    """

    if postselection_passed:
        return {
            "packet_status": "accepted",
            "packet_status_label": "accepted",
            "display_decoded_state": "accepted",
            "is_physically_lost": False,
            "is_rejected_by_postselection": False,
        }

    has_any_detection = any(detected_channels)
    has_channel_loss = any(row["lost_in_channel"] for row in channel_report)
    has_detector_miss = any(row["detector_miss"] for row in channel_report)

    if not fourfold_detected:
        if has_channel_loss:
            status = "lost_channel"
            label = "lost in channel"
            is_physically_lost = True
        elif has_detector_miss:
            status = "detector_miss"
            label = "detector miss"
            is_physically_lost = True
        elif not has_any_detection:
            status = "no_detection"
            label = "no detection"
            is_physically_lost = True
        else:
            status = "rejected_not_fourfold"
            label = "rejected: not fourfold"
            is_physically_lost = False
    elif not coincidence_passed:
        status = "rejected_timing"
        label = "rejected: timing anomaly"
        is_physically_lost = False
    else:
        status = "rejected_postselection"
        label = "rejected by postselection"
        is_physically_lost = False

    return {
        "packet_status": status,
        "packet_status_label": label,
        "display_decoded_state": label,
        "is_physically_lost": is_physically_lost,
        "is_rejected_by_postselection": True,
    }


def simulate_single_state_transmission(state_label: str, params: dict) -> dict:
    if state_label not in ARTICLE_STATE_VECTORS:
        raise ValueError(f"Unknown article state: {state_label}")

    detection_mode = params.get("simulation", {}).get("detection_mode", "fourfold")

    state_vector = ARTICLE_STATE_VECTORS[state_label]
    sent_bits = STATE_TO_BITS[state_label]

    effective_pr_angles = sample_effective_pr_angles(params)
    rotated_state = apply_pr_rotations_to_state(state_vector, effective_pr_angles)
    joint_probs = joint_pattern_probabilities_in_standard_basis(rotated_state)
    ideal_pattern = sample_joint_pattern(joint_probs)

    observed_pattern, detected_channels, channel_report = apply_channel_and_detector_effects(
        ideal_pattern,
        params,
    )

    detection_status = evaluate_detection_status(detected_channels, detection_mode)

    timing_result = simulate_arrival_times(
        detected_channels,
        params,
    )
    arrival_times = timing_result["arrival_times"]
    timing_spread = timing_result["timing_spread"]
    coincidence_passed = timing_result["coincidence_passed"]
    timing_anomaly = timing_result["timing_anomaly"]

    packet_detected = detection_status["packet_detected"]
    fourfold_detected = detection_status["fourfold_detected"]
    full_pattern_available = detection_status["full_pattern_available"]

    postselection_passed = fourfold_detected and coincidence_passed and full_pattern_available
    rejection_reason = infer_rejection_reason(
        channel_report,
        detection_status["rejection_reason"],
        coincidence_passed,
    )
    packet_classification = classify_packet_event(
        postselection_passed=postselection_passed,
        fourfold_detected=fourfold_detected,
        coincidence_passed=coincidence_passed,
        detected_channels=detected_channels,
        channel_report=channel_report,
    )

    observed_pattern_for_decoding = observed_pattern
    if not full_pattern_available:
        observed_pattern_for_decoding = None

    decoded_state = None
    decoded_bits = None
    decoding_confidence = 0.0
    is_correct = False

    if postselection_passed and observed_pattern_for_decoding is not None:
        decoded_state, decoding_confidence = decode_state_from_pattern_with_pr(
            observed_pattern_for_decoding,
            effective_pr_angles,
        )
        decoded_bits = STATE_TO_BITS[decoded_state]
        is_correct = decoded_state == state_label

    return {
        "sent_state": state_label,
        "sent_bits": sent_bits,
        "effective_pr_angles": effective_pr_angles,
        "ideal_pattern": ideal_pattern,
        "observed_pattern": observed_pattern,
        "detected_channels": detected_channels,
        "arrival_times": arrival_times,
        "timing_spread": timing_spread,
        "coincidence_window": timing_result["coincidence_window"],
        "coincidence_passed": coincidence_passed,
        "timing_anomaly": timing_anomaly,
        "packet_detected": packet_detected,
        "fourfold_detected": fourfold_detected,
        "full_pattern_available": full_pattern_available,
        "postselection_passed": postselection_passed,
        "rejection_reason": rejection_reason,
        "packet_status": packet_classification["packet_status"],
        "packet_status_label": packet_classification["packet_status_label"],
        "display_decoded_state": decoded_state or packet_classification["display_decoded_state"],
        "is_physically_lost": packet_classification["is_physically_lost"],
        "is_rejected_by_postselection": packet_classification["is_rejected_by_postselection"],
        "channel_report": channel_report,
        "decoded_state": decoded_state,
        "decoded_bits": decoded_bits,
        "decoding_confidence": decoding_confidence,
        "is_correct": is_correct,
        "was_lost": packet_classification["is_physically_lost"],
    }


def format_pattern_tuple(pattern):
    if pattern is None:
        return "—"
    return "".join("?" if bit is None else str(bit) for bit in pattern)


def format_bool_tuple(values):
    return "(" + ", ".join("T" if value else "F" for value in values) + ")"


def format_arrival_times(arrival_times):
    formatted = []
    for value in arrival_times:
        if value is None:
            formatted.append("—")
        else:
            formatted.append(f"{value:.3e}")
    return formatted


def state_vector_to_amplitude_table(state_vector: np.ndarray, threshold: float = 1e-9) -> pd.DataFrame:
    rows = []

    for index, amplitude in enumerate(state_vector):
        probability = float(abs(amplitude) ** 2)
        if probability < threshold:
            continue

        bits = format(index, "04b")
        basis_label = f"|{''.join('x' if bit == '0' else 'y' for bit in bits)}⟩"

        rows.append({
            "basis_index": index,
            "basis_bits": bits,
            "basis_state": basis_label,
            "amplitude": float(amplitude),
            "probability": probability,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("probability", ascending=False).reset_index(drop=True)
        df["probability"] = df["probability"].round(6)
        df["amplitude"] = df["amplitude"].round(6)

    return df


def probability_dict_to_dataframe(prob_dict: dict) -> pd.DataFrame:
    rows = []

    for pattern, probability in prob_dict.items():
        rows.append({
            "pattern_tuple": pattern,
            "pattern_bits": format_pattern_tuple(pattern),
            "probability": float(probability),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("probability", ascending=False).reset_index(drop=True)
        df["probability"] = df["probability"].round(6)

    return df


def build_single_packet_debug_report(state_label: str, params: dict) -> dict:
    if state_label not in ARTICLE_STATE_VECTORS:
        raise ValueError(f"Unknown article state: {state_label}")

    state_vector = ARTICLE_STATE_VECTORS[state_label]
    detection_mode = params.get("simulation", {}).get("detection_mode", "fourfold")

    effective_pr_angles = sample_effective_pr_angles(params)
    rotated_state = apply_pr_rotations_to_state(state_vector, effective_pr_angles)

    ideal_probabilities = joint_pattern_probabilities_in_standard_basis(rotated_state)
    single_result = simulate_single_state_transmission(state_label, params)

    return {
        "sent_state": state_label,
        "sent_bits": STATE_TO_BITS[state_label],
        "detection_mode": detection_mode,
        "effective_pr_angles": single_result["effective_pr_angles"],
        "initial_state_amplitudes": state_vector_to_amplitude_table(state_vector),
        "rotated_state_amplitudes": state_vector_to_amplitude_table(rotated_state),
        "ideal_probability_table": probability_dict_to_dataframe(ideal_probabilities),
        "ideal_pattern": single_result["ideal_pattern"],
        "observed_pattern": single_result["observed_pattern"],
        "detected_channels": single_result["detected_channels"],
        "arrival_times": single_result["arrival_times"],
        "timing_spread": single_result["timing_spread"],
        "coincidence_window": single_result["coincidence_window"],
        "coincidence_passed": single_result["coincidence_passed"],
        "timing_anomaly": single_result["timing_anomaly"],
        "packet_detected": single_result["packet_detected"],
        "fourfold_detected": single_result["fourfold_detected"],
        "full_pattern_available": single_result["full_pattern_available"],
        "postselection_passed": single_result["postselection_passed"],
        "rejection_reason": single_result["rejection_reason"],
        "packet_status": single_result["packet_status"],
        "packet_status_label": single_result["packet_status_label"],
        "display_decoded_state": single_result["display_decoded_state"],
        "is_physically_lost": single_result["is_physically_lost"],
        "is_rejected_by_postselection": single_result["is_rejected_by_postselection"],
        "channel_report": single_result["channel_report"],
        "decoded_state": single_result["decoded_state"],
        "decoded_bits": single_result["decoded_bits"],
        "decoding_confidence": single_result["decoding_confidence"],
        "is_correct": single_result["is_correct"],
        "ideal_probability_of_sampled_pattern": float(ideal_probabilities.get(single_result["ideal_pattern"], 0.0)),
        "observed_pattern_same_as_ideal": single_result["observed_pattern"] == single_result["ideal_pattern"],
    }


def state_norm_value(state_vector: np.ndarray) -> float:
    return float(np.linalg.norm(state_vector))


def build_probability_normalization_table(params: dict) -> pd.DataFrame:
    rows = []

    fixed_pr_angles = {
        "pr_1": params["pr"]["pr_1"]["angle"],
        "pr_2": params["pr"]["pr_2"]["angle"],
        "pr_3": params["pr"]["pr_3"]["angle"],
        "pr_4": params["pr"]["pr_4"]["angle"],
    }

    for state_label, state_vector in ARTICLE_STATE_VECTORS.items():
        rotated_state = apply_pr_rotations_to_state(state_vector, fixed_pr_angles)
        probabilities = joint_pattern_probabilities_in_standard_basis(rotated_state)
        probability_values = list(probabilities.values())

        rows.append({
            "state": state_label,
            "initial_norm": state_norm_value(state_vector),
            "rotated_norm": state_norm_value(rotated_state),
            "probability_sum": float(sum(probability_values)),
            "min_probability": float(min(probability_values)),
            "max_probability": float(max(probability_values)),
            "negative_probability_count": int(sum(1 for value in probability_values if value < -1e-12)),
        })

    return pd.DataFrame(rows)


def build_decoder_snapshot_table(params: dict) -> pd.DataFrame:
    rows = []

    fixed_pr_angles = {
        "pr_1": params["pr"]["pr_1"]["angle"],
        "pr_2": params["pr"]["pr_2"]["angle"],
        "pr_3": params["pr"]["pr_3"]["angle"],
        "pr_4": params["pr"]["pr_4"]["angle"],
    }

    for state_label, state_vector in ARTICLE_STATE_VECTORS.items():
        rotated_state = apply_pr_rotations_to_state(state_vector, fixed_pr_angles)
        probabilities = joint_pattern_probabilities_in_standard_basis(rotated_state)
        most_likely_pattern, most_likely_probability = max(probabilities.items(), key=lambda item: item[1])
        decoded_state, decoded_probability = decode_state_from_pattern_with_pr(
            most_likely_pattern,
            fixed_pr_angles,
        )

        rows.append({
            "state": state_label,
            "bits": STATE_TO_BITS[state_label],
            "most_likely_pattern": format_pattern_tuple(most_likely_pattern),
            "pattern_probability": float(most_likely_probability),
            "decoded_from_most_likely_pattern": decoded_state,
            "decoder_probability": float(decoded_probability),
            "decoded_correctly": decoded_state == state_label,
        })

    return pd.DataFrame(rows)


def build_physics_model_check(params: dict) -> dict:
    normalization_df = build_probability_normalization_table(params)
    decoder_snapshot_df = build_decoder_snapshot_table(params)

    probability_sum_ok = bool((normalization_df["probability_sum"].sub(1.0).abs() < 1e-9).all())
    norm_ok = bool((normalization_df["initial_norm"].sub(1.0).abs() < 1e-9).all() and (normalization_df["rotated_norm"].sub(1.0).abs() < 1e-9).all())
    non_negative_ok = bool((normalization_df["negative_probability_count"] == 0).all() and (normalization_df["min_probability"] >= -1e-12).all())

    return {
        "physics_model": params.get("simulation", {}).get("physics_model", "article_pr_standard_basis"),
        "normalization_df": normalization_df,
        "decoder_snapshot_df": decoder_snapshot_df,
        "probability_sum_ok": probability_sum_ok,
        "norm_ok": norm_ok,
        "non_negative_ok": non_negative_ok,
    }


def summarize_rejection_stats(results: list[dict]) -> dict:
    stats = {
        "accepted": 0,
        "failed_postselection": 0,
        "not_fourfold": 0,
        "failed_coincidence": 0,
        "channel_loss_related": 0,
        "detector_miss_related": 0,
        "no_channels_detected": 0,
        "rejected_timing": 0,
        "lost_channel": 0,
        "detector_miss": 0,
        "rejected_not_fourfold": 0,
        "rejected_postselection": 0,
        "physically_lost": 0,
    }

    for result in results:
        packet_status = result.get("packet_status", "unknown")

        if result["postselection_passed"]:
            stats["accepted"] += 1
            continue

        stats["failed_postselection"] += 1

        if packet_status in stats:
            stats[packet_status] += 1

        if result.get("is_physically_lost", False):
            stats["physically_lost"] += 1

        if not result["fourfold_detected"]:
            stats["not_fourfold"] += 1

        if not result["coincidence_passed"]:
            stats["failed_coincidence"] += 1

        if result["rejection_reason"] == "no channels detected":
            stats["no_channels_detected"] += 1

        if any(row["lost_in_channel"] for row in result["channel_report"]):
            stats["channel_loss_related"] += 1

        if any(row["detector_miss"] for row in result["channel_report"]):
            stats["detector_miss_related"] += 1

    return stats



def combined_channel_loss(channel_name: str, params: dict) -> float:
    channel_loss = params["channels"][channel_name]["loss"]

    if channel_name in ["channel_2", "channel_3"]:
        beam_splitter_loss = params["beam_splitters"]["bs_right"]["loss"]
    else:
        beam_splitter_loss = params["beam_splitters"]["bs_left"]["loss"]

    return min(1.0, channel_loss + beam_splitter_loss)


def estimate_expected_fourfold_rate(params: dict) -> float:
    rate = 1.0

    for idx, channel_name in enumerate(["channel_1", "channel_2", "channel_3", "channel_4"], start=1):
        detector_name = f"detector_{idx}"
        survival_probability = 1.0 - combined_channel_loss(channel_name, params)
        detection_probability = params["detectors"][detector_name]["eta"]
        rate *= survival_probability * detection_probability

    return max(0.0, min(1.0, rate))


def estimate_expected_timing_status(params: dict) -> dict:
    speed = params["timing"]["speed"]
    window = params["timing"]["coincidence_window"]

    expected_arrival_times = []
    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        channel = params["channels"][channel_name]
        arrival_time = channel["length"] / speed
        if channel["eve"]:
            arrival_time += channel.get("eve_delay", 0.0)
        expected_arrival_times.append(arrival_time)

    expected_spread = max(expected_arrival_times) - min(expected_arrival_times)
    expected_coincidence_passed = expected_spread <= window

    return {
        "expected_arrival_times": expected_arrival_times,
        "expected_timing_spread": expected_spread,
        "expected_coincidence_passed": expected_coincidence_passed,
    }


def build_expected_vs_observed_stats(sequence_result: dict, params: dict, tolerance: float = 0.10) -> dict:
    total_sent = sequence_result["total_sent"]
    expected_fourfold_rate = estimate_expected_fourfold_rate(params)
    timing_status = estimate_expected_timing_status(params)

    expected_postselection_rate = (
        expected_fourfold_rate if timing_status["expected_coincidence_passed"] else 0.0
    )

    observed_fourfold_rate = sequence_result["fourfold_rate"]
    observed_postselection_rate = sequence_result["postselection_rate"]

    fourfold_delta = observed_fourfold_rate - expected_fourfold_rate
    postselection_delta = observed_postselection_rate - expected_postselection_rate

    timing_anomaly_count = sequence_result.get("total_timing_anomaly", 0)
    timing_anomaly_rate = timing_anomaly_count / total_sent if total_sent else 0.0

    possible_anomaly = (
        abs(fourfold_delta) > tolerance
        or abs(postselection_delta) > tolerance
        or timing_anomaly_rate > tolerance
    )

    summary_rows = [
        {
            "metric": "fourfold_rate",
            "expected": expected_fourfold_rate,
            "observed": observed_fourfold_rate,
            "delta_observed_minus_expected": fourfold_delta,
        },
        {
            "metric": "postselection_rate",
            "expected": expected_postselection_rate,
            "observed": observed_postselection_rate,
            "delta_observed_minus_expected": postselection_delta,
        },
        {
            "metric": "timing_anomaly_rate",
            "expected": 0.0,
            "observed": timing_anomaly_rate,
            "delta_observed_minus_expected": timing_anomaly_rate,
        },
    ]

    return {
        "summary_df": pd.DataFrame(summary_rows),
        "expected_fourfold_rate": expected_fourfold_rate,
        "observed_fourfold_rate": observed_fourfold_rate,
        "expected_postselection_rate": expected_postselection_rate,
        "observed_postselection_rate": observed_postselection_rate,
        "fourfold_delta": fourfold_delta,
        "postselection_delta": postselection_delta,
        "timing_anomaly_count": timing_anomaly_count,
        "timing_anomaly_rate": timing_anomaly_rate,
        "possible_anomaly": possible_anomaly,
        "tolerance": tolerance,
        **timing_status,
    }

def simulate_state_sequence(state_sequence: list[str], params: dict) -> dict:
    results = []

    confusion_matrix = {
        "psi1": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi2": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi3": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi4": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
    }

    total_sent = len(state_sequence)
    total_detected = 0
    total_lost = 0
    total_correct = 0
    total_fourfold = 0
    total_postselected = 0
    total_coincidence_passed = 0
    total_timing_anomaly = 0

    for state_label in state_sequence:
        result = simulate_single_state_transmission(state_label, params)
        results.append(result)

        if result["packet_detected"]:
            total_detected += 1

        if result["fourfold_detected"]:
            total_fourfold += 1

        if result["coincidence_passed"]:
            total_coincidence_passed += 1

        if result.get("timing_anomaly", False):
            total_timing_anomaly += 1

        if result["postselection_passed"]:
            total_postselected += 1
            decoded_state = result["decoded_state"]
            confusion_matrix[state_label][decoded_state] += 1

            if result["is_correct"]:
                total_correct += 1
        else:
            total_lost += 1

    detection_rate = total_detected / total_sent if total_sent else 0.0
    fourfold_rate = total_fourfold / total_sent if total_sent else 0.0
    postselection_rate = total_postselected / total_sent if total_sent else 0.0
    coincidence_rate = total_coincidence_passed / total_sent if total_sent else 0.0
    symbol_accuracy = total_correct / total_postselected if total_postselected else 0.0
    loss_rate = total_lost / total_sent if total_sent else 0.0

    return {
        "results": results,
        "confusion_matrix": confusion_matrix,
        "total_sent": total_sent,
        "total_detected": total_detected,
        "total_fourfold": total_fourfold,
        "total_postselected": total_postselected,
        "total_coincidence_passed": total_coincidence_passed,
        "total_timing_anomaly": total_timing_anomaly,
        "total_lost": total_lost,
        "total_correct": total_correct,
        "detection_rate": detection_rate,
        "fourfold_rate": fourfold_rate,
        "postselection_rate": postselection_rate,
        "coincidence_rate": coincidence_rate,
        "symbol_accuracy": symbol_accuracy,
        "loss_rate": loss_rate,
        "detection_mode": params.get("simulation", {}).get("detection_mode", "fourfold"),
        "rejection_stats": summarize_rejection_stats(results),
    }


def recovered_bits_from_results(results: list[dict], fill_missing: str = "??") -> str:
    recovered_chunks = []

    for result in results:
        if result["decoded_bits"] is None:
            recovered_chunks.append(fill_missing)
        else:
            recovered_chunks.append(result["decoded_bits"])

    return "".join(recovered_chunks)


def keep_only_binary_chars(bitstring: str) -> str:
    return "".join(ch for ch in bitstring if ch in "01")


def build_message_transmission_summary(text: str, params: dict) -> dict:
    encoded = encode_text_to_states(text)
    sequence_result = simulate_state_sequence(encoded["states"], params)
    expected_observed_stats = build_expected_vs_observed_stats(sequence_result, params)

    recovered_bits_raw = recovered_bits_from_results(sequence_result["results"])
    recovered_bits_clean = keep_only_binary_chars(recovered_bits_raw)
    recovered_text = bitstring_to_text(recovered_bits_clean)

    ber_stats = compute_bit_error_rate(encoded["bitstring"], recovered_bits_raw)
    ser_stats = compute_symbol_error_rate(sequence_result["results"])
    bit_comparison_df = build_bit_comparison_table(
        encoded["bit_pairs"],
        sequence_result["results"],
    )

    return {
        "original_text": text,
        "original_bitstring": encoded["bitstring"],
        "bit_pairs": encoded["bit_pairs"],
        "sent_states": encoded["states"],
        "sequence_result": sequence_result,
        "expected_observed_stats": expected_observed_stats,
        "recovered_bits_raw": recovered_bits_raw,
        "recovered_bits_clean": recovered_bits_clean,
        "recovered_text": recovered_text,
        "ber_stats": ber_stats,
        "ser_stats": ser_stats,
        "bit_comparison_df": bit_comparison_df,
    }


def clone_params_without_eve(params):
    cloned = {
        "source": {
            "message": params["source"]["message"],
            "num_packets": params["source"]["num_packets"],
            "pair_generation_efficiency": params["source"]["pair_generation_efficiency"],
            "mode": params["source"]["mode"],
            "article_state_label": params["source"]["article_state_label"],
            "selected_state_label": params["source"]["selected_state_label"],
            "state_angles": params["source"]["state_angles"].copy(),
        },
        "channels": {},
        "pr": {},
        "detectors": {},
        "beam_splitters": {},
        "simulation": params.get("simulation", {}).copy(),
        "timing": params.get("timing", {}).copy(),
    }

    for ch_name, ch_data in params["channels"].items():
        cloned["channels"][ch_name] = {
            "loss": ch_data["loss"],
            "eve": False,
            "eve_mode": ch_data.get("eve_mode", "disturbance_only"),
            "eve_disturbance": ch_data["eve_disturbance"],
            "eve_delay": ch_data.get("eve_delay", 0.0),
            "length": ch_data.get("length", 10.0),
        }

    for pr_name, pr_data in params["pr"].items():
        cloned["pr"][pr_name] = pr_data.copy()

    for det_name, det_data in params["detectors"].items():
        cloned["detectors"][det_name] = det_data.copy()

    for bs_name, bs_data in params["beam_splitters"].items():
        cloned["beam_splitters"][bs_name] = bs_data.copy()

    return cloned


def clone_ideal_params(params: dict) -> dict:
    cloned = {
        "source": {
            "message": params["source"]["message"],
            "num_packets": params["source"]["num_packets"],
            "pair_generation_efficiency": 1.0,
            "mode": params["source"]["mode"],
            "article_state_label": params["source"]["article_state_label"],
            "selected_state_label": params["source"]["selected_state_label"],
            "state_angles": params["source"]["state_angles"].copy(),
        },
        "channels": {},
        "pr": {},
        "detectors": {},
        "beam_splitters": {},
        "simulation": params.get("simulation", {}).copy(),
        "timing": params.get("timing", {}).copy(),
    }

    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        cloned["channels"][channel_name] = {
            "loss": 0.0,
            "eve": False,
            "eve_mode": "disturbance_only",
            "eve_disturbance": 0.0,
            "eve_delay": 0.0,
            "length": params["channels"][channel_name].get("length", 10.0),
        }

    for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
        cloned["pr"][pr_name] = {
            "angle": params["pr"][pr_name]["angle"],
            "error": 0.0,
        }

    for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
        cloned["detectors"][detector_name] = {
            "eta": 1.0,
            "dark": 0.0,
        }

    cloned["beam_splitters"]["bs_left"] = {"loss": 0.0}
    cloned["beam_splitters"]["bs_right"] = {"loss": 0.0}

    return cloned


def run_ideal_self_test(trials_per_state: int, params: dict) -> dict:
    ideal_params = clone_ideal_params(params)

    confusion_matrix = {
        "psi1": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi2": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi3": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi4": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
    }

    rows = []

    for state_label in ["psi1", "psi2", "psi3", "psi4"]:
        correct_count = 0
        detected_count = 0
        fourfold_count = 0
        postselection_count = 0
        coincidence_count = 0

        for _ in range(trials_per_state):
            result = simulate_single_state_transmission(state_label, ideal_params)

            if result["packet_detected"]:
                detected_count += 1

            if result["fourfold_detected"]:
                fourfold_count += 1

            if result["coincidence_passed"]:
                coincidence_count += 1

            if result["postselection_passed"]:
                postselection_count += 1
                decoded_state = result["decoded_state"]
                confusion_matrix[state_label][decoded_state] += 1

                if decoded_state == state_label:
                    correct_count += 1

        accuracy = correct_count / postselection_count if postselection_count else 0.0

        rows.append({
            "state": state_label,
            "trials": trials_per_state,
            "detected": detected_count,
            "fourfold_detected": fourfold_count,
            "coincidence_passed": coincidence_count,
            "postselection_passed": postselection_count,
            "correct": correct_count,
            "accuracy": accuracy,
        })

    confusion_df = pd.DataFrame(confusion_matrix).T
    confusion_percent_df = confusion_df.div(confusion_df.sum(axis=1).replace(0, 1), axis=0) * 100.0
    summary_df = pd.DataFrame(rows)

    return {
        "summary_df": summary_df,
        "confusion_df": confusion_df,
        "confusion_percent_df": confusion_percent_df,
    }


def build_simulation_bundle(params: dict) -> dict:
    result_attack = run_simple_simulation(params)
    params_no_eve = clone_params_without_eve(params)
    result_no_eve = run_simple_simulation(params_no_eve)

    message_attack = build_message_transmission_summary(params["source"]["message"], params)
    message_no_eve = build_message_transmission_summary(params["source"]["message"], params_no_eve)

    return {
        "result_attack": result_attack,
        "result_no_eve": result_no_eve,
        "message_attack": message_attack,
        "message_no_eve": message_no_eve,
        "params_no_eve": params_no_eve,
    }


def plot_confusion_heatmap(confusion_percent_df):
    fig, ax = plt.subplots(figsize=(6, 5))

    matrix = confusion_percent_df.values
    im = ax.imshow(matrix, aspect="auto")

    ax.set_xticks(range(len(confusion_percent_df.columns)))
    ax.set_xticklabels(confusion_percent_df.columns)

    ax.set_yticks(range(len(confusion_percent_df.index)))
    ax.set_yticklabels(confusion_percent_df.index)

    ax.set_xlabel("Decoded state")
    ax.set_ylabel("Sent state")
    ax.set_title("Confusion Matrix Heatmap (%)")

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center")

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    return fig


def plot_difference_heatmap(diff_df):
    fig, ax = plt.subplots(figsize=(6, 5))

    matrix = diff_df.values
    im = ax.imshow(matrix, aspect="auto", vmin=-100, vmax=100, cmap="bwr")

    ax.set_xticks(range(len(diff_df.columns)))
    ax.set_xticklabels(diff_df.columns)

    ax.set_yticks(range(len(diff_df.index)))
    ax.set_yticklabels(diff_df.index)

    ax.set_xlabel("Decoded state")
    ax.set_ylabel("Sent state")
    ax.set_title("Difference Heatmap: With Eve - Without Eve (%)")

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.1f}", ha="center", va="center")

    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    return fig


def generate_text_analysis(result_no_eve, result_attack):
    lines = []

    source_mode = result_attack["source_mode"]
    selected_state = result_attack["selected_state_label"]
    detection_mode = result_attack.get("detection_mode", "unknown")

    detected_no_eve = result_no_eve["detected"]
    detected_attack = result_attack["detected"]

    errors_no_eve = result_no_eve["errors"]
    errors_attack = result_attack["errors"]

    success_no_eve = result_no_eve["success_rate"]
    success_attack = result_attack["success_rate"]

    qber_no_eve = result_no_eve["qber"]
    qber_attack = result_attack["qber"]

    delta_detected = detected_attack - detected_no_eve
    delta_errors = errors_attack - errors_no_eve
    delta_success = success_attack - success_no_eve
    delta_qber = qber_attack - qber_no_eve

    lines.append("### Textual analysis of results")
    lines.append("")
    lines.append(
        f"The simulation was run in **{source_mode}** mode"
        + (f" with source state **{selected_state}**." if source_mode == "article_state" else ".")
    )
    lines.append(f"Detection mode was **{detection_mode}**.")
    lines.append("")

    lines.append("**1. Detection efficiency**")
    if detected_attack > detected_no_eve:
        lines.append(
            f"With Eve, the number of detected packets increased from **{detected_no_eve}** to **{detected_attack}** "
            f"(change: **{delta_detected:+d}**)."
        )
    elif detected_attack < detected_no_eve:
        lines.append(
            f"With Eve, the number of detected packets decreased from **{detected_no_eve}** to **{detected_attack}** "
            f"(change: **{delta_detected:+d}**)."
        )
    else:
        lines.append(f"The number of detected packets stayed the same: **{detected_no_eve}**.")

    lines.append("")
    lines.append("**2. Error behaviour / QBER**")
    if qber_attack > qber_no_eve:
        lines.append(
            f"The QBER increased from **{qber_no_eve:.3f}** to **{qber_attack:.3f}** "
            f"(change: **{delta_qber:+.3f}**), and the number of errors changed from "
            f"**{errors_no_eve}** to **{errors_attack}** (**{delta_errors:+d}**)."
        )
    elif qber_attack < qber_no_eve:
        lines.append(
            f"The QBER decreased from **{qber_no_eve:.3f}** to **{qber_attack:.3f}** "
            f"(change: **{delta_qber:+.3f}**)."
        )
    else:
        lines.append(f"The QBER remained unchanged at **{qber_attack:.3f}**.")

    lines.append("")
    lines.append("**3. Success rate**")
    if success_attack > success_no_eve:
        lines.append(
            f"The success rate increased from **{success_no_eve:.3f}** to **{success_attack:.3f}** "
            f"(change: **{delta_success:+.3f}**)."
        )
    elif success_attack < success_no_eve:
        lines.append(
            f"The success rate decreased from **{success_no_eve:.3f}** to **{success_attack:.3f}** "
            f"(change: **{delta_success:+.3f}**)."
        )
    else:
        lines.append(f"The success rate remained the same at **{success_attack:.3f}**.")

    lines.append("")
    if source_mode == "article_state":
        lines.append("**4. State decoding interpretation**")
        confusion_attack_df = pd.DataFrame(result_attack["confusion_matrix"]).T
        row_sums_attack = confusion_attack_df.sum(axis=1).replace(0, 1)
        confusion_attack_percent_df = (confusion_attack_df.div(row_sums_attack, axis=0) * 100)

        if selected_state in confusion_attack_percent_df.index:
            row = confusion_attack_percent_df.loc[selected_state]
            best_decoded = row.idxmax()
            best_value = row.max()

            lines.append(
                f"For the sent state **{selected_state}**, the most frequent decoded state was "
                f"**{best_decoded}** with probability about **{best_value:.1f}%**."
            )

    lines.append("")
    lines.append("**5. Relation to the article**")
    lines.append(
        "At this stage, the application is functioning as a simplified transmission model based on the article’s 4-photon state structure, "
        "4 channels, polarization rotations, detector efficiencies, channel disturbance, and coincidence timing."
    )

    return "\n".join(lines)


def generate_message_level_analysis(summary_no_eve, summary_attack):
    seq_no_eve = summary_no_eve["sequence_result"]
    seq_attack = summary_attack["sequence_result"]

    ber_no_eve = summary_no_eve["ber_stats"]["ber"]
    ber_attack = summary_attack["ber_stats"]["ber"]

    ser_no_eve = summary_no_eve["ser_stats"]["ser"]
    ser_attack = summary_attack["ser_stats"]["ser"]

    detection_mode = summary_attack["sequence_result"].get("detection_mode", "unknown")

    lines = []
    lines.append("### Message-level analysis")
    lines.append("")
    lines.append(f"Original text: **{summary_attack['original_text']}**")
    lines.append(f"Detection mode: **{detection_mode}**")
    lines.append("")
    lines.append("**1. Detection statistics**")
    lines.append(
        f"Without Eve, **{seq_no_eve['total_postselected']}** out of **{seq_no_eve['total_sent']}** "
        f"2-bit blocks passed postselection (**{seq_no_eve['postselection_rate']:.3f}**)."
    )
    lines.append(
        f"With Eve, **{seq_attack['total_postselected']}** out of **{seq_attack['total_sent']}** "
        f"2-bit blocks passed postselection (**{seq_attack['postselection_rate']:.3f}**)."
    )
    lines.append("")
    lines.append("**2. Symbol-level accuracy**")
    lines.append(f"Without Eve, SER = **{ser_no_eve:.3f}**.")
    lines.append(f"With Eve, SER = **{ser_attack:.3f}**.")
    lines.append("")
    lines.append("**3. Bit-level accuracy**")
    lines.append(f"Without Eve, BER = **{ber_no_eve:.3f}**.")
    lines.append(f"With Eve, BER = **{ber_attack:.3f}**.")
    lines.append("")
    lines.append("**4. Recovered text**")
    lines.append(f"Without Eve: `{summary_no_eve['recovered_text']}`")
    lines.append(f"With Eve: `{summary_attack['recovered_text']}`")

    return "\n".join(lines)


def run_simple_simulation(params):
    message = params["source"]["message"]
    num_packets = params["source"]["num_packets"]
    pair_eff = params["source"]["pair_generation_efficiency"]
    source_mode = params["source"]["mode"]
    selected_state_label = params["source"].get("selected_state_label", "manual")

    transmitted = 0
    detected = 0
    errors = 0

    active_eve_channels = [
        ch for ch, v in params["channels"].items()
        if v["eve"]
    ]

    channel_names = ["channel_1", "channel_2", "channel_3", "channel_4"]

    decoded_state_counts = {
        "psi1": 0,
        "psi2": 0,
        "psi3": 0,
        "psi4": 0,
        "manual": 0,
    }

    confusion_matrix = {
        "psi1": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi2": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi3": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
        "psi4": {"psi1": 0, "psi2": 0, "psi3": 0, "psi4": 0},
    }

    postselected = 0

    for _ in range(num_packets):
        if random.random() > pair_eff:
            continue

        transmitted += 1
        packet_detected = False
        packet_error = False

        if source_mode == "article_state" and selected_state_label in ARTICLE_STATE_VECTORS:
            single_result = simulate_single_state_transmission(selected_state_label, params)
            packet_detected = single_result["packet_detected"]

            if single_result["postselection_passed"]:
                postselected += 1
                decoded_state = single_result["decoded_state"]
                decoded_state_counts[decoded_state] += 1
                confusion_matrix[selected_state_label][decoded_state] += 1

                if not single_result["is_correct"]:
                    packet_error = True

        else:
            for idx, channel_name in enumerate(channel_names, start=1):
                pr_name = f"pr_{idx}"
                detector_name = f"detector_{idx}"

                channel = params["channels"][channel_name]
                pr = params["pr"][pr_name]
                detector = params["detectors"][detector_name]

                loss_prob = channel["loss"]
                if channel_name in ["channel_2", "channel_3"]:
                    loss_prob = min(1.0, loss_prob + params["beam_splitters"]["bs_right"]["loss"])
                else:
                    loss_prob = min(1.0, loss_prob + params["beam_splitters"]["bs_left"]["loss"])

                if random.random() < loss_prob:
                    continue

                channel_state_angle = params["source"]["state_angles"][channel_name]

                p_quantum = quantum_measurement_probability(
                    state_angle_deg=channel_state_angle,
                    pr_angle_deg=pr["angle"],
                    pr_error=pr["error"],
                )

                eve_disturbance = channel.get("eve_disturbance", 0.0) if channel["eve"] else 0.0
                p_click = p_quantum * detector["eta"]
                click = random.random() < p_click

                if not click and random.random() < detector["dark"]:
                    click = True

                if channel["eve"] and random.random() < eve_disturbance:
                    click = not click

                if click:
                    packet_detected = True

                    basis_error = 1.0 - p_quantum
                    local_error_probability = min(1.0, basis_error + eve_disturbance)

                    if random.random() < local_error_probability:
                        packet_error = True

            if packet_detected:
                decoded_state_counts["manual"] += 1

        if packet_detected:
            detected += 1
            if packet_error:
                errors += 1

    success_rate = detected / num_packets if num_packets else 0.0
    qber = errors / postselected if postselected else 0.0

    return {
        "message": message,
        "num_packets": num_packets,
        "transmitted": transmitted,
        "detected": detected,
        "postselected": postselected,
        "errors": errors,
        "success_rate": success_rate,
        "qber": qber,
        "eve_channels": active_eve_channels,
        "selected_state_label": selected_state_label,
        "source_mode": source_mode,
        "decoded_state_counts": decoded_state_counts,
        "confusion_matrix": confusion_matrix,
        "detection_mode": params.get("simulation", {}).get("detection_mode", "fourfold"),
    }



# ============================================================
# Validation suite helpers
# ============================================================

def make_validation_ideal_params(params: dict) -> dict:
    validation_params = copy.deepcopy(params)

    validation_params["source"]["mode"] = "article_state"
    validation_params["source"]["selected_state_label"] = "psi1"
    validation_params["source"]["article_state_label"] = "psi1"
    validation_params["source"]["pair_generation_efficiency"] = 1.0
    validation_params["simulation"]["detection_mode"] = "fourfold"

    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        validation_params["channels"][channel_name]["loss"] = 0.0
        validation_params["channels"][channel_name]["eve"] = False
        validation_params["channels"][channel_name]["eve_mode"] = "disturbance_only"
        validation_params["channels"][channel_name]["eve_disturbance"] = 0.0
        validation_params["channels"][channel_name]["eve_delay"] = 0.0
        validation_params["channels"][channel_name]["length"] = 10.0

    for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
        validation_params["detectors"][detector_name]["eta"] = 1.0
        validation_params["detectors"][detector_name]["dark"] = 0.0

    for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
        validation_params["pr"][pr_name]["angle"] = 0.0
        validation_params["pr"][pr_name]["error"] = 0.0

    validation_params["beam_splitters"]["bs_left"]["loss"] = 0.0
    validation_params["beam_splitters"]["bs_right"]["loss"] = 0.0

    validation_params["timing"]["speed"] = 2e8
    validation_params["timing"]["coincidence_window"] = 2e-9
    validation_params["timing"]["detector_jitter"] = 0.0

    return validation_params


def make_validation_realistic_params(params: dict) -> dict:
    validation_params = make_validation_ideal_params(params)

    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        validation_params["channels"][channel_name]["loss"] = 0.05
        validation_params["channels"][channel_name]["eve"] = False
        validation_params["channels"][channel_name]["eve_mode"] = "disturbance_only"
        validation_params["channels"][channel_name]["eve_delay"] = 0.0

    for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
        validation_params["detectors"][detector_name]["eta"] = 0.85
        validation_params["detectors"][detector_name]["dark"] = 0.0

    validation_params["beam_splitters"]["bs_left"]["loss"] = 0.02
    validation_params["beam_splitters"]["bs_right"]["loss"] = 0.02
    validation_params["timing"]["detector_jitter"] = 0.2e-9

    return validation_params


def make_validation_eve_delay_params(params: dict) -> dict:
    validation_params = make_validation_ideal_params(params)
    validation_params["channels"]["channel_2"]["eve"] = True
    validation_params["channels"]["channel_2"]["eve_mode"] = "passive_monitor"
    validation_params["channels"]["channel_2"]["eve_delay"] = 5e-9
    validation_params["timing"]["detector_jitter"] = 0.0
    return validation_params


def validation_result_row(test_name: str, passed: bool, metric: str, comment: str) -> dict:
    return {
        "test": test_name,
        "result": "PASS" if passed else "FAIL",
        "key_metric": metric,
        "comment": comment,
    }


def run_validation_suite(params: dict, trials_per_state: int = 100, sequence_repeats: int = 200) -> dict:
    rows = []
    details = {}

    # 1. Ideal channel test
    ideal_params = make_validation_ideal_params(params)
    ideal_result = run_ideal_self_test(trials_per_state, ideal_params)
    ideal_summary = ideal_result["summary_df"]

    ideal_accuracy_ok = bool((ideal_summary["accuracy"] == 1.0).all())
    ideal_postselection_ok = bool((ideal_summary["postselection_passed"] == trials_per_state).all())
    ideal_passed = ideal_accuracy_ok and ideal_postselection_ok

    rows.append(validation_result_row(
        "Ideal channel",
        ideal_passed,
        f"min accuracy={ideal_summary['accuracy'].min():.3f}, min postselection={int(ideal_summary['postselection_passed'].min())}/{trials_per_state}",
        "All states should be decoded perfectly in the ideal fourfold/postselection channel.",
    ))
    details["ideal_self_test_summary"] = ideal_summary

    # 2. psi3 0000 regression test
    psi3_params = make_validation_ideal_params(params)
    fixed_angles = {"pr_1": 0.0, "pr_2": 0.0, "pr_3": 0.0, "pr_4": 0.0}
    observed_pattern, detected_channels, channel_report = apply_channel_and_detector_effects(
        (0, 0, 0, 0),
        psi3_params,
    )
    detection_status = evaluate_detection_status(detected_channels, "fourfold")
    timing_result = simulate_arrival_times(detected_channels, psi3_params)
    postselection_passed = (
        detection_status["fourfold_detected"]
        and detection_status["full_pattern_available"]
        and timing_result["coincidence_passed"]
    )
    decoded_state, decoded_probability = decode_state_from_pattern_with_pr(observed_pattern, fixed_angles)
    psi3_passed = bool(
        observed_pattern == (0, 0, 0, 0)
        and all(detected_channels)
        and postselection_passed
        and decoded_state == "psi3"
    )
    rows.append(validation_result_row(
        "psi3 0000 regression",
        psi3_passed,
        f"observed={format_pattern_tuple(observed_pattern)}, decoded={decoded_state}, postselection={postselection_passed}",
        "The valid xxxx polarization outcome must not be treated as no-click/lost.",
    ))
    details["psi3_0000"] = {
        "observed_pattern": observed_pattern,
        "detected_channels": detected_channels,
        "postselection_passed": postselection_passed,
        "decoded_state": decoded_state,
        "decoded_probability": decoded_probability,
    }

    # 3. Realistic baseline test
    realistic_params = make_validation_realistic_params(params)
    state_sequence = ["psi1", "psi2", "psi3", "psi4"] * sequence_repeats
    realistic_sequence = simulate_state_sequence(state_sequence, realistic_params)
    realistic_stats = build_expected_vs_observed_stats(realistic_sequence, realistic_params, tolerance=0.12)

    realistic_fourfold_delta = abs(realistic_stats["fourfold_delta"])
    realistic_timing_anomaly_rate = realistic_stats["timing_anomaly_rate"]
    realistic_passed = bool(
        realistic_fourfold_delta <= 0.12
        and realistic_timing_anomaly_rate <= 0.05
        and realistic_sequence["symbol_accuracy"] >= 0.95
    )
    rows.append(validation_result_row(
        "Realistic baseline without Eve",
        realistic_passed,
        f"expected fourfold={realistic_stats['expected_fourfold_rate']:.3f}, observed={realistic_stats['observed_fourfold_rate']:.3f}, timing anomaly={realistic_timing_anomaly_rate:.3f}",
        "Observed fourfold rate should roughly match the no-attack estimate; timing anomalies should be rare.",
    ))
    details["realistic_expected_vs_observed"] = realistic_stats["summary_df"]
    details["realistic_rejection_stats"] = realistic_sequence["rejection_stats"]

    # 4. Eve delay timing test
    eve_params = make_validation_eve_delay_params(params)
    eve_sequence = simulate_state_sequence(state_sequence, eve_params)
    eve_timing_anomaly_rate = eve_sequence["total_timing_anomaly"] / eve_sequence["total_sent"] if eve_sequence["total_sent"] else 0.0
    eve_postselection_rate = eve_sequence["postselection_rate"]
    eve_passed = bool(eve_timing_anomaly_rate >= 0.95 and eve_postselection_rate <= 0.05)

    rows.append(validation_result_row(
        "Eve delay timing rejection",
        eve_passed,
        f"timing anomaly={eve_timing_anomaly_rate:.3f}, postselection={eve_postselection_rate:.3f}",
        "With 5 ns delay and a 2 ns coincidence window, packets should be rejected by timing.",
    ))
    details["eve_delay_rejection_stats"] = eve_sequence["rejection_stats"]

    validation_df = pd.DataFrame(rows)
    all_passed = bool((validation_df["result"] == "PASS").all())

    return {
        "all_passed": all_passed,
        "validation_df": validation_df,
        "details": details,
        "trials_per_state": trials_per_state,
        "sequence_repeats": sequence_repeats,
    }


# ============================================================
# Parameter sweep helpers
# ============================================================

def make_sweep_base_params(params: dict) -> dict:
    """Stable baseline for sweep experiments: article state, fourfold, no Eve by default."""
    sweep_params = make_validation_realistic_params(params)
    sweep_params["source"]["mode"] = "article_state"
    sweep_params["source"]["selected_state_label"] = "psi1"
    sweep_params["source"]["article_state_label"] = "psi1"
    sweep_params["source"]["pair_generation_efficiency"] = 1.0
    sweep_params["simulation"]["detection_mode"] = "fourfold"
    sweep_params["timing"]["detector_jitter"] = 0.0
    return sweep_params


def set_all_detector_eta(params: dict, eta_value: float) -> None:
    for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
        params["detectors"][detector_name]["eta"] = float(eta_value)


def set_all_channel_loss(params: dict, loss_value: float) -> None:
    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        params["channels"][channel_name]["loss"] = float(loss_value)


def reset_all_eve(params: dict) -> None:
    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        params["channels"][channel_name]["eve"] = False
        params["channels"][channel_name]["eve_mode"] = "disturbance_only"
        params["channels"][channel_name]["eve_delay"] = 0.0
        params["channels"][channel_name]["eve_disturbance"] = 0.0


def summarize_sequence_for_sweep(sequence_result: dict, params: dict, parameter_name: str, parameter_value: float) -> dict:
    expected_stats = build_expected_vs_observed_stats(sequence_result, params, tolerance=0.12)
    symbol_error_rate = 1.0 - sequence_result["symbol_accuracy"] if sequence_result["total_postselected"] else 0.0

    return {
        "parameter": parameter_value,
        "parameter_name": parameter_name,
        "expected_fourfold_rate": expected_stats["expected_fourfold_rate"],
        "observed_fourfold_rate": sequence_result["fourfold_rate"],
        "observed_postselection_rate": sequence_result["postselection_rate"],
        "timing_anomaly_rate": expected_stats["timing_anomaly_rate"],
        "symbol_accuracy": sequence_result["symbol_accuracy"],
        "symbol_error_rate": symbol_error_rate,
        "postselected_count": sequence_result["total_postselected"],
        "fourfold_count": sequence_result["total_fourfold"],
        "timing_anomaly_count": sequence_result["total_timing_anomaly"],
    }


def run_single_sweep(params: dict, parameter_name: str, values: list[float], trials: int, state_label: str = "psi1") -> pd.DataFrame:
    rows = []
    state_sequence = [state_label] * int(trials)

    for value in values:
        sweep_params = make_sweep_base_params(params)
        reset_all_eve(sweep_params)

        if parameter_name == "detector_eta":
            set_all_channel_loss(sweep_params, 0.05)
            sweep_params["beam_splitters"]["bs_left"]["loss"] = 0.02
            sweep_params["beam_splitters"]["bs_right"]["loss"] = 0.02
            set_all_detector_eta(sweep_params, value)

        elif parameter_name == "channel_loss":
            set_all_channel_loss(sweep_params, value)
            set_all_detector_eta(sweep_params, 0.85)
            sweep_params["beam_splitters"]["bs_left"]["loss"] = 0.02
            sweep_params["beam_splitters"]["bs_right"]["loss"] = 0.02

        elif parameter_name == "eve_delay_ns":
            # Ideal detection + one delayed Eve channel: isolates timing effect.
            set_all_channel_loss(sweep_params, 0.0)
            set_all_detector_eta(sweep_params, 1.0)
            sweep_params["beam_splitters"]["bs_left"]["loss"] = 0.0
            sweep_params["beam_splitters"]["bs_right"]["loss"] = 0.0
            sweep_params["channels"]["channel_2"]["eve"] = True
            sweep_params["channels"]["channel_2"]["eve_mode"] = "passive_monitor"
            sweep_params["channels"]["channel_2"]["eve_delay"] = float(value) * 1e-9
            sweep_params["channels"]["channel_2"]["eve_disturbance"] = 0.0
            sweep_params["timing"]["coincidence_window"] = 2e-9
            sweep_params["timing"]["detector_jitter"] = 0.0

        elif parameter_name == "eve_disturbance":
            # No delay; isolate polarization disturbance effect.
            set_all_channel_loss(sweep_params, 0.0)
            set_all_detector_eta(sweep_params, 1.0)
            sweep_params["beam_splitters"]["bs_left"]["loss"] = 0.0
            sweep_params["beam_splitters"]["bs_right"]["loss"] = 0.0
            sweep_params["channels"]["channel_2"]["eve"] = True
            sweep_params["channels"]["channel_2"]["eve_mode"] = "disturbance_only"
            sweep_params["channels"]["channel_2"]["eve_delay"] = 0.0
            sweep_params["channels"]["channel_2"]["eve_disturbance"] = float(value)
            sweep_params["timing"]["detector_jitter"] = 0.0

        else:
            raise ValueError(f"Unknown sweep parameter: {parameter_name}")

        sequence_result = simulate_state_sequence(state_sequence, sweep_params)
        rows.append(summarize_sequence_for_sweep(sequence_result, sweep_params, parameter_name, float(value)))

    return pd.DataFrame(rows)


def run_parameter_sweeps(params: dict, trials: int = 500, state_label: str = "psi1") -> dict:
    eta_values = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 1.00]
    loss_values = [0.00, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
    eve_delay_values_ns = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    eve_disturbance_values = [0.00, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]

    return {
        "trials": trials,
        "state_label": state_label,
        "eta_sweep": run_single_sweep(params, "detector_eta", eta_values, trials, state_label),
        "loss_sweep": run_single_sweep(params, "channel_loss", loss_values, trials, state_label),
        "eve_delay_sweep": run_single_sweep(params, "eve_delay_ns", eve_delay_values_ns, trials, state_label),
        "eve_disturbance_sweep": run_single_sweep(params, "eve_disturbance", eve_disturbance_values, trials, state_label),
    }

# ============================================================
# Display scheme
# ============================================================

with left_col:
    st.subheader("Experimental Scheme")

    base_image = load_scheme_image()
    display_image = draw_highlight_on_scheme(
        base_image,
        st.session_state.selected_element,
        CLICK_ZONES,
    )

    coords = streamlit_image_coordinates(
        display_image,
        key="scheme",
        width=850,
    )

    clicked_zone = detect_clicked_zone(coords, CLICK_ZONES)

    if clicked_zone is not None:
        st.session_state.selected_element = clicked_zone

    selected = st.session_state.selected_element

    st.caption(f"Clicked coordinates: {coords}")
    st.caption(f"Selected element: {selected}")

# ============================================================
# Settings panel
# ============================================================

with right_col:
    st.subheader("Element Settings")

    if selected is None:
        st.info("Click any element on the scheme to configure it.")

    elif selected == "source":
        st.markdown("### Source S")

        # This selector is intentionally OUTSIDE the form.
        # Streamlit forms do not redraw conditional form contents until submit,
        # so mode-dependent settings must be controlled outside the form.
        if "source_mode_ui" not in st.session_state:
            st.session_state.source_mode_ui = params["source"].get("mode", "manual")

        mode = st.radio(
            "Source state mode",
            ["manual", "article_state"],
            index=0 if st.session_state.source_mode_ui == "manual" else 1,
            key="source_mode_ui",
        )

        if mode == "article_state":
            st.info(
                "Article-state mode: manual source polarization angles are hidden. "
                "The source is one of ψ1..ψ4 from the article."
            )
        else:
            st.info(
                "Manual mode: the source is configured by independent polarization angles. "
                "This is mainly a debug mode."
            )

        with st.form("source_form"):
            message = st.text_input(
                "Message Alice sends",
                value=params["source"]["message"],
            )

            num_packets = st.slider(
                "Number of photon packets",
                100,
                20000,
                params["source"]["num_packets"],
                100,
            )

            pair_generation_efficiency = st.slider(
                "Pair generation efficiency",
                0.0,
                1.0,
                params["source"]["pair_generation_efficiency"],
                0.01,
            )

            detection_mode = st.selectbox(
                "Detection mode",
                ["fourfold", "any_click"],
                index=0 if params["simulation"]["detection_mode"] == "fourfold" else 1,
            )

            timing_speed = st.number_input(
                "Propagation speed (m/s)",
                min_value=1e6,
                max_value=3e8,
                value=float(params["timing"]["speed"]),
                step=1e6,
                format="%.3e",
            )

            coincidence_window = st.number_input(
                "Coincidence window (s)",
                min_value=1e-12,
                max_value=1e-6,
                value=float(params["timing"]["coincidence_window"]),
                step=1e-10,
                format="%.3e",
            )

            detector_jitter = st.number_input(
                "Detector jitter (s)",
                min_value=0.0,
                max_value=1e-6,
                value=float(params["timing"]["detector_jitter"]),
                step=1e-10,
                format="%.3e",
            )

            st.caption("Main physics path is fixed: article state → PR rotations → measurement in the standard x/y basis.")

            article_state_label = params["source"]["article_state_label"]
            angle_1 = params["source"]["state_angles"]["channel_1"]
            angle_2 = params["source"]["state_angles"]["channel_2"]
            angle_3 = params["source"]["state_angles"]["channel_3"]
            angle_4 = params["source"]["state_angles"]["channel_4"]

            if mode == "article_state":
                article_state_label = st.selectbox(
                    "Article state",
                    ["psi1", "psi2", "psi3", "psi4"],
                    index=["psi1", "psi2", "psi3", "psi4"].index(params["source"]["article_state_label"]),
                )

                st.markdown("#### Components of this state")
                st.write(ARTICLE_STATES[article_state_label])

            else:
                st.markdown("#### Polarization angles by channel")

                angle_1 = st.slider(
                    "Channel 1 angle",
                    -180.0,
                    180.0,
                    params["source"]["state_angles"]["channel_1"],
                    1.0,
                    key="source_angle_1",
                )

                angle_2 = st.slider(
                    "Channel 2 angle",
                    -180.0,
                    180.0,
                    params["source"]["state_angles"]["channel_2"],
                    1.0,
                    key="source_angle_2",
                )

                angle_3 = st.slider(
                    "Channel 3 angle",
                    -180.0,
                    180.0,
                    params["source"]["state_angles"]["channel_3"],
                    1.0,
                    key="source_angle_3",
                )

                angle_4 = st.slider(
                    "Channel 4 angle",
                    -180.0,
                    180.0,
                    params["source"]["state_angles"]["channel_4"],
                    1.0,
                    key="source_angle_4",
                )

            submitted = st.form_submit_button("Apply source settings")

            if submitted:
                params["source"]["message"] = message
                params["source"]["num_packets"] = num_packets
                params["source"]["pair_generation_efficiency"] = pair_generation_efficiency
                params["source"]["mode"] = mode
                params["source"]["article_state_label"] = article_state_label
                params["simulation"]["detection_mode"] = detection_mode
                params["timing"]["speed"] = float(timing_speed)
                params["timing"]["coincidence_window"] = float(coincidence_window)
                params["timing"]["detector_jitter"] = float(detector_jitter)

                if mode == "article_state":
                    params["source"]["selected_state_label"] = article_state_label
                else:
                    params["source"]["selected_state_label"] = "manual"
                    params["source"]["state_angles"]["channel_1"] = angle_1
                    params["source"]["state_angles"]["channel_2"] = angle_2
                    params["source"]["state_angles"]["channel_3"] = angle_3
                    params["source"]["state_angles"]["channel_4"] = angle_4

                st.success("Source settings applied.")

    elif selected.startswith("channel"):
        st.markdown(f"### {selected}")

        with st.form(f"{selected}_form"):
            eve = st.checkbox(
                "Eve taps this channel",
                value=params["channels"][selected]["eve"],
            )

            eve_mode = st.selectbox(
                "Eve mode",
                ["passive_monitor", "disturbance_only", "intercept_resend"],
                index=["passive_monitor", "disturbance_only", "intercept_resend"].index(
                    params["channels"][selected].get("eve_mode", "disturbance_only")
                ),
            )

            loss = st.slider(
                "Channel loss",
                0.0,
                1.0,
                params["channels"][selected]["loss"],
                0.01,
            )

            eve_disturbance = st.slider(
                "Eve disturbance probability",
                0.0,
                1.0,
                params["channels"][selected]["eve_disturbance"],
                0.01,
            )

            eve_delay_ns = st.number_input(
                "Eve delay (ns)",
                min_value=0.0,
                max_value=1000.0,
                value=float(params["channels"][selected].get("eve_delay", 0.0) * 1e9),
                step=0.1,
            )

            length = st.number_input(
                "Channel length (m)",
                min_value=0.1,
                max_value=100000.0,
                value=float(params["channels"][selected]["length"]),
                step=0.1,
            )

            submitted = st.form_submit_button("Apply channel settings")

            if submitted:
                params["channels"][selected]["eve"] = eve
                params["channels"][selected]["eve_mode"] = eve_mode
                params["channels"][selected]["loss"] = loss
                params["channels"][selected]["eve_disturbance"] = eve_disturbance
                params["channels"][selected]["eve_delay"] = eve_delay_ns * 1e-9
                params["channels"][selected]["length"] = float(length)

    elif selected.startswith("pr"):
        st.markdown(f"### {selected}")

        with st.form(f"{selected}_form"):
            angle = st.slider(
                "Polarization rotation angle",
                -180.0,
                180.0,
                params["pr"][selected]["angle"],
                1.0,
            )

            error = st.slider(
                "Rotation error",
                0.0,
                0.2,
                params["pr"][selected]["error"],
                0.01,
            )

            submitted = st.form_submit_button("Apply PR settings")

            if submitted:
                params["pr"][selected]["angle"] = angle
                params["pr"][selected]["error"] = error

    elif selected.startswith("detector"):
        st.markdown(f"### {selected}")

        with st.form(f"{selected}_form"):
            eta = st.slider(
                "Detector efficiency η",
                0.0,
                1.0,
                params["detectors"][selected]["eta"],
                0.01,
            )

            dark = st.slider(
                "Dark count probability",
                0.0,
                0.2,
                params["detectors"][selected]["dark"],
                0.001,
            )

            submitted = st.form_submit_button("Apply detector settings")

            if submitted:
                params["detectors"][selected]["eta"] = eta
                params["detectors"][selected]["dark"] = dark

    elif selected.startswith("bs"):
        st.markdown(f"### {selected}")

        with st.form(f"{selected}_form"):
            loss = st.slider(
                "Beam splitter loss",
                0.0,
                1.0,
                params["beam_splitters"][selected]["loss"],
                0.01,
            )

            submitted = st.form_submit_button("Apply BS settings")

            if submitted:
                params["beam_splitters"][selected]["loss"] = loss


# ============================================================
# Direct controls: reliable settings without clicking tiny zones
# ============================================================

with st.expander("Direct configuration panels (use this if image clicking is inconvenient)", expanded=True):
    st.caption(
        "These controls duplicate the scheme settings, but do not depend on clicking the image. "
        "Use them for channels 2/3 and for quick test presets."
    )

    preset_tab, source_tab, channels_tab, detectors_tab, pr_tab, bs_tab, timing_tab = st.tabs([
        "Presets",
        "Source",
        "Channels",
        "Detectors",
        "PR",
        "Beam splitters",
        "Timing",
    ])

    with preset_tab:
        st.markdown("### Fast test presets")

        preset_col1, preset_col2 = st.columns(2)

        with preset_col1:
            if st.button("Apply ideal article-state channel", key="preset_ideal_channel"):
                params["source"]["mode"] = "article_state"
                params["source"]["selected_state_label"] = params["source"].get("article_state_label", "psi1")
                params["source"]["pair_generation_efficiency"] = 1.0
                params["simulation"]["detection_mode"] = "fourfold"

                for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
                    params["channels"][channel_name]["loss"] = 0.0
                    params["channels"][channel_name]["eve"] = False
                    params["channels"][channel_name]["eve_mode"] = "disturbance_only"
                    params["channels"][channel_name]["eve_disturbance"] = 0.0
                    params["channels"][channel_name]["eve_delay"] = 0.0
                    params["channels"][channel_name]["length"] = 10.0

                for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
                    params["detectors"][detector_name]["eta"] = 1.0
                    params["detectors"][detector_name]["dark"] = 0.0

                for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
                    params["pr"][pr_name]["angle"] = 0.0
                    params["pr"][pr_name]["error"] = 0.0

                params["beam_splitters"]["bs_left"]["loss"] = 0.0
                params["beam_splitters"]["bs_right"]["loss"] = 0.0

                params["timing"]["speed"] = 2e8
                params["timing"]["coincidence_window"] = 2e-9
                params["timing"]["detector_jitter"] = 0.2e-9

                st.success("Ideal article-state channel preset applied.")

        with preset_col2:
            if st.button("Apply realistic baseline without Eve", key="preset_realistic_no_eve"):
                params["source"]["mode"] = "article_state"
                params["source"]["selected_state_label"] = params["source"].get("article_state_label", "psi1")
                params["source"]["pair_generation_efficiency"] = 0.95
                params["simulation"]["detection_mode"] = "fourfold"

                for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
                    params["channels"][channel_name]["loss"] = 0.05
                    params["channels"][channel_name]["eve"] = False
                    params["channels"][channel_name]["eve_mode"] = "disturbance_only"
                    params["channels"][channel_name]["eve_disturbance"] = 0.15
                    params["channels"][channel_name]["eve_delay"] = 0.0
                    params["channels"][channel_name]["length"] = 10.0

                for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
                    params["detectors"][detector_name]["eta"] = 0.85
                    params["detectors"][detector_name]["dark"] = 0.0

                for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
                    params["pr"][pr_name]["angle"] = 0.0
                    params["pr"][pr_name]["error"] = 0.0

                params["beam_splitters"]["bs_left"]["loss"] = 0.02
                params["beam_splitters"]["bs_right"]["loss"] = 0.02

                params["timing"]["speed"] = 2e8
                params["timing"]["coincidence_window"] = 2e-9
                params["timing"]["detector_jitter"] = 0.2e-9

                st.success("Realistic no-Eve baseline preset applied.")

        st.markdown("### Current quick summary")
        st.write("Source mode:", params["source"].get("mode"))
        st.write("Selected state:", params["source"].get("selected_state_label"))
        st.write("Detection mode:", params["simulation"].get("detection_mode"))

    with source_tab:
        st.markdown("### Source settings without image click")

        source_mode_direct = st.radio(
            "Source mode",
            ["manual", "article_state"],
            index=0 if params["source"].get("mode", "manual") == "manual" else 1,
            key="direct_source_mode",
            horizontal=True,
        )

        with st.form("direct_source_form"):
            source_message_direct = st.text_input(
                "Message Alice sends",
                value=params["source"]["message"],
                key="direct_source_message",
            )

            source_packets_direct = st.number_input(
                "Number of photon packets",
                min_value=1,
                max_value=100000,
                value=int(params["source"]["num_packets"]),
                step=100,
                key="direct_source_packets",
            )

            source_pair_eff_direct = st.number_input(
                "Pair generation efficiency",
                min_value=0.0,
                max_value=1.0,
                value=float(params["source"]["pair_generation_efficiency"]),
                step=0.01,
                key="direct_source_pair_eff",
            )

            detection_mode_direct = st.selectbox(
                "Detection mode",
                ["fourfold", "any_click"],
                index=0 if params["simulation"].get("detection_mode", "fourfold") == "fourfold" else 1,
                key="direct_detection_mode",
            )

            article_state_direct = params["source"].get("article_state_label", "psi1")
            manual_angles_direct = params["source"]["state_angles"].copy()

            if source_mode_direct == "article_state":
                article_state_direct = st.selectbox(
                    "Article state",
                    ["psi1", "psi2", "psi3", "psi4"],
                    index=["psi1", "psi2", "psi3", "psi4"].index(params["source"].get("article_state_label", "psi1")),
                    key="direct_article_state",
                )
                st.write(ARTICLE_STATES[article_state_direct])
            else:
                st.markdown("#### Manual polarization angles")
                angle_cols = st.columns(4)
                for idx, channel_name in enumerate(["channel_1", "channel_2", "channel_3", "channel_4"]):
                    with angle_cols[idx]:
                        manual_angles_direct[channel_name] = st.number_input(
                            f"{channel_name} angle",
                            min_value=-180.0,
                            max_value=180.0,
                            value=float(params["source"]["state_angles"][channel_name]),
                            step=1.0,
                            key=f"direct_{channel_name}_source_angle",
                        )

            source_direct_submitted = st.form_submit_button("Apply direct source settings")

            if source_direct_submitted:
                params["source"]["message"] = source_message_direct
                params["source"]["num_packets"] = int(source_packets_direct)
                params["source"]["pair_generation_efficiency"] = float(source_pair_eff_direct)
                params["source"]["mode"] = source_mode_direct
                params["simulation"]["detection_mode"] = detection_mode_direct

                if source_mode_direct == "article_state":
                    params["source"]["article_state_label"] = article_state_direct
                    params["source"]["selected_state_label"] = article_state_direct
                else:
                    params["source"]["selected_state_label"] = "manual"
                    params["source"]["state_angles"].update(manual_angles_direct)

                st.success("Direct source settings applied.")

    with channels_tab:
        st.markdown("### Channel settings without image click")

        st.markdown("#### Apply same values to all channels")
        with st.form("all_channels_form"):
            all_loss = st.number_input("All channels loss", min_value=0.0, max_value=1.0, value=0.0, step=0.01, key="all_channels_loss")
            all_length = st.number_input("All channels length (m)", min_value=0.1, max_value=100000.0, value=10.0, step=0.1, key="all_channels_length")
            all_eve = st.checkbox("Eve on all channels", value=False, key="all_channels_eve")
            all_eve_mode = st.selectbox("All channels Eve mode", ["passive_monitor", "disturbance_only", "intercept_resend"], index=1, key="all_channels_eve_mode")
            all_eve_disturbance = st.number_input("All channels Eve disturbance", min_value=0.0, max_value=1.0, value=0.0, step=0.01, key="all_channels_eve_disturbance")
            all_eve_delay_ns = st.number_input("All channels Eve delay (ns)", min_value=0.0, max_value=1000.0, value=0.0, step=0.1, key="all_channels_eve_delay")
            apply_all_channels = st.form_submit_button("Apply to all channels")

            if apply_all_channels:
                for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
                    params["channels"][channel_name]["loss"] = float(all_loss)
                    params["channels"][channel_name]["length"] = float(all_length)
                    params["channels"][channel_name]["eve"] = bool(all_eve)
                    params["channels"][channel_name]["eve_mode"] = all_eve_mode
                    params["channels"][channel_name]["eve_disturbance"] = float(all_eve_disturbance)
                    params["channels"][channel_name]["eve_delay"] = float(all_eve_delay_ns) * 1e-9
                st.success("Applied values to all channels.")

        st.markdown("#### Configure one channel")
        direct_channel_name = st.selectbox(
            "Channel",
            ["channel_1", "channel_2", "channel_3", "channel_4"],
            key="direct_channel_select",
        )

        with st.form("direct_single_channel_form"):
            channel_data = params["channels"][direct_channel_name]
            direct_channel_eve = st.checkbox("Eve taps this channel", value=bool(channel_data["eve"]), key="direct_channel_eve")
            direct_channel_eve_mode = st.selectbox(
                "Eve mode",
                ["passive_monitor", "disturbance_only", "intercept_resend"],
                index=["passive_monitor", "disturbance_only", "intercept_resend"].index(channel_data.get("eve_mode", "disturbance_only")),
                key="direct_channel_eve_mode",
            )
            direct_channel_loss = st.number_input("Channel loss", min_value=0.0, max_value=1.0, value=float(channel_data["loss"]), step=0.01, key="direct_channel_loss")
            direct_channel_eve_disturbance = st.number_input("Eve disturbance probability", min_value=0.0, max_value=1.0, value=float(channel_data["eve_disturbance"]), step=0.01, key="direct_channel_eve_disturbance")
            direct_channel_eve_delay_ns = st.number_input("Eve delay (ns)", min_value=0.0, max_value=1000.0, value=float(channel_data.get("eve_delay", 0.0) * 1e9), step=0.1, key="direct_channel_eve_delay")
            direct_channel_length = st.number_input("Channel length (m)", min_value=0.1, max_value=100000.0, value=float(channel_data["length"]), step=0.1, key="direct_channel_length")
            direct_channel_submitted = st.form_submit_button("Apply selected channel settings")

            if direct_channel_submitted:
                params["channels"][direct_channel_name]["eve"] = bool(direct_channel_eve)
                params["channels"][direct_channel_name]["eve_mode"] = direct_channel_eve_mode
                params["channels"][direct_channel_name]["loss"] = float(direct_channel_loss)
                params["channels"][direct_channel_name]["eve_disturbance"] = float(direct_channel_eve_disturbance)
                params["channels"][direct_channel_name]["eve_delay"] = float(direct_channel_eve_delay_ns) * 1e-9
                params["channels"][direct_channel_name]["length"] = float(direct_channel_length)
                st.success(f"{direct_channel_name} settings applied.")

        channel_overview = pd.DataFrame(params["channels"]).T.reset_index().rename(columns={"index": "channel"})
        channel_overview["eve_delay_ns"] = channel_overview["eve_delay"] * 1e9
        st.dataframe(channel_overview[["channel", "loss", "length", "eve", "eve_mode", "eve_disturbance", "eve_delay_ns"]], use_container_width=True)

    with detectors_tab:
        st.markdown("### Detector settings without image click")

        with st.form("all_detectors_form"):
            all_eta = st.number_input("All detectors eta", min_value=0.0, max_value=1.0, value=1.0, step=0.01, key="all_detectors_eta")
            all_dark = st.number_input("All detectors dark count probability", min_value=0.0, max_value=0.2, value=0.0, step=0.001, key="all_detectors_dark")
            apply_all_detectors = st.form_submit_button("Apply to all detectors")

            if apply_all_detectors:
                for detector_name in ["detector_1", "detector_2", "detector_3", "detector_4"]:
                    params["detectors"][detector_name]["eta"] = float(all_eta)
                    params["detectors"][detector_name]["dark"] = float(all_dark)
                st.success("Applied values to all detectors.")

        direct_detector_name = st.selectbox("Detector", ["detector_1", "detector_2", "detector_3", "detector_4"], key="direct_detector_select")
        with st.form("direct_single_detector_form"):
            detector_data = params["detectors"][direct_detector_name]
            direct_eta = st.number_input("Detector efficiency η", min_value=0.0, max_value=1.0, value=float(detector_data["eta"]), step=0.01, key="direct_detector_eta")
            direct_dark = st.number_input("Dark count probability", min_value=0.0, max_value=0.2, value=float(detector_data["dark"]), step=0.001, key="direct_detector_dark")
            direct_detector_submitted = st.form_submit_button("Apply selected detector settings")

            if direct_detector_submitted:
                params["detectors"][direct_detector_name]["eta"] = float(direct_eta)
                params["detectors"][direct_detector_name]["dark"] = float(direct_dark)
                st.success(f"{direct_detector_name} settings applied.")

        st.dataframe(pd.DataFrame(params["detectors"]).T.reset_index().rename(columns={"index": "detector"}), use_container_width=True)

    with pr_tab:
        st.markdown("### PR settings without image click")

        with st.form("all_pr_form"):
            all_pr_angle = st.number_input("All PR angle (deg)", min_value=-180.0, max_value=180.0, value=0.0, step=1.0, key="all_pr_angle")
            all_pr_error = st.number_input("All PR error", min_value=0.0, max_value=0.2, value=0.0, step=0.01, key="all_pr_error")
            apply_all_pr = st.form_submit_button("Apply to all PR elements")

            if apply_all_pr:
                for pr_name in ["pr_1", "pr_2", "pr_3", "pr_4"]:
                    params["pr"][pr_name]["angle"] = float(all_pr_angle)
                    params["pr"][pr_name]["error"] = float(all_pr_error)
                st.success("Applied values to all PR elements.")

        direct_pr_name = st.selectbox("PR element", ["pr_1", "pr_2", "pr_3", "pr_4"], key="direct_pr_select")
        with st.form("direct_single_pr_form"):
            pr_data = params["pr"][direct_pr_name]
            direct_pr_angle = st.number_input("Polarization rotation angle", min_value=-180.0, max_value=180.0, value=float(pr_data["angle"]), step=1.0, key="direct_pr_angle")
            direct_pr_error = st.number_input("Rotation error", min_value=0.0, max_value=0.2, value=float(pr_data["error"]), step=0.01, key="direct_pr_error")
            direct_pr_submitted = st.form_submit_button("Apply selected PR settings")

            if direct_pr_submitted:
                params["pr"][direct_pr_name]["angle"] = float(direct_pr_angle)
                params["pr"][direct_pr_name]["error"] = float(direct_pr_error)
                st.success(f"{direct_pr_name} settings applied.")

        st.dataframe(pd.DataFrame(params["pr"]).T.reset_index().rename(columns={"index": "pr"}), use_container_width=True)

    with bs_tab:
        st.markdown("### Beam splitter settings without image click")

        with st.form("direct_bs_form"):
            bs_left_loss = st.number_input("BS left loss", min_value=0.0, max_value=1.0, value=float(params["beam_splitters"]["bs_left"]["loss"]), step=0.01, key="direct_bs_left_loss")
            bs_right_loss = st.number_input("BS right loss", min_value=0.0, max_value=1.0, value=float(params["beam_splitters"]["bs_right"]["loss"]), step=0.01, key="direct_bs_right_loss")
            bs_submitted = st.form_submit_button("Apply beam splitter settings")

            if bs_submitted:
                params["beam_splitters"]["bs_left"]["loss"] = float(bs_left_loss)
                params["beam_splitters"]["bs_right"]["loss"] = float(bs_right_loss)
                st.success("Beam splitter settings applied.")

        st.dataframe(pd.DataFrame(params["beam_splitters"]).T.reset_index().rename(columns={"index": "beam_splitter"}), use_container_width=True)

    with timing_tab:
        st.markdown("### Timing settings without image click")

        with st.form("direct_timing_form"):
            direct_speed = st.number_input("Propagation speed (m/s)", min_value=1e6, max_value=3e8, value=float(params["timing"]["speed"]), step=1e6, format="%.3e", key="direct_timing_speed")
            direct_window_ns = st.number_input("Coincidence window (ns)", min_value=0.001, max_value=1000.0, value=float(params["timing"]["coincidence_window"] * 1e9), step=0.1, key="direct_timing_window")
            direct_jitter_ns = st.number_input("Detector jitter (ns)", min_value=0.0, max_value=1000.0, value=float(params["timing"]["detector_jitter"] * 1e9), step=0.1, key="direct_timing_jitter")
            timing_submitted = st.form_submit_button("Apply timing settings")

            if timing_submitted:
                params["timing"]["speed"] = float(direct_speed)
                params["timing"]["coincidence_window"] = float(direct_window_ns) * 1e-9
                params["timing"]["detector_jitter"] = float(direct_jitter_ns) * 1e-9
                st.success("Timing settings applied.")

        st.json({
            "speed_m_per_s": params["timing"]["speed"],
            "coincidence_window_ns": params["timing"]["coincidence_window"] * 1e9,
            "detector_jitter_ns": params["timing"]["detector_jitter"] * 1e9,
        })


st.divider()

# ============================================================
# Display current configuration
# ============================================================

with st.expander("Current Scheme Configuration"):
    st.json(params)

with st.expander("Message encoding preview"):
    preview_text = params["source"]["message"]
    encoding_preview = encode_text_to_states(preview_text)

    st.write("Original text:", encoding_preview["text"])
    st.write("Bitstring:", encoding_preview["bitstring"])
    st.write("Bit pairs:", encoding_preview["bit_pairs"])
    st.write("Mapped states:", encoding_preview["states"])

st.divider()

st.subheader("Run heavy calculations only on demand")
st.caption("This part was refactored so Streamlit does not recompute the expensive blocks every time you change one slider.")

control_col1, control_col2, control_col3, control_col4 = st.columns(4)

with control_col1:
    debug_state_label = st.selectbox(
        "State for single-packet debug",
        ["psi1", "psi2", "psi3", "psi4"],
        index=["psi1", "psi2", "psi3", "psi4"].index(params["source"].get("article_state_label", "psi1")),
    )
    if st.button("Run single packet debug"):
        st.session_state.last_debug_result = build_single_packet_debug_report(debug_state_label, params)
        st.session_state.last_debug_state_label = debug_state_label

with control_col2:
    if st.button("Run message transmission"):
        st.session_state.last_message_result = build_message_transmission_summary(params["source"]["message"], params)

with control_col3:
    self_test_trials = st.number_input("Ideal self-test trials per state", min_value=1, max_value=10000, value=100, step=10)
    if st.button("Run ideal self-test"):
        st.session_state.last_self_test_result = run_ideal_self_test(int(self_test_trials), params)

with control_col4:
    if st.button("Run physics model self-check"):
        st.session_state.last_physics_check_result = build_physics_model_check(params)

if st.button("Run full simulation"):
    st.session_state.last_simulation_result = build_simulation_bundle(params)

if st.button("Run validation suite"):
    st.session_state.last_validation_result = run_validation_suite(params)

sweep_col_a, sweep_col_b = st.columns([1, 3])
with sweep_col_a:
    sweep_trials = st.number_input("Sweep trials per point", min_value=50, max_value=5000, value=500, step=50)
with sweep_col_b:
    sweep_state_label = st.selectbox("State for sweeps", ["psi1", "psi2", "psi3", "psi4"], index=0)

if st.button("Run parameter sweeps"):
    st.session_state.last_sweep_result = run_parameter_sweeps(params, int(sweep_trials), sweep_state_label)

with st.expander("Physics model self-check", expanded=False):
    if st.session_state.last_physics_check_result is None:
        st.info("Click 'Run physics model self-check' to verify the main article-state → PR rotation → x/y-basis measurement path.")
    else:
        physics_check = st.session_state.last_physics_check_result

        st.write("Physics model:", physics_check["physics_model"])

        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("State norms OK", "yes" if physics_check["norm_ok"] else "no")
        metric_col2.metric("Probability sums OK", "yes" if physics_check["probability_sum_ok"] else "no")
        metric_col3.metric("Non-negative probabilities", "yes" if physics_check["non_negative_ok"] else "no")

        st.markdown("### Normalization and probability checks")
        st.dataframe(physics_check["normalization_df"], use_container_width=True)

        st.markdown("### Decoder snapshot for the most likely pattern of each state")
        st.dataframe(physics_check["decoder_snapshot_df"], use_container_width=True)


with st.expander("Validation suite", expanded=False):
    if st.session_state.last_validation_result is None:
        st.info("Click 'Run validation suite' to run the built-in regression checks: ideal channel, psi3/0000, realistic baseline, and Eve delay timing rejection.")
    else:
        validation_result = st.session_state.last_validation_result
        st.metric("Overall validation", "PASS" if validation_result["all_passed"] else "FAIL")
        st.dataframe(validation_result["validation_df"], use_container_width=True)

        details = validation_result["details"]

        st.markdown("### Ideal self-test summary")
        st.dataframe(details["ideal_self_test_summary"], use_container_width=True)

        st.markdown("### psi3 / 0000 regression details")
        st.json(details["psi3_0000"])

        st.markdown("### Realistic baseline expected vs observed")
        st.dataframe(details["realistic_expected_vs_observed"], use_container_width=True)

        st.markdown("### Realistic baseline rejection stats")
        st.json(details["realistic_rejection_stats"])

        st.markdown("### Eve delay rejection stats")
        st.json(details["eve_delay_rejection_stats"])


with st.expander("Parameter sweeps", expanded=False):
    if st.session_state.last_sweep_result is None:
        st.info("Click 'Run parameter sweeps' to build plots for detector efficiency, channel loss, Eve delay, and Eve disturbance.")
    else:
        sweep_result = st.session_state.last_sweep_result
        st.write("Trials per point:", sweep_result["trials"])
        st.write("State used:", sweep_result["state_label"])

        tab_eta, tab_loss, tab_delay, tab_disturbance = st.tabs([
            "Detector η",
            "Channel loss",
            "Eve delay",
            "Eve disturbance",
        ])

        with tab_eta:
            df = sweep_result["eta_sweep"]
            st.markdown("### Detector efficiency η → fourfold/postselection rate")
            st.dataframe(df, use_container_width=True)
            st.line_chart(
                df.set_index("parameter")[["expected_fourfold_rate", "observed_fourfold_rate", "observed_postselection_rate"]]
            )

        with tab_loss:
            df = sweep_result["loss_sweep"]
            st.markdown("### Channel loss → fourfold/postselection rate")
            st.dataframe(df, use_container_width=True)
            st.line_chart(
                df.set_index("parameter")[["expected_fourfold_rate", "observed_fourfold_rate", "observed_postselection_rate"]]
            )

        with tab_delay:
            df = sweep_result["eve_delay_sweep"]
            st.markdown("### Eve delay → timing anomaly / postselection")
            st.dataframe(df, use_container_width=True)
            st.line_chart(
                df.set_index("parameter")[["timing_anomaly_rate", "observed_postselection_rate"]]
            )

        with tab_disturbance:
            df = sweep_result["eve_disturbance_sweep"]
            st.markdown("### Eve disturbance → symbol error rate")
            st.dataframe(df, use_container_width=True)
            st.line_chart(
                df.set_index("parameter")[["symbol_error_rate", "symbol_accuracy", "observed_postselection_rate"]]
            )

with st.expander("Single packet debug view", expanded=False):
    if st.session_state.last_debug_result is None:
        st.info("Click 'Run single packet debug' to calculate one packet and freeze its report in session state.")
    else:
        debug_report = st.session_state.last_debug_result

        st.markdown(f"### Debugging one packet for **{debug_report['sent_state']}** ({debug_report['sent_bits']})")

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("Ideal sampled pattern", format_pattern_tuple(debug_report["ideal_pattern"]))
        metric_col2.metric("Observed pattern", format_pattern_tuple(debug_report["observed_pattern"]))
        metric_col3.metric("Detected channels", format_bool_tuple(debug_report["detected_channels"]))
        metric_col4.metric("Decoded state", debug_report["decoded_state"] or "—")

        metric_col5, metric_col6, metric_col7, metric_col8 = st.columns(4)
        metric_col5.metric("Fourfold", "yes" if debug_report["fourfold_detected"] else "no")
        metric_col6.metric("Coincidence", "yes" if debug_report["coincidence_passed"] else "no")
        metric_col7.metric("Postselection", "yes" if debug_report["postselection_passed"] else "no")
        metric_col8.metric("Packet status", debug_report["packet_status_label"])

        st.markdown("#### Step 1. Effective PR angles used in this packet")
        st.json(debug_report["effective_pr_angles"])

        st.markdown("#### Step 2. Non-zero amplitudes of the original state")
        st.dataframe(debug_report["initial_state_amplitudes"], use_container_width=True)

        st.markdown("#### Step 3. Non-zero amplitudes after PR rotations")
        st.dataframe(debug_report["rotated_state_amplitudes"], use_container_width=True)

        st.markdown("#### Step 4. Probabilities of all 16 detector patterns")
        st.dataframe(debug_report["ideal_probability_table"], use_container_width=True)

        st.markdown("#### Step 5. Timing diagnostics")
        st.write("Arrival times (s):", format_arrival_times(debug_report["arrival_times"]))

        st.markdown("#### Step 6. Channel-by-channel diagnostics")
        channel_df = pd.DataFrame(debug_report["channel_report"]).copy()
        if not channel_df.empty:
            for col in ["lost_in_channel", "detected", "detector_miss", "dark_count_used", "eve_disturbed"]:
                channel_df[col] = channel_df[col].map({True: "yes", False: "no"})
        st.dataframe(channel_df, use_container_width=True)

        st.markdown("#### Step 7. Packet interpretation")
        st.write("Probability of sampled ideal pattern:", f"{debug_report['ideal_probability_of_sampled_pattern']:.6f}")
        st.write("Observed pattern stayed equal to ideal pattern:", debug_report["observed_pattern_same_as_ideal"])
        st.write("Packet status:", debug_report["packet_status_label"])
        st.write("Rejection reason:", debug_report["rejection_reason"] or "—")
        st.write("Physically lost:", debug_report["is_physically_lost"])
        st.write("Rejected by postselection:", debug_report["is_rejected_by_postselection"])
        st.write("Decoded bits:", debug_report["decoded_bits"] if debug_report["decoded_bits"] is not None else "—")
        st.write("Decoding confidence:", f"{debug_report['decoding_confidence']:.6f}")
        st.write("Decoded correctly:", debug_report["is_correct"])

with st.expander("Message transmission test", expanded=False):
    if st.session_state.last_message_result is None:
        st.info("Click 'Run message transmission' to calculate this block once.")
    else:
        message_result = st.session_state.last_message_result

        st.write("Original text:", message_result["original_text"])
        st.write("Bitstring:", message_result["original_bitstring"])
        st.write("Bit pairs:", message_result["bit_pairs"])
        st.write("Sent states:", message_result["sent_states"])

        seq = message_result["sequence_result"]
        st.write("Detection mode:", seq["detection_mode"])
        st.write("Total sent:", seq["total_sent"])
        st.write("Total detected:", seq["total_detected"])
        st.write("Total fourfold:", seq["total_fourfold"])
        st.write("Total coincidence passed:", seq["total_coincidence_passed"])
        st.write("Total postselected:", seq["total_postselected"])
        st.write("Total lost:", seq["total_lost"])
        st.write("Detection rate:", f"{seq['detection_rate']:.3f}")
        st.write("Fourfold rate:", f"{seq['fourfold_rate']:.3f}")
        st.write("Coincidence rate:", f"{seq['coincidence_rate']:.3f}")
        st.write("Postselection rate:", f"{seq['postselection_rate']:.3f}")
        st.write("Symbol accuracy:", f"{seq['symbol_accuracy']:.3f}")
        st.write("Loss rate:", f"{seq['loss_rate']:.3f}")
        st.write("BER:", f"{message_result['ber_stats']['ber']:.3f}")
        st.write("SER:", f"{message_result['ser_stats']['ser']:.3f}")
        st.write("Rejection stats:", seq["rejection_stats"])

        st.markdown("### Expected vs observed statistics")
        expected_stats = message_result["expected_observed_stats"]
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        stat_col1.metric("Expected fourfold rate", f"{expected_stats['expected_fourfold_rate']:.3f}")
        stat_col2.metric("Observed fourfold rate", f"{expected_stats['observed_fourfold_rate']:.3f}")
        stat_col3.metric("Possible anomaly", "yes" if expected_stats["possible_anomaly"] else "no")
        st.dataframe(expected_stats["summary_df"], use_container_width=True)
        st.write("Expected arrival times (s):", format_arrival_times(expected_stats["expected_arrival_times"]))
        st.write("Expected timing spread (s):", f"{expected_stats['expected_timing_spread']:.3e}")

        st.write("Recovered bits raw:", message_result["recovered_bits_raw"])
        st.write("Recovered bits clean:", message_result["recovered_bits_clean"])
        st.write("Recovered text:", message_result["recovered_text"])

        transmission_df = pd.DataFrame(seq["results"])
        st.dataframe(transmission_df, use_container_width=True)
        st.dataframe(message_result["bit_comparison_df"], use_container_width=True)

with st.expander("Ideal self-test for ψ1..ψ4", expanded=False):
    if st.session_state.last_self_test_result is None:
        st.info("Click 'Run ideal self-test' to compute the confusion matrix in the ideal channel.")
    else:
        self_test_result = st.session_state.last_self_test_result
        st.markdown("### Accuracy by state")
        st.dataframe(self_test_result["summary_df"], use_container_width=True)

        st.markdown("### Confusion matrix")
        st.dataframe(self_test_result["confusion_df"], use_container_width=True)

        st.markdown("### Confusion matrix (%)")
        st.dataframe(self_test_result["confusion_percent_df"], use_container_width=True)

        fig_self_test = plot_confusion_heatmap(self_test_result["confusion_percent_df"])
        st.pyplot(fig_self_test)

st.divider()

st.subheader("Simulation")

if st.session_state.last_simulation_result is None:
    st.info("Click 'Run full simulation' to compare with Eve and without Eve.")
else:
    bundle = st.session_state.last_simulation_result
    result_attack = bundle["result_attack"]
    result_no_eve = bundle["result_no_eve"]
    message_attack = bundle["message_attack"]
    message_no_eve = bundle["message_no_eve"]

    st.success("Showing the latest saved full simulation result")

    st.subheader("Packet-level comparison: without Eve vs with Eve")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Without Eve")
        st.metric("Packets detected", result_no_eve["detected"])
        st.metric("Packets postselected", result_no_eve["postselected"])
        st.metric("Errors", result_no_eve["errors"])
        st.metric("Success rate", f"{result_no_eve['success_rate']:.3f}")
        st.metric("QBER", f"{result_no_eve['qber']:.3f}")

    with col2:
        st.markdown("### With Eve")
        st.metric("Packets detected", result_attack["detected"])
        st.metric("Packets postselected", result_attack["postselected"])
        st.metric("Errors", result_attack["errors"])
        st.metric("Success rate", f"{result_attack['success_rate']:.3f}")
        st.metric("QBER", f"{result_attack['qber']:.3f}")

    st.write("Message:", result_attack["message"])
    st.write("Source mode:", result_attack["source_mode"])
    st.write("Selected source state:", result_attack["selected_state_label"])
    st.write("Active Eve channels:", result_attack["eve_channels"])
    st.write("Detection mode:", params["simulation"]["detection_mode"])

    if result_attack["source_mode"] == "article_state":
        st.subheader("Packet-level confusion matrix comparison")

        confusion_no_eve_df = pd.DataFrame(result_no_eve["confusion_matrix"]).T
        confusion_no_eve_df.index.name = "Sent state"
        confusion_no_eve_df.columns.name = "Decoded state"

        confusion_attack_df = pd.DataFrame(result_attack["confusion_matrix"]).T
        confusion_attack_df.index.name = "Sent state"
        confusion_attack_df.columns.name = "Decoded state"

        row_sums_no_eve = confusion_no_eve_df.sum(axis=1).replace(0, 1)
        confusion_no_eve_percent_df = (confusion_no_eve_df.div(row_sums_no_eve, axis=0) * 100).round(2)

        row_sums_attack = confusion_attack_df.sum(axis=1).replace(0, 1)
        confusion_attack_percent_df = (confusion_attack_df.div(row_sums_attack, axis=0) * 100).round(2)

        difference_df = (confusion_attack_percent_df - confusion_no_eve_percent_df).round(2)

        tab1, tab2, tab3, tab4 = st.tabs(["Raw counts", "Percent tables", "Heatmaps", "Difference"])

        with tab1:
            left_raw, right_raw = st.columns(2)
            with left_raw:
                st.markdown("#### Without Eve")
                st.dataframe(confusion_no_eve_df, use_container_width=True)
            with right_raw:
                st.markdown("#### With Eve")
                st.dataframe(confusion_attack_df, use_container_width=True)

        with tab2:
            left_pct, right_pct = st.columns(2)
            with left_pct:
                st.markdown("#### Without Eve (%)")
                st.dataframe(confusion_no_eve_percent_df, use_container_width=True)
            with right_pct:
                st.markdown("#### With Eve (%)")
                st.dataframe(confusion_attack_percent_df, use_container_width=True)

        with tab3:
            left_heat, right_heat = st.columns(2)
            with left_heat:
                st.markdown("#### Without Eve")
                fig1 = plot_confusion_heatmap(confusion_no_eve_percent_df)
                st.pyplot(fig1)
            with right_heat:
                st.markdown("#### With Eve")
                fig2 = plot_confusion_heatmap(confusion_attack_percent_df)
                st.pyplot(fig2)

        with tab4:
            st.markdown("#### Difference: With Eve - Without Eve (%)")
            st.dataframe(difference_df, use_container_width=True)
            fig_diff = plot_difference_heatmap(difference_df)
            st.pyplot(fig_diff)

    analysis_text = generate_text_analysis(result_no_eve, result_attack)
    st.markdown(analysis_text)

    st.subheader("Message-level comparison: without Eve vs with Eve")

    msg_col1, msg_col2 = st.columns(2)

    seq_no_eve = message_no_eve["sequence_result"]
    seq_attack = message_attack["sequence_result"]

    with msg_col1:
        st.markdown("### Without Eve")
        st.metric("Postselected 2-bit blocks", seq_no_eve["total_postselected"])
        st.metric("Lost 2-bit blocks", seq_no_eve["total_lost"])
        st.metric("Postselection rate", f"{seq_no_eve['postselection_rate']:.3f}")
        st.metric("Symbol accuracy", f"{seq_no_eve['symbol_accuracy']:.3f}")
        st.metric("BER", f"{message_no_eve['ber_stats']['ber']:.3f}")
        st.metric("SER", f"{message_no_eve['ser_stats']['ser']:.3f}")

    with msg_col2:
        st.markdown("### With Eve")
        st.metric("Postselected 2-bit blocks", seq_attack["total_postselected"])
        st.metric("Lost 2-bit blocks", seq_attack["total_lost"])
        st.metric("Postselection rate", f"{seq_attack['postselection_rate']:.3f}")
        st.metric("Symbol accuracy", f"{seq_attack['symbol_accuracy']:.3f}")
        st.metric("BER", f"{message_attack['ber_stats']['ber']:.3f}")
        st.metric("SER", f"{message_attack['ser_stats']['ser']:.3f}")

    st.markdown("### Recovered text")
    st.write("Original text:", message_attack["original_text"])
    st.write("Recovered without Eve:", message_no_eve["recovered_text"])
    st.write("Recovered with Eve:", message_attack["recovered_text"])

    st.markdown("### Recovered bits")
    st.write("Without Eve (raw):", message_no_eve["recovered_bits_raw"])
    st.write("With Eve (raw):", message_attack["recovered_bits_raw"])

    msg_tab1, msg_tab2, msg_tab3, msg_tab4 = st.tabs([
        "Transmission table: without Eve",
        "Transmission table: with Eve",
        "Bit comparison",
        "Message analysis",
    ])

    with msg_tab1:
        transmission_df_no_eve = pd.DataFrame(message_no_eve["sequence_result"]["results"])
        st.dataframe(transmission_df_no_eve, use_container_width=True)

    with msg_tab2:
        transmission_df_attack = pd.DataFrame(message_attack["sequence_result"]["results"])
        st.dataframe(transmission_df_attack, use_container_width=True)

    with msg_tab3:
        st.markdown("#### Without Eve")
        st.dataframe(message_no_eve["bit_comparison_df"], use_container_width=True)

        st.markdown("#### With Eve")
        st.dataframe(message_attack["bit_comparison_df"], use_container_width=True)

    with msg_tab4:
        message_analysis = generate_message_level_analysis(message_no_eve, message_attack)
        st.markdown(message_analysis)
