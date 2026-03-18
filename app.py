import streamlit as st
from PIL import Image, ImageDraw
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
        "source": {
            "message": "Hello Bob",
            "num_packets": 2000,
            "pair_generation_efficiency": 0.95
        },
        "channels": {
            "channel_1": {"loss": 0.05, "eve": False},
            "channel_2": {"loss": 0.05, "eve": False},
            "channel_3": {"loss": 0.05, "eve": False},
            "channel_4": {"loss": 0.05, "eve": False},
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
        }
    }

params = st.session_state.scheme_params
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

# ============================================================
# Display scheme
# ============================================================

st.subheader("Experimental Scheme")

def draw_highlight_on_scheme(image: Image.Image, selected: str, zones: dict) -> Image.Image:
    """
    Draw a rectangle around the selected element on the scheme.
    Returns a copy of the image with highlighting.
    """
    highlighted = image.copy()
    draw = ImageDraw.Draw(highlighted)

    if selected in zones:
        zone = zones[selected]
        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]

        draw.rectangle([x1, y1, x2, y2], outline="red", width=4)
        draw.rectangle([x1 + 2, y1 + 2, x2 - 2, y2 - 2], outline="yellow", width=2)

    return highlighted

base_image = Image.open("assets/scheme.png")

display_image = draw_highlight_on_scheme(
    base_image,
    st.session_state.selected_element,
    CLICK_ZONES
)

coords = streamlit_image_coordinates(
    display_image,
    key="scheme"
)

clicked_zone = detect_clicked_zone(coords, CLICK_ZONES)

if clicked_zone is not None:
    st.session_state.selected_element = clicked_zone
    st.rerun()

selected = st.session_state.selected_element

st.caption(f"Clicked coordinates: {coords}")
st.caption(f"Selected element: {selected}")

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

elif selected.startswith("pr"):

    st.markdown(f"### {selected}")

    angle = st.slider(
        "Polarization rotation angle",
        -180.0,
        180.0,
        params["pr"][selected]["angle"],
        1.0
    )

    error = st.slider(
        "Rotation error",
        0.0,
        0.2,
        params["pr"][selected]["error"],
        0.01
    )

    params["pr"][selected]["angle"] = angle
    params["pr"][selected]["error"] = error
    
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

elif selected == "source":

    st.markdown("### source")

    message = st.text_input(
        "Message Alice sends",
        value=params["source"]["message"]
    )

    num_packets = st.slider(
        "Number of photon packets",
        100,
        20000,
        params["source"]["num_packets"],
        100
    )

    pair_generation_efficiency = st.slider(
        "Pair generation efficiency",
        0.0,
        1.0,
        params["source"]["pair_generation_efficiency"],
        0.01
    )

    params["source"]["message"] = message
    params["source"]["num_packets"] = num_packets
    params["source"]["pair_generation_efficiency"] = pair_generation_efficiency

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

message = params["source"]["message"]
num_packets = params["source"]["num_packets"]

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
