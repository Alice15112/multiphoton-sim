import math
import random

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Multiphoton Quantum Simulator", layout="wide")

st.title("Multiphoton Quantum Communication Simulator")

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
            "channel_1": {"loss": 0.05, "eve": False, "eve_disturbance": 0.15},
            "channel_2": {"loss": 0.05, "eve": False, "eve_disturbance": 0.15},
            "channel_3": {"loss": 0.05, "eve": False, "eve_disturbance": 0.15},
            "channel_4": {"loss": 0.05, "eve": False, "eve_disturbance": 0.15},
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
            "detection_mode": "any_click",
            "physics_model": "article_pr_standard_basis",
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
    params["simulation"] = {"detection_mode": "any_click", "physics_model": "article_pr_standard_basis"}

if "physics_model" not in params["simulation"]:
    params["simulation"]["physics_model"] = "article_pr_standard_basis"

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
    detected_results = [r for r in results if r["packet_detected"]]

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
            "decoded_state": result["decoded_state"],
            "recovered_bits": recovered_bits,
            "bit_errors_in_symbol": bit_errors,
            "symbol_correct": result["is_correct"],
            "detected": result["packet_detected"],
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
# New PR-as-state-rotation path
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
    params: dict
) -> tuple[tuple, tuple]:
    """
    IMPORTANT:
    ideal_pattern stores polarization outcomes in the measurement basis:
        0 -> x polarization
        1 -> y polarization

    It does NOT mean "no click / click".

    Therefore we keep two separate objects:
    - observed_polarization_pattern: tuple[int | None, ...]
      * 0 / 1 if a polarization outcome was observed
      * None if that channel was not detected at all
    - detected_channels: tuple[bool, ...]
      * True if the channel produced a detector event
      * False if the channel was lost / missed without a dark count
    """
    channel_names = ["channel_1", "channel_2", "channel_3", "channel_4"]
    detector_names = ["detector_1", "detector_2", "detector_3", "detector_4"]

    observed_polarization_pattern = []
    detected_channels = []

    for idx, (channel_name, detector_name) in enumerate(zip(channel_names, detector_names)):
        channel = params["channels"][channel_name]
        detector = params["detectors"][detector_name]

        ideal_polarization = ideal_pattern[idx]

        total_loss = channel["loss"]

        if channel_name in ["channel_2", "channel_3"]:
            total_loss = min(1.0, total_loss + params["beam_splitters"]["bs_right"]["loss"])
        else:
            total_loss = min(1.0, total_loss + params["beam_splitters"]["bs_left"]["loss"])

        photon_lost = random.random() < total_loss

        detected = False
        observed_polarization = None

        if photon_lost:
            # No photon arrived. A dark count may still happen, but then the
            # registered polarization outcome is effectively random.
            if random.random() < detector["dark"]:
                detected = True
                observed_polarization = random.randint(0, 1)
        else:
            # Photon arrived. Detector may register it with efficiency eta.
            if random.random() < detector["eta"]:
                detected = True
                observed_polarization = ideal_polarization
            else:
                # Missed photon; a dark count can still create a fake click.
                if random.random() < detector["dark"]:
                    detected = True
                    observed_polarization = random.randint(0, 1)

        # Eve disturbance acts on the observed polarization value, not on the
        # fact of "whether the bit is 0 or 1".
        if detected and channel["eve"]:
            if random.random() < channel.get("eve_disturbance", 0.0):
                observed_polarization = 1 - observed_polarization

        observed_polarization_pattern.append(observed_polarization)
        detected_channels.append(detected)

    return tuple(observed_polarization_pattern), tuple(detected_channels)



def is_informative_detection(detected_channels: tuple, mode: str = "any_click") -> bool:
    if mode == "any_click":
        return any(detected_channels)

    if mode == "fourfold":
        return all(detected_channels)

    raise ValueError(f"Unknown detection mode: {mode}")



def simulate_single_state_transmission(state_label: str, params: dict) -> dict:
    if state_label not in ARTICLE_STATE_VECTORS:
        raise ValueError(f"Unknown article state: {state_label}")

    detection_mode = params.get("simulation", {}).get("detection_mode", "any_click")

    state_vector = ARTICLE_STATE_VECTORS[state_label]
    sent_bits = STATE_TO_BITS[state_label]

    effective_pr_angles = sample_effective_pr_angles(params)

    rotated_state = apply_pr_rotations_to_state(state_vector, effective_pr_angles)
    joint_probs = joint_pattern_probabilities_in_standard_basis(rotated_state)
    ideal_pattern = sample_joint_pattern(joint_probs)

    observed_pattern, detected_channels = apply_channel_and_detector_effects(ideal_pattern, params)

    coincidence_detected = is_informative_detection(detected_channels, detection_mode)
    full_pattern_available = all(detected_channels)

    # For article-state decoding we need a complete 4-channel polarization pattern.
    # This also fixes the previous bug where 0000 was wrongly treated as "no clicks".
    packet_detected = full_pattern_available
    was_lost = not packet_detected

    decoded_state = None
    decoded_bits = None
    decoding_confidence = 0.0
    is_correct = False

    if packet_detected:
        decoded_state, decoding_confidence = decode_state_from_pattern_with_pr(
            observed_pattern,
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
        "coincidence_detected": coincidence_detected,
        "full_pattern_available": full_pattern_available,
        "packet_detected": packet_detected,
        "was_lost": was_lost,
        "decoded_state": decoded_state,
        "decoded_bits": decoded_bits,
        "decoding_confidence": decoding_confidence,
        "is_correct": is_correct,
    }



def format_pattern_tuple(pattern: tuple | None) -> str:
    if pattern is None:
        return "—"

    rendered = []
    for bit in pattern:
        if bit is None:
            rendered.append("·")
        else:
            rendered.append(str(bit))
    return "".join(rendered)


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
    detection_mode = params.get("simulation", {}).get("detection_mode", "any_click")

    effective_pr_angles = sample_effective_pr_angles(params)
    rotated_state = apply_pr_rotations_to_state(state_vector, effective_pr_angles)

    ideal_probabilities = joint_pattern_probabilities_in_standard_basis(rotated_state)
    ideal_pattern = sample_joint_pattern(ideal_probabilities)
    observed_pattern, detected_channels = apply_channel_and_detector_effects(ideal_pattern, params)

    coincidence_detected = is_informative_detection(detected_channels, detection_mode)
    full_pattern_available = all(detected_channels)
    packet_detected = full_pattern_available

    decoded_state = None
    decoded_bits = None
    decoding_confidence = 0.0

    if packet_detected:
        decoded_state, decoding_confidence = decode_state_from_pattern_with_pr(
            observed_pattern,
            effective_pr_angles,
        )
        decoded_bits = STATE_TO_BITS[decoded_state]

    return {
        "sent_state": state_label,
        "sent_bits": STATE_TO_BITS[state_label],
        "detection_mode": detection_mode,
        "effective_pr_angles": effective_pr_angles,
        "initial_state_amplitudes": state_vector_to_amplitude_table(state_vector),
        "rotated_state_amplitudes": state_vector_to_amplitude_table(rotated_state),
        "ideal_probability_table": probability_dict_to_dataframe(ideal_probabilities),
        "ideal_pattern": ideal_pattern,
        "observed_pattern": observed_pattern,
        "detected_channels": detected_channels,
        "coincidence_detected": coincidence_detected,
        "full_pattern_available": full_pattern_available,
        "packet_detected": packet_detected,
        "decoded_state": decoded_state,
        "decoded_bits": decoded_bits,
        "decoding_confidence": decoding_confidence,
        "is_correct": decoded_state == state_label if decoded_state is not None else False,
        "ideal_probability_of_sampled_pattern": float(ideal_probabilities.get(ideal_pattern, 0.0)),
        "observed_pattern_same_as_ideal": observed_pattern == ideal_pattern,
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

    for state_label in state_sequence:
        result = simulate_single_state_transmission(state_label, params)
        results.append(result)

        if result["packet_detected"]:
            total_detected += 1
            decoded_state = result["decoded_state"]
            confusion_matrix[state_label][decoded_state] += 1

            if result["is_correct"]:
                total_correct += 1
        else:
            total_lost += 1

    detection_rate = total_detected / total_sent if total_sent else 0.0
    symbol_accuracy = total_correct / total_detected if total_detected else 0.0
    loss_rate = total_lost / total_sent if total_sent else 0.0

    return {
        "results": results,
        "confusion_matrix": confusion_matrix,
        "total_sent": total_sent,
        "total_detected": total_detected,
        "total_lost": total_lost,
        "total_correct": total_correct,
        "detection_rate": detection_rate,
        "symbol_accuracy": symbol_accuracy,
        "loss_rate": loss_rate,
        "detection_mode": params.get("simulation", {}).get("detection_mode", "any_click"),
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
    }

    for ch_name, ch_data in params["channels"].items():
        cloned["channels"][ch_name] = {
            "loss": ch_data["loss"],
            "eve": False,
            "eve_disturbance": ch_data["eve_disturbance"],
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
    }

    for channel_name in ["channel_1", "channel_2", "channel_3", "channel_4"]:
        cloned["channels"][channel_name] = {
            "loss": 0.0,
            "eve": False,
            "eve_disturbance": 0.0,
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

        for _ in range(trials_per_state):
            result = simulate_single_state_transmission(state_label, ideal_params)

            if result["packet_detected"]:
                detected_count += 1
                decoded_state = result["decoded_state"]
                confusion_matrix[state_label][decoded_state] += 1

                if decoded_state == state_label:
                    correct_count += 1

        accuracy = correct_count / detected_count if detected_count else 0.0

        rows.append({
            "state": state_label,
            "trials": trials_per_state,
            "detected": detected_count,
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
            f"(change: **{delta_detected:+d}**). "
            "This may happen in the current simplified model because Eve-induced disturbance and detector dark counts "
            "can create additional clicks."
        )
    elif detected_attack < detected_no_eve:
        lines.append(
            f"With Eve, the number of detected packets decreased from **{detected_no_eve}** to **{detected_attack}** "
            f"(change: **{delta_detected:+d}**). "
            "This indicates that the attack reduces the probability of preserving the expected multi-photon detection pattern."
        )
    else:
        lines.append(f"The number of detected packets stayed the same: **{detected_no_eve}**.")

    lines.append("")
    lines.append("**2. Error behaviour / QBER**")
    if qber_attack > qber_no_eve:
        lines.append(
            f"The QBER increased from **{qber_no_eve:.3f}** to **{qber_attack:.3f}** "
            f"(change: **{delta_qber:+.3f}**), and the number of errors changed from "
            f"**{errors_no_eve}** to **{errors_attack}** (**{delta_errors:+d}**). "
            "This means that Eve makes the decoded result less consistent with the sent state."
        )
    elif qber_attack < qber_no_eve:
        lines.append(
            f"The QBER decreased from **{qber_no_eve:.3f}** to **{qber_attack:.3f}** "
            f"(change: **{delta_qber:+.3f}**). "
            "For a realistic attack this is unusual, so this would most likely indicate that the current simplified stochastic model "
            "and finite sampling fluctuations dominate the result."
        )
    else:
        lines.append(f"The QBER remained unchanged at **{qber_attack:.3f}**.")

    lines.append("")
    lines.append("**3. Success rate**")
    if success_attack > success_no_eve:
        lines.append(
            f"The success rate increased from **{success_no_eve:.3f}** to **{success_attack:.3f}** "
            f"(change: **{delta_success:+.3f}**). "
            "In the present model this can occur because 'success' is defined through detection events, "
            "not yet through the full protocol logic from the article."
        )
    elif success_attack < success_no_eve:
        lines.append(
            f"The success rate decreased from **{success_no_eve:.3f}** to **{success_attack:.3f}** "
            f"(change: **{delta_success:+.3f}**). "
            "This is consistent with the idea that disturbance in the channel worsens transmission quality."
        )
    else:
        lines.append(f"The success rate remained the same at **{success_attack:.3f}**.")

    lines.append("")
    if source_mode == "article_state":
        lines.append("**4. State decoding interpretation**")
        lines.append(
            "In article-state mode, the main physically meaningful result is not only the total number of clicks, "
            "but also how often the received multi-detector click pattern is decoded back into the original sent state."
        )

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

            if best_decoded == selected_state:
                lines.append("So the dominant decoding channel is still correct.")
            else:
                lines.append(
                    "So the dominant decoding channel is already shifted to another state, "
                    "which is a strong sign of disturbance."
                )

    lines.append("")
    lines.append("**5. Relation to the article**")
    lines.append(
        "At this stage, the application is functioning as a simplified transmission model based on the article’s 4-photon state structure, "
        "4 channels, polarization rotations, detector efficiencies, and channel disturbance. "
        "It is not yet implementing the full communication protocol with time-of-arrival control and channel-order key logic."
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
        f"Without Eve, **{seq_no_eve['total_detected']}** out of **{seq_no_eve['total_sent']}** "
        f"2-bit blocks were detected (**{seq_no_eve['detection_rate']:.3f}**)."
    )
    lines.append(
        f"With Eve, **{seq_attack['total_detected']}** out of **{seq_attack['total_sent']}** "
        f"2-bit blocks were detected (**{seq_attack['detection_rate']:.3f}**)."
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

    lines.append("**4. Losses**")
    lines.append(
        f"Without Eve, **{seq_no_eve['total_lost']}** blocks were lost "
        f"(**{seq_no_eve['loss_rate']:.3f}**)."
    )
    lines.append(
        f"With Eve, **{seq_attack['total_lost']}** blocks were lost "
        f"(**{seq_attack['loss_rate']:.3f}**)."
    )
    lines.append("")

    lines.append("**5. Recovered text**")
    lines.append(f"Without Eve: `{summary_no_eve['recovered_text']}`")
    lines.append(f"With Eve: `{summary_attack['recovered_text']}`")
    lines.append("")

    if ber_attack > ber_no_eve:
        lines.append("Eve increases the bit-level distortion of the transmitted message.")
    elif ber_attack < ber_no_eve:
        lines.append(
            "In this run the attack appears to improve bit-level recovery, which is usually a sign that the simplified "
            "stochastic model or finite sampling still dominates the result."
        )
    else:
        lines.append("The bit-level error rate stayed unchanged in this run.")

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

    for _ in range(num_packets):
        if random.random() > pair_eff:
            continue

        transmitted += 1
        packet_detected = False
        packet_error = False

        if source_mode == "article_state" and selected_state_label in ARTICLE_STATE_VECTORS:
            single_result = simulate_single_state_transmission(selected_state_label, params)
            packet_detected = single_result["packet_detected"]

            if packet_detected:
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

                if random.random() < channel["loss"]:
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
    qber = errors / detected if detected else 0.0

    return {
        "message": message,
        "num_packets": num_packets,
        "transmitted": transmitted,
        "detected": detected,
        "errors": errors,
        "success_rate": success_rate,
        "qber": qber,
        "eve_channels": active_eve_channels,
        "selected_state_label": selected_state_label,
        "source_mode": source_mode,
        "decoded_state_counts": decoded_state_counts,
        "confusion_matrix": confusion_matrix,
        "detection_mode": params.get("simulation", {}).get("detection_mode", "any_click"),
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

            mode = st.radio(
                "Source state mode",
                ["manual", "article_state"],
                index=0 if params["source"]["mode"] == "manual" else 1,
            )

            detection_mode = st.selectbox(
                "Detection mode",
                ["any_click", "fourfold"],
                index=0 if params["simulation"]["detection_mode"] == "any_click" else 1,
            )

            st.caption("Main physics path is fixed: article state → PR rotations → measurement in the standard x/y basis.")

            article_state_label = params["source"]["article_state_label"]

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

                if mode == "article_state":
                    params["source"]["selected_state_label"] = article_state_label
                else:
                    params["source"]["selected_state_label"] = "manual"
                    params["source"]["state_angles"]["channel_1"] = angle_1
                    params["source"]["state_angles"]["channel_2"] = angle_2
                    params["source"]["state_angles"]["channel_3"] = angle_3
                    params["source"]["state_angles"]["channel_4"] = angle_4

    elif selected.startswith("channel"):
        st.markdown(f"### {selected}")

        with st.form(f"{selected}_form"):
            eve = st.checkbox(
                "Eve taps this channel",
                value=params["channels"][selected]["eve"],
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

            submitted = st.form_submit_button("Apply channel settings")

            if submitted:
                params["channels"][selected]["eve"] = eve
                params["channels"][selected]["loss"] = loss
                params["channels"][selected]["eve_disturbance"] = eve_disturbance

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

with st.expander("Single packet debug view", expanded=False):
    if st.session_state.last_debug_result is None:
        st.info("Click 'Run single packet debug' to calculate one packet and freeze its report in session state.")
    else:
        debug_report = st.session_state.last_debug_result

        st.markdown(f"### Debugging one packet for **{debug_report['sent_state']}** ({debug_report['sent_bits']})")

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("Ideal sampled pattern", format_pattern_tuple(debug_report["ideal_pattern"]))
        metric_col2.metric("Observed pattern", format_pattern_tuple(debug_report["observed_pattern"]))
        metric_col3.metric("Coincidence detected", "yes" if debug_report["coincidence_detected"] else "no")
        metric_col4.metric("Decoded state", debug_report["decoded_state"] or "lost")

        st.markdown("#### Step 1. Effective PR angles used in this packet")
        st.json(debug_report["effective_pr_angles"])

        st.markdown("#### Step 2. Non-zero amplitudes of the original state")
        st.dataframe(debug_report["initial_state_amplitudes"], use_container_width=True)

        st.markdown("#### Step 3. Non-zero amplitudes after PR rotations")
        st.dataframe(debug_report["rotated_state_amplitudes"], use_container_width=True)

        st.markdown("#### Step 4. Probabilities of all 16 detector patterns")
        st.dataframe(debug_report["ideal_probability_table"], use_container_width=True)

        st.markdown("#### Step 5. Packet interpretation")
        st.write("Probability of sampled ideal pattern:", f"{debug_report['ideal_probability_of_sampled_pattern']:.6f}")
        st.write("Detected channels:", debug_report["detected_channels"])
        st.write("Observed pattern stayed equal to ideal pattern:", debug_report["observed_pattern_same_as_ideal"])
        st.write("Full 4-channel pattern available:", debug_report["full_pattern_available"])
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
        st.write("Total lost:", seq["total_lost"])
        st.write("Detection rate:", f"{seq['detection_rate']:.3f}")
        st.write("Symbol accuracy:", f"{seq['symbol_accuracy']:.3f}")
        st.write("Loss rate:", f"{seq['loss_rate']:.3f}")
        st.write("BER:", f"{message_result['ber_stats']['ber']:.3f}")
        st.write("SER:", f"{message_result['ser_stats']['ser']:.3f}")

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
        st.metric("Errors", result_no_eve["errors"])
        st.metric("Success rate", f"{result_no_eve['success_rate']:.3f}")
        st.metric("QBER", f"{result_no_eve['qber']:.3f}")

    with col2:
        st.markdown("### With Eve")
        st.metric("Packets detected", result_attack["detected"])
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
        st.metric("Detected 2-bit blocks", seq_no_eve["total_detected"])
        st.metric("Lost 2-bit blocks", seq_no_eve["total_lost"])
        st.metric("Detection rate", f"{seq_no_eve['detection_rate']:.3f}")
        st.metric("Symbol accuracy", f"{seq_no_eve['symbol_accuracy']:.3f}")
        st.metric("BER", f"{message_no_eve['ber_stats']['ber']:.3f}")
        st.metric("SER", f"{message_no_eve['ser_stats']['ser']:.3f}")

    with msg_col2:
        st.markdown("### With Eve")
        st.metric("Detected 2-bit blocks", seq_attack["total_detected"])
        st.metric("Lost 2-bit blocks", seq_attack["total_lost"])
        st.metric("Detection rate", f"{seq_attack['detection_rate']:.3f}")
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
