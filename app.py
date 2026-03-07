import streamlit as st
import numpy as np

st.set_page_config(page_title="Multiphoton Simulator (Quantum Baseline)", layout="wide")
st.title("Multiphoton Entanglement Simulator — Quantum Baseline (4-photon)")
st.image("assets/scheme.png", use_container_width=True)

# =========================================================
# 1) RNG
# =========================================================
def make_rng(seed: int | None) -> np.random.Generator:
    if seed is None:
        seed = int(np.random.SeedSequence().entropy)
    return np.random.default_rng(seed)

# =========================================================
# 2) Text -> bits -> 2-bit blocks
# =========================================================
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

# =========================================================
# 3) Basis and helpers for 4 qubits
#    Convention: |x> = |0>, |y> = |1>
#    Index: b1 b2 b3 b4 -> int(b1*8 + b2*4 + b3*2 + b4)
# =========================================================
def ket_index(b1: int, b2: int, b3: int, b4: int) -> int:
    return (b1 << 3) | (b2 << 2) | (b3 << 1) | b4

def ket(bits4: tuple[int, int, int, int]) -> np.ndarray:
    v = np.zeros(16, dtype=complex)
    v[ket_index(*bits4)] = 1.0
    return v

def projector(psi: np.ndarray) -> np.ndarray:
    return np.outer(psi, psi.conj())

# =========================================================
# 4) Define psi1..psi4 exactly as in your formula (4)
#    |psi1> = 1/2 (|y x y x> + |x y x y> + |x x y y> + |y y x x>)  == 00
#    |psi2> = 1/2 (|y x y y> + |x y x x> + |x x y x> + |y y x y>)  == 01
#    |psi3> = 1/2 (|y y y y> + |x x x x> + |x y y x> + |y x x y>)  == 10
#    |psi4> = 1/2 (|y y y x> + |x x x y> + |x y y y> + |y x x x>)  == 11
# =========================================================
def build_psi_states() -> dict[str, np.ndarray]:
    x = 0
    y = 1

    psi1 = 0.5 * (ket((y, x, y, x)) + ket((x, y, x, y)) + ket((x, x, y, y)) + ket((y, y, x, x)))
    psi2 = 0.5 * (ket((y, x, y, y)) + ket((x, y, x, x)) + ket((x, x, y, x)) + ket((y, y, x, y)))
    psi3 = 0.5 * (ket((y, y, y, y)) + ket((x, x, x, x)) + ket((x, y, y, x)) + ket((y, x, x, y)))
    psi4 = 0.5 * (ket((y, y, y, x)) + ket((x, x, x, y)) + ket((x, y, y, y)) + ket((y, x, x, x)))

    # normalize defensively (should already be normalized)
    psi1 = psi1 / np.linalg.norm(psi1)
    psi2 = psi2 / np.linalg.norm(psi2)
    psi3 = psi3 / np.linalg.norm(psi3)
    psi4 = psi4 / np.linalg.norm(psi4)

    return {"psi1": psi1, "psi2": psi2, "psi3": psi3, "psi4": psi4}

PSI = build_psi_states()
P = {name: projector(vec) for name, vec in PSI.items()}

BITS_TO_PSI = {
    (0, 0): "psi1",
    (0, 1): "psi2",
    (1, 0): "psi3",
    (1, 1): "psi4",
}
PSI_TO_BITS = {v: k for k, v in BITS_TO_PSI.items()}

# =========================================================
# 5) Depolarizing noise (per qubit), applied to density matrix
#    rho -> (1-p) rho + (p/3) (X rho X + Y rho Y + Z rho Z)  on each qubit
# =========================================================
I2 = np.array([[1, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

def op_on_qubit(single_qubit_op: np.ndarray, qubit_index: int) -> np.ndarray:
    # qubit_index: 0..3 corresponds to photon 1..4
    ops = []
    for i in range(4):
        ops.append(single_qubit_op if i == qubit_index else I2)
    out = ops[0]
    for k in range(1, 4):
        out = np.kron(out, ops[k])
    return out

OPS_X = [op_on_qubit(X, i) for i in range(4)]
OPS_Y = [op_on_qubit(Y, i) for i in range(4)]
OPS_Z = [op_on_qubit(Z, i) for i in range(4)]

def depolarize_each_qubit(rho: np.ndarray, p: float) -> np.ndarray:
    if p <= 0.0:
        return rho
    p = float(np.clip(p, 0.0, 1.0))
    out = rho
    for i in range(4):
        Xi, Yi, Zi = OPS_X[i], OPS_Y[i], OPS_Z[i]
        out = (1 - p) * out + (p / 3.0) * (Xi @ out @ Xi.conj().T + Yi @ out @ Yi.conj().T + Zi @ out @ Zi.conj().T)
    return out

# =========================================================
# 6) Quantum measurement in {psi1..psi4}
#    p(i) = Tr(Pi rho)
# =========================================================
def measure_in_psi_basis(rho: np.ndarray, rng: np.random.Generator) -> str:
    probs = []
    names = ["psi1", "psi2", "psi3", "psi4"]
    for name in names:
        prob = np.trace(P[name] @ rho).real
        probs.append(max(0.0, prob))
    s = sum(probs)
    if s <= 0:
        # fallback
        return "psi1"
    probs = [p / s for p in probs]
    idx = int(rng.choice(len(names), p=probs))
    return names[idx]

# =========================================================
# 7) Event layer (loss + detectors) + Quantum decoding
# =========================================================
def simulate_quantum_baseline(
    message_text: str,
    num_packets: int,
    require_all_4_clicks: bool,
    photon_loss_probability: float,
    detector_efficiency: float,
    dark_count_probability: float,
    polarization_noise_p: float,
    seed: int | None,
):
    rng = make_rng(seed)

    bits = text_to_bits(message_text)
    blocks = bits_to_2bit_blocks(bits)
    if not blocks:
        blocks = [(0, 0)]

    packets_sent = num_packets
    packets_received = 0

    bob_bits_total = 0
    bob_bit_errors = 0

    for i in range(packets_sent):
        original_bits = (blocks[i % len(blocks)][0] & 1, blocks[i % len(blocks)][1] & 1)

        # Alice encodes by choosing the corresponding psi-state (formula (4))
        psi_name = BITS_TO_PSI[original_bits]
        psi_vec = PSI[psi_name]
        rho = projector(psi_vec)

        # Channel losses + detector clicks (post-selection-like acceptance)
        arrived = [rng.random() > photon_loss_probability for _ in range(4)]
        clicks = []
        for a in arrived:
            if a:
                click = rng.random() < detector_efficiency
            else:
                click = rng.random() < dark_count_probability
            clicks.append(click)

        accepted = all(clicks) if require_all_4_clicks else (sum(clicks) >= 3)
        if not accepted:
            continue

        packets_received += 1

        # Quantum noise on polarization (depolarization per photon)
        rho_noisy = depolarize_each_qubit(rho, polarization_noise_p)

        # Bob measures in the psi-basis (Born rule)
        measured_psi = measure_in_psi_basis(rho_noisy, rng)
        decoded_bits = PSI_TO_BITS[measured_psi]

        bob_bits_total += 2
        bob_bit_errors += int(decoded_bits[0] != original_bits[0])
        bob_bit_errors += int(decoded_bits[1] != original_bits[1])

    success_rate = packets_received / packets_sent if packets_sent else 0.0
    bob_ber = bob_bit_errors / bob_bits_total if bob_bits_total else 0.0

    return {
        "packets_sent": packets_sent,
        "packets_received": packets_received,
        "success_rate": success_rate,
        "bob_ber": bob_ber,
        "bob_bits_total": bob_bits_total,
    }

# =========================================================
# 8) UI
# =========================================================
st.sidebar.header("Randomness")
seed_input = st.sidebar.number_input("Seed (int). Use -1 for random", value=42, step=1)
seed = None if int(seed_input) == -1 else int(seed_input)

st.sidebar.header("Experiment size")
num_packets = st.sidebar.slider("Packets to simulate (quantum is heavier)", 100, 20000, 2000, 100)

st.sidebar.header("Channel losses / detectors (post-selection)")
photon_loss_probability = st.sidebar.slider("Photon loss probability", 0.0, 0.9, 0.05, 0.01)
detector_efficiency = st.sidebar.slider("Detector efficiency η", 0.0, 1.0, 0.85, 0.01)
dark_count_probability = st.sidebar.slider("Dark count probability", 0.0, 0.2, 0.0, 0.001)
require_all_4_clicks = st.sidebar.checkbox("Require 4/4 clicks (else accept 3/4)", value=True)

st.sidebar.header("Polarization noise (quantum)")
polarization_noise_p = st.sidebar.slider("Depolarization p per photon", 0.0, 0.5, 0.02, 0.005)

st.subheader("Message")
message_text = st.text_area("Text Alice wants to send", value="Hello, Bob!")

if st.button("Run quantum baseline"):
    result = simulate_quantum_baseline(
        message_text=message_text,
        num_packets=int(num_packets),
        require_all_4_clicks=bool(require_all_4_clicks),
        photon_loss_probability=float(photon_loss_probability),
        detector_efficiency=float(detector_efficiency),
        dark_count_probability=float(dark_count_probability),
        polarization_noise_p=float(polarization_noise_p),
        seed=seed,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Packets sent", result["packets_sent"])
    col2.metric("Packets received", result["packets_received"])
    col3.metric("Success rate", f'{result["success_rate"]:.3f}')

    st.metric("Bob BER (quantum)", f'{result["bob_ber"]:.5f}')
    st.caption(
        "This uses Born rule measurement in the {|psi1>,|psi2>,|psi3>,|psi4>} basis from formula (4). "
        "Noise is depolarization per photon; losses+detectors define acceptance (post-selection-like)."
    )
