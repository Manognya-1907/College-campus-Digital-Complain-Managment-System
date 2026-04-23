import requests
import streamlit as st

API_BASE_URL = "https://college-campus-digital-complain.onrender.com"
DEPARTMENTS = ["IT", "Library", "Admin", "Accounts", "Hostel"]
TICKET_STATUSES = ["Open", "In Progress", "Closed"]


def apply_custom_styles():
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 45%, #ecfeff 100%);
            }
            .block-container {
                padding-top: 3.5rem;
                padding-bottom: 1.5rem;
            }
            
            .main .block-container p, 
            .main .block-container h1, 
            .main .block-container h2, 
            .main .block-container h3, 
            .main .block-container label {
                color: #0f172a !important; 
            }

            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1e3a8a 0%, #0f172a 100%);
            }
            section[data-testid="stSidebar"] * {
                color: #f8fafc !important;
            }
            div[data-testid="stMetric"] {
                background: #ffffffcc;
                border: 1px solid #dbeafe;
                border-radius: 12px;
                padding: 8px 12px;
            }
            .app-hero {
                background: linear-gradient(90deg, #2563eb 0%, #0ea5e9 100%);
                color: white;
                padding: 14px 18px;
                border-radius: 12px;
                margin-bottom: 12px;
                box-shadow: 0 8px 20px rgba(37, 99, 235, 0.18);
            }
            .auth-title {
                text-align: center;
                font-size: 1.6rem;
                font-weight: 700;
                color: #0f172a;
                margin-top: 1.2rem;
                margin-bottom: 0.2rem;
            }
            .auth-subtitle {
                text-align: center;
                color: #334155;
                margin-bottom: 1rem;
            }
            .stButton > button {
                border-radius: 10px;
                border: none;
                color: white;
                background: linear-gradient(90deg, #2563eb 0%, #0284c7 100%);
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    if "token" not in st.session_state:
        st.session_state.token = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "name" not in st.session_state:
        st.session_state.name = None
    if "email" not in st.session_state:
        st.session_state.email = None


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_request(method, path, data=None, use_auth=False):
    headers = {}
    if use_auth:
        headers.update(auth_headers())
    response = requests.request(
        method=method, url=f"{API_BASE_URL}{path}", json=data, headers=headers, timeout=20
    )
    return response


def safe_json(response):
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return None


def response_error_message(response, fallback):
    payload = safe_json(response)
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    text = (response.text or "").strip()
    if text:
        return f"{fallback} (HTTP {response.status_code}): {text[:200]}"
    return f"{fallback} (HTTP {response.status_code})"


def show_auth():
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown('<div class="auth-title">Campus Compliance System</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-subtitle">Secure login to raise and manage campus tickets</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Login", "Register"])

            with tab_login:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Login", use_container_width=True):
                    res = api_request("POST", "/login", {"email": email, "password": password})
                    if res.ok:
                        data = safe_json(res) or {}
                        st.session_state.token = data["access_token"]
                        st.session_state.role = data["role"]
                        st.session_state.name = data["name"]
                        st.session_state.email = data["email"]
                        st.success("Login successful")
                        st.rerun()
                    else:
                        st.error(response_error_message(res, "Login failed"))

            with tab_register:
                name = st.text_input("Name", key="reg_name")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password")
                role = st.selectbox("Role", ["student", "department", "admin"])
                st.caption(
                    "For department users, set Name exactly as department (e.g., IT, Library)."
                )
                if st.button("Register", use_container_width=True):
                    payload = {"name": name, "email": email, "password": password, "role": role}
                    res = api_request("POST", "/register", payload)
                    if res.ok:
                        st.success("Registration successful. Please login.")
                    else:
                        st.error(response_error_message(res, "Registration failed"))


def show_student_ui():
    st.markdown(
        '<div class="app-hero"><b>Student Workspace</b><br/>Create and track your tickets in one place.</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Student Panel")

    with st.expander("Create Ticket", expanded=True):
        title = st.text_input("Title")
        description = st.text_area("Description")
        department = st.selectbox("Department", DEPARTMENTS)
        if st.button("Create Ticket"):
            payload = {
                "title": title,
                "description": description,
                "department": department,
            }
            res = api_request("POST", "/tickets", payload, use_auth=True)
            if res.ok:
                ticket_payload = safe_json(res) or {}
                st.success(f"Ticket created with ID #{ticket_payload.get('id', '-')}")
            else:
                st.error(response_error_message(res, "Failed to create ticket"))

    st.markdown("---")
    st.subheader("My Tickets")
    res = api_request("GET", "/tickets/my", use_auth=True)
    if not res.ok:
        st.error(response_error_message(res, "Failed to fetch tickets"))
        return

    tickets = safe_json(res) or []
    if not tickets:
        st.info("No tickets yet.")
        return

    display_map = {f"#{t['id']} - {t['title']} ({t['status']})": t["id"] for t in tickets}
    selected_label = st.selectbox("Select Ticket", options=list(display_map.keys()))
    ticket_id = display_map[selected_label]

    details_res = api_request("GET", f"/tickets/{ticket_id}", use_auth=True)
    if not details_res.ok:
        st.error(response_error_message(details_res, "Failed to load ticket details"))
        return

    ticket = safe_json(details_res) or {}
    st.write(f"**Title:** {ticket['title']}")
    st.write(f"**Department:** {ticket['department']}")
    st.write(f"**Status:** {ticket['status']}")
    st.write(f"**Description:** {ticket['description']}")

    st.write("### Replies")
    if ticket["replies"]:
        for reply in ticket["replies"]:
            st.markdown(
                f"- **{reply.get('sender_name', 'Unknown')} ({reply.get('sender_role', '-')})**: {reply['message']}"
            )
    else:
        st.caption("No replies yet.")

    with st.form(f"student_reply_form_{ticket_id}", clear_on_submit=True):
        message = st.text_area("Add Reply")
        submitted = st.form_submit_button("Send Reply")
        if submitted:
            rr = api_request(
                "POST", f"/tickets/{ticket_id}/reply", {"message": message}, use_auth=True
            )
            if rr.ok:
                st.success("Reply added")
                st.rerun()
            else:
                st.error(response_error_message(rr, "Failed to add reply"))


def show_department_ui():
    st.markdown(
        '<div class="app-hero"><b>Department Workspace</b><br/>Resolve assigned tickets and update statuses quickly.</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Department Panel")
    res = api_request("GET", "/tickets/department", use_auth=True)
    if not res.ok:
        st.error(response_error_message(res, "Failed to fetch department tickets"))
        return
    tickets = safe_json(res) or []
    if not tickets:
        st.info("No assigned tickets.")
        return

    display_map = {f"#{t['id']} - {t['title']} ({t['status']})": t["id"] for t in tickets}
    selected_label = st.selectbox("Assigned Tickets", options=list(display_map.keys()))
    ticket_id = display_map[selected_label]

    details_res = api_request("GET", f"/tickets/{ticket_id}", use_auth=True)
    if not details_res.ok:
        st.error(response_error_message(details_res, "Failed to load ticket details"))
        return
    ticket = safe_json(details_res) or {}

    st.write(f"**Student ID:** {ticket['student_id']}")
    st.write(f"**Title:** {ticket['title']}")
    st.write(f"**Status:** {ticket['status']}")
    st.write(f"**Description:** {ticket['description']}")

    with st.form(f"status_form_{ticket_id}"):
        status = st.selectbox("Update Status", TICKET_STATUSES, index=TICKET_STATUSES.index(ticket["status"]))
        update_submitted = st.form_submit_button("Update")
        if update_submitted:
            ur = api_request(
                "PUT", f"/tickets/{ticket_id}/status", {"status": status}, use_auth=True
            )
            if ur.ok:
                st.success("Status updated")
                st.rerun()
            else:
                st.error(response_error_message(ur, "Failed to update status"))

    st.write("### Replies")
    if ticket["replies"]:
        for reply in ticket["replies"]:
            st.markdown(
                f"- **{reply.get('sender_name', 'Unknown')} ({reply.get('sender_role', '-')})**: {reply['message']}"
            )
    else:
        st.caption("No replies yet.")

    with st.form(f"department_reply_form_{ticket_id}", clear_on_submit=True):
        message = st.text_area("Add Reply")
        submitted = st.form_submit_button("Send Reply")
        if submitted:
            rr = api_request(
                "POST", f"/tickets/{ticket_id}/reply", {"message": message}, use_auth=True
            )
            if rr.ok:
                st.success("Reply added")
                st.rerun()
            else:
                st.error(response_error_message(rr, "Failed to add reply"))


def show_admin_ui():
    st.markdown(
        '<div class="app-hero"><b>Admin Workspace</b><br/>Monitor ticket activity across departments.</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Admin Dashboard")
    res = api_request("GET", "/admin/tickets", use_auth=True)
    if not res.ok:
        st.error(response_error_message(res, "Failed to load all tickets"))
        return
    tickets = safe_json(res) or []
    st.metric("Total Tickets", len(tickets))
    for t in tickets:
        st.markdown(
            f"- **#{t['id']}** | {t['title']} | Student: {t['student_email']} | Dept: {t['department']} | Status: {t['status']}"
        )


def show_main_app():
    st.sidebar.title("Session")
    st.sidebar.write(f"Name: {st.session_state.name}")
    st.sidebar.write(f"Email: {st.session_state.email}")
    st.sidebar.write(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.role = None
        st.session_state.name = None
        st.session_state.email = None
        st.rerun()

    role = st.session_state.role
    if role == "student":
        show_student_ui()
    elif role == "department":
        show_department_ui()
    elif role == "admin":
        show_admin_ui()
    else:
        st.error("Unknown role")


def main():
    st.set_page_config(page_title="Campus Compliance Ticketing", layout="wide")
    apply_custom_styles()
    init_state()
    if st.session_state.token:
        show_main_app()
    else:
        show_auth()


if __name__ == "__main__":
    main()
