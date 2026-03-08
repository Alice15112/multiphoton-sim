import streamlit as st
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Multiphoton Quantum Simulator", layout="wide")

st.title("Multiphoton Quantum Communication Simulator")

st.markdown(
"""
Interactive simulator of the quantum communication scheme.

Click elements of the scheme to configure:
- channels
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
        "channels": {
            "channel_1": {"loss": 0.05, "eve": False},
            "channel_2": {"loss": 0.05, "eve": False},
            "channel_3": {"loss": 0.05, "eve": False},
            "channel_4": {"loss": 0.05, "eve": False},
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
        }
    }

params = st.session_state.scheme_params


# ============================================================
# Click zones on scheme
# ============================================================

CLICK_ZONES = {

    "channel_1": {"x1": 640, "x2": 670, "y1": 73, "y2": 134},
    "channel_2": {"x1": 640, "x2": 670, "y1": 281, "y2": 330},
    "channel_3": {"x1": 640, "x2": 670, "y1": 230, "y2": 300},
    "channel_4": {"x1": 640, "x2": 670, "y1": 367, "y2": 421},

    "detector_1": {"x1": 822, "x2": 918, "y1": 60, "y2": 150},
    "detector_2": {"x1": 822, "x2": 918, "y1": 150, "y2": 250},
    "detector_3": {"x1": 822, "x2": 918, "y1": 250, "y2": 310},
    "detector_4": {"x1": 822, "x2": 918, "y1": 350, "y2": 450},

    "bs_left": {"x1": 87, "x2": 140, "y1": 236, "y2": 265},
    "bs_right": {"x1": 526, "x2": 600, "y1": 239, "y2": 257},
}


def detect_clicked_zone(coords, zones):

    if coords is None:
        return None

    x = coords["x"]
    y = coords["y"]

    for zone_name, zone in zones.items():
        if zone["x1"] <= x <= zone["x2"] and zone["y1"] <= y <= zone["y2"]:
            return zone_name

    return None


# ============================================================
# Display scheme
# ============================================================

st.subheader("Experimental Scheme")

image = Image.open("assets/scheme.png")

coords = streamlit_image_coordinates(
    image,
    key="scheme"
)

clicked_zone = detect_clicked_zone(coords, CLICK_ZONES)

if clicked_zone is not None:
    st.session_state.selected_element = clicked_zone

selected = st.session_state.selected_element

st.caption(f"Clicked coordinates: {coords}")
st.caption(f"Selected element: {selected}")

st.divider()

# ============================================================
# Settings panel
# ============================================================

st.subheader("Element Settings")

if selected is None:

    st.info("Click any element on the scheme to configure it.")

# ------------------------------------------------------------
# CHANNEL SETTINGS
# ------------------------------------------------------------

elif selected.startswith("channel"):

    st.markdown(f"### {selected}")

    eve = st.checkbox(
        "Eve taps this channel",
        value=params["channels"][selected]["eve"]
    )

    loss = st.slider(
        "Channel loss",
        0.0,
        1.0,
        params["channels"][selected]["loss"],
        0.01
    )

    params["channels"][selected]["eve"] = eve
    params["channels"][selected]["loss"] = loss

# ------------------------------------------------------------
# DETECTOR SETTINGS
# ------------------------------------------------------------

elif selected.startswith("detector"):

    st.markdown(f"### {selected}")

    eta = st.slider(
        "Detector efficiency η",
        0.0,
        1.0,
        params["detectors"][selected]["eta"],
        0.01
    )

    dark = st.slider(
        "Dark count probability",
        0.0,
        0.2,
        params["detectors"][selected]["dark"],
        0.001
    )

    params["detectors"][selected]["eta"] = eta
    params["detectors"][selected]["dark"] = dark


# ------------------------------------------------------------
# BEAM SPLITTER SETTINGS
# ------------------------------------------------------------

elif selected.startswith("bs"):

    st.markdown(f"### {selected}")

    loss = st.slider(
        "Beam splitter loss",
        0.0,
        1.0,
        params["beam_splitters"][selected]["loss"],
        0.01
    )

    params["beam_splitters"][selected]["loss"] = loss


st.divider()

# ============================================================
# Display current configuration
# ============================================================

st.subheader("Current Scheme Configuration")

st.json(params)


st.divider()

# ============================================================
# Simulation block placeholder
# ============================================================

st.subheader("Simulation")

message = st.text_input(
    "Message Alice sends",
    value="Hello Bob"
)

num_packets = st.slider(
    "Number of photon packets",
    100,
    20000,
    2000,
    100
)

if st.button("Run simulation"):

    st.success("Simulation placeholder")

    st.write("Message:", message)
    st.write("Packets:", num_packets)

    st.write("Active Eve channels:")

    eve_channels = [
        ch for ch, v in params["channels"].items()
        if v["eve"]
    ]

    st.write(eve_channels)
