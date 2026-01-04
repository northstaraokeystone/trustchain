"""
TrustChain Streamlit Demo - CLAUDEME v3.1 Compliant

Public demonstration interface:
- Paste receipt JSON, see traffic light instantly
- Example buttons for high/medium/low trust receipts
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import streamlit as st
except ImportError:
    print("Streamlit not installed. Run: pip install streamlit")
    sys.exit(1)

from src.trust_score import compute_trust_score
from src.traffic_light import render_traffic_light, select_emoji, get_trust_level


# Example receipts
EXAMPLE_HIGH_TRUST = {
    "receipt_type": "decision",
    "ts": "2025-01-04T10:30:00Z",
    "tenant_id": "default",
    "decision_id": "nav-001",
    "action": "navigate_waypoint",
    "confidence": 0.95,
    "raci": {"accountable": "CPT Anderson"},
    "sources": ["sensor_1", "sensor_2", "map_data", "weather_api", "intel_feed"],
    "monte_carlo_validated": True,
    "human_verified": True
}

EXAMPLE_MEDIUM_TRUST = {
    "receipt_type": "decision",
    "ts": "2025-01-04T11:45:00Z",
    "tenant_id": "default",
    "decision_id": "log-042",
    "action": "reorder_supplies",
    "confidence": 0.72,
    "raci": {"accountable": "SGT Williams"},
    "sources": ["inventory_db", "forecast_model"],
    "monte_carlo_validated": False,
    "human_verified": False
}

EXAMPLE_LOW_TRUST = {
    "receipt_type": "decision",
    "ts": "2025-01-04T09:15:00Z",
    "tenant_id": "default",
    "decision_id": "maint-099",
    "action": "defer_maintenance",
    "confidence": 0.45,
    "sources": [],
    "monte_carlo_validated": False,
    "human_verified": False
}


def main():
    st.set_page_config(
        page_title="TRUSTCHAIN - AI Decision Trust",
        page_icon="🚦",
        layout="centered"
    )

    st.title("🚦 TRUSTCHAIN")
    st.subheader("Receipts-to-Trust Traffic Light")

    st.markdown("""
    Paste a receipt JSON below to see the trust assessment.
    The traffic light shows whether to **trust**, **review**, or **override** the AI decision.
    """)

    # Example buttons
    st.markdown("### Quick Examples")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ High Trust", use_container_width=True):
            st.session_state.receipt_json = json.dumps(EXAMPLE_HIGH_TRUST, indent=2)

    with col2:
        if st.button("⚠️ Medium Trust", use_container_width=True):
            st.session_state.receipt_json = json.dumps(EXAMPLE_MEDIUM_TRUST, indent=2)

    with col3:
        if st.button("❌ Low Trust", use_container_width=True):
            st.session_state.receipt_json = json.dumps(EXAMPLE_LOW_TRUST, indent=2)

    # Initialize session state
    if "receipt_json" not in st.session_state:
        st.session_state.receipt_json = ""

    # Text area for receipt JSON
    st.markdown("### Receipt JSON")
    receipt_json = st.text_area(
        "Paste receipt JSON here:",
        value=st.session_state.receipt_json,
        height=200,
        key="receipt_input"
    )

    # Analyze button
    if st.button("🔍 Analyze Trust", type="primary", use_container_width=True):
        if not receipt_json.strip():
            st.error("Please paste a receipt JSON or click an example button.")
        else:
            try:
                receipt = json.loads(receipt_json)

                # Compute trust score
                score = compute_trust_score(receipt)
                trust_level = get_trust_level(score)
                emoji = select_emoji(score)

                # Display traffic light
                st.markdown("---")

                # Color-coded result box
                if trust_level == "GREEN":
                    color = "#28a745"
                    message = "Trust this AI decision"
                elif trust_level == "YELLOW":
                    color = "#ffc107"
                    message = "Review before proceeding"
                else:
                    color = "#dc3545"
                    message = "Override recommended"

                st.markdown(f"""
                <div style="
                    background-color: {color};
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    font-size: 24px;
                    margin: 20px 0;
                ">
                    {emoji} TRUST STATUS: {trust_level}<br>
                    <span style="font-size: 18px;">{message}</span>
                </div>
                """, unsafe_allow_html=True)

                # Display traffic light text
                output = render_traffic_light(score, receipt)
                st.code(output, language=None)

                # Expandable receipt view
                with st.expander("📋 View Full Receipt"):
                    st.json(receipt)

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")
            except Exception as e:
                st.error(f"Error processing receipt: {e}")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 12px;">
        TrustChain v1.0 | CLAUDEME v3.1 Compliant |
        The traffic light IS the interface
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
