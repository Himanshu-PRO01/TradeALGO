"""Upstox Sandbox page: API testing without live orders."""
import streamlit as st
from algobot import ui
from algobot.upstox_sandbox import UpstoxSandboxClient, UpstoxSandboxError, sandbox_token

ui.setup("Upstox Sandbox","🧪")
ui.header("Upstox Sandbox",
          "Test the Upstox API order workflow without touching live funds.",
          mode="execution:Sandbox")

st.info("🟢 SANDBOX ONLY · This page uses only Upstox's sandbox endpoint. No live order endpoint is available here.")

token=sandbox_token()
if token:
    st.success("Sandbox token detected privately. It is not displayed.")
else:
    st.warning("No sandbox token detected. Set UPSTOX_SANDBOX_ACCESS_TOKEN privately before sending a test order.")

st.markdown("### 1. Create the sandbox app")
st.markdown("Create a **Sandbox App** in Upstox Developer Apps and generate its sandbox access token.")
st.markdown("[Open Upstox Sandbox documentation](https://upstox.com/developer/api-documentation/sandbox/)")

st.markdown("### 2. Store the token privately")
st.code("UPSTOX_SANDBOX_ACCESS_TOKEN=your_token_here",language="text")
st.caption("Local: environment variable. Streamlit Cloud: App Settings → Secrets. Never commit the token to GitHub or paste it into chat.")

st.divider()
st.markdown("### 3. Send a sandbox order")
st.caption("Enter an instrument token supplied by Upstox. Do not guess a contract token.")
with st.form("upstox_sandbox_order"):
    instrument_token=st.text_input("Instrument token",placeholder="NSE_FO|...")
    quantity=st.number_input("Quantity",min_value=1,value=1,step=1)
    transaction_type=st.selectbox("Side",["BUY","SELL"])
    order_type=st.selectbox("Order type",["MARKET","LIMIT"])
    price=st.number_input("Limit price",min_value=0.0,value=0.0,step=0.05) if order_type=="LIMIT" else 0.0
    confirm=st.checkbox("I confirm this sends an order to UPSTOX SANDBOX ONLY, not live Upstox.")
    send=st.form_submit_button("🧪 Send sandbox order",type="primary")

if send:
    if not confirm: st.error("Tick the sandbox confirmation first.")
    elif not token: st.error("No sandbox token is configured.")
    elif not instrument_token.strip(): st.error("Enter the Upstox instrument token.")
    else:
        try:
            response=UpstoxSandboxClient(token=token).place_order(
                instrument_token, int(quantity), transaction_type, order_type=order_type, price=float(price))
            st.success("Sandbox order request accepted by Upstox.")
            st.json(response)
            order_id=(response.get("data") or {}).get("order_id")
            if order_id:
                st.session_state["upstox_sandbox_order_id"]=order_id
                st.code(order_id,language="text")
        except UpstoxSandboxError as exc: st.error(str(exc))

st.divider()
st.markdown("### 4. Modify or cancel the last sandbox order")
last_order=st.session_state.get("upstox_sandbox_order_id")
if last_order:
    st.code(last_order,language="text")
    m1,m2=st.columns(2)
    with m1:
        if st.button("Modify last sandbox order"):
            try:
                response=UpstoxSandboxClient(token=token).modify_order(last_order,int(quantity),price=float(price))
                st.success("Sandbox modify request accepted."); st.json(response)
            except UpstoxSandboxError as exc: st.error(str(exc))
    with m2:
        if st.button("Cancel last sandbox order"):
            try:
                response=UpstoxSandboxClient(token=token).cancel_order(last_order)
                st.success("Sandbox cancel request accepted."); st.json(response)
            except UpstoxSandboxError as exc: st.error(str(exc))
else: st.caption("Place a sandbox order first; its order ID will appear here.")

st.divider()
ui.check_row("PASS","Live endpoint is not used","The client is hard-coded to sandbox.upstox.com.")
ui.check_row("PASS","No live credentials requested","Only UPSTOX_SANDBOX_ACCESS_TOKEN is read.")
ui.check_row("PASS","Existing risk controls are untouched","This is a separate sandbox integration layer.")
ui.check_row("TODO","Strategy-to-order wiring","Only connect approved deterministic strategy signals after sandbox order plumbing is verified.")
ui.footer_note("Upstox Sandbox only. No live orders. Keep the sandbox token private.")
