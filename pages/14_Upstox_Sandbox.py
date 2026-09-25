"""Upstox Sandbox page: API testing without live orders."""
import streamlit as st
from algobot import ui
from algobot.upstox_sandbox import UpstoxSandboxClient, UpstoxSandboxError, sandbox_token

ui.setup("Upstox Sandbox", "🧪")
ui.header(
    "Upstox Sandbox",
    "Connect the private sandbox token, test the order lifecycle, and keep live trading completely separate.",
    mode="execution:Sandbox",
)

st.info(
    "🟢 SANDBOX ONLY · This page uses Upstox's sandbox endpoint. "
    "No live Upstox endpoint or live credential is used."
)

# Prefer the process environment, then Streamlit Secrets. Never display the token.
token = sandbox_token()
token_source = "environment" if token else ""
if not token:
    try:
        secret_value = st.secrets.get("UPSTOX_SANDBOX_ACCESS_TOKEN")
        token = str(secret_value).strip() if secret_value else None
        token_source = "Streamlit Secrets" if token else ""
    except Exception:
        token = None

if token:
    st.success(f"✅ Sandbox token detected privately ({token_source}). Token value is never shown.")
else:
    st.warning(
        "No sandbox token detected. Add UPSTOX_SANDBOX_ACCESS_TOKEN to Streamlit Secrets "
        "and refresh the app."
    )

st.markdown("### 1. Sandbox setup")
st.markdown(
    "Upstox sandbox tokens are intended for sandbox orders only. "
    "Upstox currently documents sandbox order placement, modification, and cancellation."
)
st.markdown(
    "[Open the official Upstox Sandbox documentation]"
    "(https://upstox.com/developer/api-documentation/sandbox/)"
)
st.caption(
    "Upstox says sandbox access tokens are valid for 30 days. "
    "Keep the token private and never commit it to GitHub or paste it into chat."
)

st.divider()
st.markdown("### 2. Place a sandbox order")
st.caption(
    "Use an instrument token supplied by Upstox. Do not guess a NIFTY/BANKNIFTY option token; "
    "the token must match the exact sandbox instrument."
)

with st.form("upstox_sandbox_order"):
    instrument_token = st.text_input(
        "Instrument token",
        placeholder="Example: NSE_FO|...",
        help="Use the exact instrument_token supplied by Upstox for the contract you are testing.",
    )
    c1, c2 = st.columns(2)
    with c1:
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        transaction_type = st.selectbox("Side", ["BUY", "SELL"])
        product = st.selectbox("Product", ["D", "I", "MTF"], index=0)
    with c2:
        order_type = st.selectbox("Order type", ["MARKET", "LIMIT", "SL", "SL-M"])
        validity = st.selectbox("Validity", ["DAY", "IOC"])
        disclosed_quantity = st.number_input(
            "Disclosed quantity", min_value=0, value=0, step=1
        )

    price = 0.0
    trigger_price = 0.0
    if order_type in {"LIMIT", "SL"}:
        price = st.number_input(
            "Price", min_value=0.0, value=0.0, step=0.05,
            help="Required for LIMIT and SL orders.",
        )
    if order_type in {"SL", "SL-M"}:
        trigger_price = st.number_input(
            "Trigger price", min_value=0.0, value=0.0, step=0.05,
            help="Required for SL and SL-M orders.",
        )

    confirm = st.checkbox(
        "I confirm this sends an order to UPSTOX SANDBOX ONLY, not live Upstox."
    )
    send = st.form_submit_button("🧪 Send sandbox order", type="primary")

if send:
    if not confirm:
        st.error("Tick the sandbox confirmation first.")
    elif not token:
        st.error("No sandbox token is configured.")
    elif not instrument_token.strip():
        st.error("Enter the Upstox instrument token.")
    else:
        preview = {
            "instrument_token": instrument_token.strip(),
            "quantity": int(quantity),
            "transaction_type": transaction_type,
            "order_type": order_type,
            "product": product,
            "validity": validity,
            "price": float(price),
            "trigger_price": float(trigger_price),
            "disclosed_quantity": int(disclosed_quantity),
            "environment": "UPSTOX SANDBOX",
        }
        st.markdown("**Order preview**")
        st.json(preview)
        try:
            response = UpstoxSandboxClient(token=token).place_order(
                instrument_token=instrument_token,
                quantity=int(quantity),
                transaction_type=transaction_type,
                order_type=order_type,
                product=product,
                validity=validity,
                price=float(price),
                trigger_price=float(trigger_price),
                disclosed_quantity=int(disclosed_quantity),
            )
            st.success("Sandbox order request accepted by Upstox.")
            st.json(response)
            data = response.get("data") or {}
            order_id = data.get("order_id")
            if not order_id:
                order_ids = data.get("order_ids") or []
                order_id = order_ids[0] if order_ids else None
            if order_id:
                st.session_state["upstox_sandbox_order_id"] = order_id
                st.code(order_id, language="text")
        except UpstoxSandboxError as exc:
            st.error(str(exc))

st.divider()
st.markdown("### 3. Modify or cancel the last sandbox order")
last_order = st.session_state.get("upstox_sandbox_order_id")
if last_order:
    st.code(last_order, language="text")
    m1, m2 = st.columns(2)
    with m1:
        modify_confirm = st.checkbox(
            "Confirm sandbox modification",
            key="sandbox_modify_confirm",
        )
        if st.button("Modify last sandbox order", disabled=not modify_confirm):
            try:
                response = UpstoxSandboxClient(token=token).modify_order(
                    last_order,
                    int(quantity),
                    price=float(price),
                    order_type=order_type,
                    trigger_price=float(trigger_price),
                    validity=validity,
                    disclosed_quantity=int(disclosed_quantity),
                )
                st.success("Sandbox modify request accepted.")
                st.json(response)
            except UpstoxSandboxError as exc:
                st.error(str(exc))
    with m2:
        cancel_confirm = st.checkbox(
            "Confirm sandbox cancellation",
            key="sandbox_cancel_confirm",
        )
        if st.button("Cancel last sandbox order", disabled=not cancel_confirm):
            try:
                response = UpstoxSandboxClient(token=token).cancel_order(last_order)
                st.success("Sandbox cancel request accepted.")
                st.json(response)
            except UpstoxSandboxError as exc:
                st.error(str(exc))
else:
    st.caption("Place a sandbox order first; its order ID will appear here.")

st.divider()
st.markdown("### 4. What we are testing")
ui.check_row(
    "PASS",
    "Sandbox endpoint only",
    "The client uses Upstox's official SDK with Configuration(sandbox=True); there is no live-host switch.",
)
ui.check_row(
    "PASS",
    "Private token",
    "The token is read from the environment or Streamlit Secrets and is never displayed.",
)
ui.check_row(
    "PASS",
    "Explicit confirmation",
    "Place, modify, and cancel actions require a separate user confirmation.",
)
ui.check_row(
    "PASS",
    "Existing risk controls untouched",
    "This sandbox page is separate from the existing risk manager and live-trading lock.",
)
ui.check_row(
    "TODO",
    "Strategy-to-order wiring",
    "Only connect approved deterministic strategy signals after the sandbox lifecycle is verified.",
)
ui.footer_note("Upstox Sandbox only. No live orders. Keep the sandbox token private.")
