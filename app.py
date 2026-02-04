import streamlit as st
import numpy as np

st.set_page_config(page_title="Multiphoton Simulator (Baseline)", layout="wide")
st.title("Multiphoton Entanglement Simulator — Baseline (4-photon MVP)")

# -------------------------
# Helpers (single-file MVP)
# -------------------------
def make_rng(seed: int | None) -> np.random.Generator:
    if seed is None:
        seed = int(np.random.SeedSequence().entropy)
    return np.random.default_rng(seed)

def text_to_bits(text: str) -> list[int]:
    data = text.encode("utf-8")
    bits: list[int] = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_2bit_blocks(bits: list[int]) -> list[tuple[int, int]]:
    if len(bits) % 2 != 0:
        bits = bits + [0]
    return [(bits[i], bits[i + 1]) for i in range(0, len(bits), 2)]

def simulate_baseline(
    message_text: str,
    num_packets: int,
    require_all_4_clicks: bool,
    photon_loss_probability: float,
    detector_efficiency: float,
    dark_count_probability: float,
    base_delay_us: float,
    jitter_us: float,
    eve_extra_delay_us: float,
    seed: int | None,
):
    rng = make_rng(seed)

    # message blocks (2 bits per packet)
    bits = text_to_bits(message_text)
    blocks = bits_to_2bit_blocks(bits)
    if not blocks:
        blocks = [(0, 0)]

    packets_sent = num_packets
    packets_received = 0
    bob_bits_total = 0
    bob_bit_errors = 0

    eve_blocks_total = 0
    eve_correct_blocks = 0

    delay_sum_s = 0.0

    for i in range(packets_sent):
        original = blocks[i % len(blocks)]

        # Channel: 4 photons survive?
        arrived = [rng.random() > photon_loss_probability for _ in range(4)]

        # Detector clicks
        clicks = []
        for a in arrived:
            if a:
                click = rng.random() < detector_efficiency
            else:
                click = rng.random() < dark_count_probability
            clicks.append(click)

        accepted = all(clicks) if require_all_4_clicks else (sum(clicks) >= 3)

        # Timing (for display / future Protocol 1)
        jitter_s = rng.normal(0.0, jitter_us * 1e-6) if jitter_us > 0 else 0.0
        delay_s = max(0.0, base_delay_us * 1e-6 + jitter_s + eve_extra_delay_us * 1e-6)
        delay_sum_s += delay_s

        if not accepted:
            continue

        packets_received += 1

        # MVP: Bob decodes perfectly if accepted
        decoded = (original[0] & 1, original[1] & 1)
        bob_bits_total += 2
        bob_bit_errors += int(decoded[0] != (original[0] & 1))
        bob_bit_errors += int(decoded[1] != (original[1] & 1))

        # MVP: Eve guesses randomly (will improve later)
        eve_guess = (int(rng.integers(0, 2)), int(rng.integers(0, 2)))
        eve_correct_blocks += int(eve_guess == (original[0] & 1, original[1] & 1))
        eve_blocks_total += 1

    success_rate = packets_received / packets_sent if packets_sent else 0.0
    bob_ber = bob_bit_errors / bob_bits_total if bob_bits_total else 0.0
    eve_acc = eve_correct_blocks / eve_blocks_total if eve_blocks_total else 0.0
    avg_delay_us = (delay_sum_s / packets_sent) * 1e6 if packets_sent else 0.0

    return {
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "success_rate": success_rate,
        "bob_ber": bob_ber,
        "eve_block_accuracy": eve_acc,
        "avg_delay_us": avg_delay_us,
    }

# -------------------------
# UI
# -------------------------
st.sidebar.header("Randomness")
seed_input = st.sidebar.number_input("Seed (int). Use -1 for random", value=42, step=1)
seed = None if int(seed_input) == -1 else int(seed_input)

st.sidebar.header("Experiment size")
num_packets = st.sidebar.slider("Packets to simulate", 100, 200000, 20000, 100)

st.sidebar.header("Channel")
photon_loss_probability = st.sidebar.slider("Photon loss probability", 0.0, 0.9, 0.05, 0.01)
base_delay_us = st.sidebar.slider("Base delay (µs)", 0.0, 5000.0, 1.0, 0.5)
jitter_us = st.sidebar.slider("Jitter std (µs)", 0.0, 5000.0, 0.0, 0.5)

st.sidebar.header("Detectors")
detector_efficiency = st.sidebar.slider("Detector efficiency η", 0.0, 1.0, 0.8, 0.01)
dark_count_probability = st.sidebar.slider("Dark count probability", 0.0, 0.2, 0.0, 0.001)

st.sidebar.header("Eavesdropper (Eve)")
eve_extra_delay_us = st.sidebar.slider("Extra delay added by Eve (µs)", 0.0, 5000.0, 0.0, 0.5)

st.sidebar.header("Acceptance rule")
require_all_4_clicks = st.sidebar.checkbox("Require 4/4 clicks (else accept 3/4)", value=True)

st.subheader("Message")
message_text = st.text_area("Text Alice wants to send", value="Hello, Bob!")

if st.button("Run simulation"):
    result = simulate_baseline(
        message_text=message_text,
        num_packets=int(num_packets),
        require_all_4_clicks=bool(require_all_4_clicks),
        photon_loss_probability=float(photon_loss_probability),
        detector_efficiency=float(detector_efficiency),
        dark_count_probability=float(dark_count_probability),
        base_delay_us=float(base_delay_us),
        jitter_us=float(jitter_us),
        eve_extra_delay_us=float(eve_extra_delay_us),
        seed=seed,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Packets sent", result["packets_sent"])
    col2.metric("Packets received", result["packets_received"])
    col3.metric("Success rate", f'{result["success_rate"]:.3f}')
    col4.metric("Avg delay (µs)", f'{result["avg_delay_us"]:.2f}')

    col1, col2 = st.columns(2)
    col1.metric("Bob BER", f'{result["bob_ber"]:.4f}')
    col2.metric("Eve block accuracy", f'{result["eve_block_accuracy"]:.4f}')

    st.caption("MVP note: Bob decodes perfectly if a packet is accepted; Eve currently guesses randomly. We'll improve both next.")
