
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
    }

params = st.session_state.scheme_params

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


def projector_for_angle(angle_deg, pr_error):
    effective_angle = angle_deg + random.uniform(-pr_error * 180.0, pr_error * 180.0)
    theta = math.radians(effective_angle)

    ket_theta = np.array([
        math.cos(theta),
        math.sin(theta),
    ], dtype=float)

    return np.outer(ket_theta, ket_theta)


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
        lines.append(
            f"The number of detected packets stayed the same: **{detected_no_eve}**."
        )

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
        lines.append(
            f"The QBER remained unchanged at **{qber_attack:.3f}**."
        )

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
        lines.append(
            f"The success rate remained the same at **{success_attack:.3f}**."
        )

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
                lines.append(
                    "So the dominant decoding channel is still correct."
                )
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
    detector_names = ["detector_1", "detector_2", "detector_3", "detector_4"]

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
            state_vector = ARTICLE_STATE_VECTORS[selected_state_label]
            effective_angles = effective_pr_angles_for_packet(params)
            joint_probs = joint_pattern_probabilities(state_vector, effective_angles)
            ideal_pattern = sample_joint_pattern(joint_probs)

            observed_pattern = []

            for idx, (channel_name, detector_name) in enumerate(zip(channel_names, detector_names)):
                channel = params["channels"][channel_name]
                detector = params["detectors"][detector_name]

                ideal_click = ideal_pattern[idx]

                if random.random() < channel["loss"]:
                    click = 1 if random.random() < detector["dark"] else 0
                else:
                    if ideal_click == 1:
                        click = 1 if random.random() < detector["eta"] else 0
                    else:
                        click = 0

                    if click == 0 and random.random() < detector["dark"]:
                        click = 1

                if channel["eve"]:
                    if random.random() < channel.get("eve_disturbance", 0.0):
                        click = 1 - click

                observed_pattern.append(click)

            packet_detected = any(observed_pattern)

            if packet_detected:
                decoded_state, _ = decode_state_from_pattern(observed_pattern, effective_angles)
                decoded_state_counts[decoded_state] += 1
                confusion_matrix[selected_state_label][decoded_state] += 1

                if decoded_state != selected_state_label:
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

st.divider()

# ============================================================
# Simulation
# ============================================================

st.subheader("Simulation")

if st.button("Run simulation"):
    result_attack = run_simple_simulation(params)
    params_no_eve = clone_params_without_eve(params)
    result_no_eve = run_simple_simulation(params_no_eve)

    st.success("Simulation complete")

    st.subheader("Comparison: without Eve vs with Eve")

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

    if result_attack["source_mode"] == "article_state":
        st.subheader("Confusion Matrix Comparison")

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
