import math
import random

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
# Article-inspired states
# ============================================================

ARTICLE_STATES = {
    "psi1": [
        {"channel_1": "y", "channel_2": "x", "channel_3": "y", "channel_4": "x"},
        {"channel_1": "x", "channel_2": "y", "channel_3": "x", "channel_4": "y"},
        {"channel_1": "x", "channel_2": "x", "channel_3": "y", "channel_4": "y"},
        {"channel_1": "y", "channel_2": "y", "channel_3": "x", "channel_4": "x"},
    ],
    "psi2": [
        {"channel_1": "y", "channel_2": "x", "channel_3": "y", "channel_4": "y"},
        {"channel_1": "x", "channel_2": "y", "channel_3": "x", "channel_4": "x"},
        {"channel_1": "x", "channel_2": "x", "channel_3": "y", "channel_4": "x"},
        {"channel_1": "y", "channel_2": "y", "channel_3": "x", "channel_4": "y"},
    ],
    "psi3": [
        {"channel_1": "y", "channel_2": "y", "channel_3": "y", "channel_4": "y"},
        {"channel_1": "x", "channel_2": "x", "channel_3": "x", "channel_4": "x"},
        {"channel_1": "x", "channel_2": "y", "channel_3": "y", "channel_4": "x"},
        {"channel_1": "y", "channel_2": "x", "channel_3": "x", "channel_4": "y"},
    ],
    "psi4": [
        {"channel_1": "y", "channel_2": "y", "channel_3": "y", "channel_4": "x"},
        {"channel_1": "x", "channel_2": "x", "channel_3": "x", "channel_4": "y"},
        {"channel_1": "x", "channel_2": "y", "channel_3": "y", "channel_4": "y"},
        {"channel_1": "y", "channel_2": "x", "channel_3": "x", "channel_4": "x"},
    ],
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
    """
    Malus-like law:
    P = cos^2(theta_state - theta_PR_effective)
    """
    effective_pr_angle = pr_angle_deg + random.uniform(-pr_error * 180.0, pr_error * 180.0)
    angle_diff_rad = math.radians(state_angle_deg - effective_pr_angle)
    probability = math.cos(angle_diff_rad) ** 2
    return max(0.0, min(1.0, probability))


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
    pr_names = ["pr_1", "pr_2", "pr_3", "pr_4"]
    detector_names = ["detector_1", "detector_2", "detector_3", "detector_4"]

    for _ in range(num_packets):
        if random.random() > pair_eff:
            continue

        transmitted += 1

        if source_mode == "article_state" and selected_state_label in ARTICLE_STATES:
            component = random.choice(ARTICLE_STATES[selected_state_label])
            state_angles_this_packet = {
                ch: polarization_label_to_angle(component[ch]) for ch in channel_names
            }
        else:
            state_angles_this_packet = params["source"]["state_angles"].copy()

        packet_detected = False
        packet_error = False

        for channel_name, pr_name, detector_name in zip(channel_names, pr_names, detector_names):
            channel = params["channels"][channel_name]
            pr = params["pr"][pr_name]
            detector = params["detectors"][detector_name]

            if random.random() < channel["loss"]:
                continue

            channel_state_angle = state_angles_this_packet[channel_name]

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

            if click:
                packet_detected = True

                basis_error = 1.0 - p_quantum
                local_error_probability = min(1.0, basis_error + eve_disturbance)

                if random.random() < local_error_probability:
                    packet_error = True

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
    result = run_simple_simulation(params)

    st.success("Simulation complete")

    col1, col2, col3 = st.columns(3)
    col1.metric("Packets launched", result["num_packets"])
    col2.metric("Packets detected", result["detected"])
    col3.metric("Errors", result["errors"])

    col1, col2 = st.columns(2)
    col1.metric("Success rate", f"{result['success_rate']:.3f}")
    col2.metric("QBER", f"{result['qber']:.3f}")

    st.write("Message:", result["message"])
    st.write("Active Eve channels:", result["eve_channels"])
    st.write("Source mode:", result["source_mode"])
    st.write("Selected source state:", result["selected_state_label"])
