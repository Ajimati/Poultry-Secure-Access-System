import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from .config import DB_PATH, LOG_FILE, MODEL_PATH, ensure_directories, staff_id_storage_key
from .database import DatabaseManager, DuplicateUserError
from .face_engine import FaceEngine, FaceRecognitionError
from .logging_utils import configure_logging
from .security import hash_password, verify_password


class PoultryFarmAccessApp:
    def __init__(self) -> None:
        ensure_directories()
        self.database = DatabaseManager(DB_PATH)
        self.database.initialize()
        self.logger = configure_logging(str(LOG_FILE))
        self.face_engine = FaceEngine(self.database)

        self.root = tk.Tk()
        self.root.title("Secure Access Control System for Poultry Farms")
        self.root.geometry("1240x820")
        self.root.minsize(1120, 760)
        self.root.configure(bg="#edf3f0")

        self.style = ttk.Style()
        self._configure_styles()

        self.register_name_var = tk.StringVar()
        self.register_staff_id_var = tk.StringVar()
        self.register_role_var = tk.StringVar(value="Farm Staff")
        self.register_password_var = tk.StringVar()
        self.capture_staff_id_var = tk.StringVar()
        self.verification_staff_id_var = tk.StringVar()
        self.verification_password_var = tk.StringVar()

        self.status_var = tk.StringVar(value="System ready.")
        self.verification_state_var = tk.StringVar(value="Awaiting full verification.")
        self.verification_result_var = tk.StringVar(
            value=(
                "This checkpoint uses two factors in one access flow:\n"
                "1. Password validation\n"
                "2. Live face recognition with anti-spoofing"
            )
        )

        self.users_metric_var = tk.StringVar(value="0")
        self.enrolled_metric_var = tk.StringVar(value="0")
        self.logs_metric_var = tk.StringVar(value="0")
        self.model_metric_var = tk.StringVar(value="Not Trained")

        self._build_ui()
        self.refresh_all()

    def _configure_styles(self) -> None:
        self.style.theme_use("clam")
        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("App.TFrame", background="#edf3f0")
        self.style.configure("Surface.TFrame", background="#ffffff")
        self.style.configure(
            "Card.TLabelframe",
            background="#ffffff",
            borderwidth=1,
            relief="solid",
            bordercolor="#d4e0da",
        )
        self.style.configure(
            "Card.TLabelframe.Label",
            background="#ffffff",
            foreground="#173127",
            font=("Segoe UI", 10, "bold"),
        )
        self.style.configure("CardText.TLabel", background="#ffffff", foreground="#4d645b")
        self.style.configure(
            "SectionTitle.TLabel",
            background="#ffffff",
            foreground="#173127",
            font=("Segoe UI", 13, "bold"),
        )
        self.style.configure(
            "MetricValue.TLabel",
            background="#102a1f",
            foreground="#ffffff",
            font=("Segoe UI", 16, "bold"),
        )
        self.style.configure(
            "MetricLabel.TLabel",
            background="#102a1f",
            foreground="#b7d5c5",
            font=("Segoe UI", 9),
        )
        self.style.configure("TNotebook", background="#edf3f0", borderwidth=0)
        self.style.configure(
            "TNotebook.Tab",
            background="#dce8e2",
            foreground="#355247",
            padding=(18, 10),
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#173127")],
        )
        self.style.configure(
            "Accent.TButton",
            background="#2f855a",
            foreground="#ffffff",
            padding=(14, 10),
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map("Accent.TButton", background=[("active", "#276749")])
        self.style.configure(
            "Secondary.TButton",
            background="#eef4f1",
            foreground="#1f3a30",
            padding=(12, 10),
            borderwidth=1,
            font=("Segoe UI", 10, "bold"),
        )
        self.style.map("Secondary.TButton", background=[("active", "#e2ebe6")])
        self.style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#1b2f28",
            rowheight=30,
            bordercolor="#d4e0da",
        )
        self.style.configure(
            "Treeview.Heading",
            background="#eaf2ee",
            foreground="#173127",
            font=("Segoe UI", 10, "bold"),
        )

    def _build_ui(self) -> None:
        self._build_header()

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        enrollment_tab = ttk.Frame(notebook, padding=16, style="App.TFrame")
        verification_tab = ttk.Frame(notebook, padding=16, style="App.TFrame")
        logs_tab = ttk.Frame(notebook, padding=16, style="App.TFrame")

        notebook.add(enrollment_tab, text="Enrollment")
        notebook.add(verification_tab, text="Unified Verification")
        notebook.add(logs_tab, text="Audit Logs")

        self._build_enrollment_tab(enrollment_tab)
        self._build_verification_tab(verification_tab)
        self._build_logs_tab(logs_tab)

        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#dfeae4",
            fg="#20352c",
            anchor="w",
            padx=14,
            pady=8,
            font=("Segoe UI", 10),
        )
        status_bar.pack(fill="x", side="bottom")

    def _build_header(self) -> None:
        header = tk.Frame(self.root, bg="#102a1f", padx=24, pady=20)
        header.pack(fill="x", padx=18, pady=(18, 12))

        tk.Label(
            header,
            text="Secure Access Control for Poultry Farms",
            bg="#102a1f",
            fg="#ffffff",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="LBPH face biometrics, anti-spoofing, and password verification in one access workflow.",
            bg="#102a1f",
            fg="#b9d7c7",
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", pady=(6, 18))

        metrics = tk.Frame(header, bg="#102a1f")
        metrics.grid(row=2, column=0, sticky="ew")
        for column in range(4):
            metrics.columnconfigure(column, weight=1)

        self._create_metric_card(metrics, 0, "Registered Users", self.users_metric_var)
        self._create_metric_card(metrics, 1, "Face Enrolled", self.enrolled_metric_var)
        self._create_metric_card(metrics, 2, "Audit Events", self.logs_metric_var)
        self._create_metric_card(metrics, 3, "Model Status", self.model_metric_var)

        header.columnconfigure(0, weight=1)

    def _create_metric_card(
        self,
        parent: tk.Frame,
        column: int,
        label_text: str,
        value_var: tk.StringVar,
    ) -> None:
        card = tk.Frame(parent, bg="#173629", bd=0, padx=16, pady=12)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
        tk.Label(
            card,
            text=label_text,
            bg="#173629",
            fg="#b7d5c5",
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        tk.Label(
            card,
            textvariable=value_var,
            bg="#173629",
            fg="#ffffff",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(4, 0))

    def _build_enrollment_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=2)
        parent.columnconfigure(1, weight=3)
        parent.rowconfigure(1, weight=1)

        registration = ttk.LabelFrame(
            parent,
            text="Register Authorized Staff",
            style="Card.TLabelframe",
            padding=16,
        )
        registration.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        registration.columnconfigure(1, weight=1)

        ttk.Label(registration, text="Full Name").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(registration, textvariable=self.register_name_var).grid(
            row=0, column=1, sticky="ew", pady=8
        )
        ttk.Label(registration, text="Staff ID").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(registration, textvariable=self.register_staff_id_var).grid(
            row=1, column=1, sticky="ew", pady=8
        )
        ttk.Label(registration, text="Role").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Combobox(
            registration,
            textvariable=self.register_role_var,
            values=(
                "Farm Staff",
                "Security Officer",
                "Supervisor",
                "Veterinarian",
                "Administrator",
            ),
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=8)
        ttk.Label(registration, text="Password").grid(row=3, column=0, sticky="w", pady=8)
        ttk.Entry(registration, textvariable=self.register_password_var, show="*").grid(
            row=3, column=1, sticky="ew", pady=8
        )
        ttk.Button(
            registration,
            text="Register User",
            style="Accent.TButton",
            command=self.register_user,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        ttk.Label(
            registration,
            text=(
                "Duplicate staff IDs and duplicate full names are blocked before a record is saved."
            ),
            style="CardText.TLabel",
            wraplength=300,
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        biometric = ttk.LabelFrame(
            parent,
            text="Biometric Enrollment",
            style="Card.TLabelframe",
            padding=16,
        )
        biometric.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        biometric.columnconfigure(1, weight=1)

        ttk.Label(biometric, text="Staff ID for capture").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(biometric, textvariable=self.capture_staff_id_var).grid(
            row=0, column=1, sticky="ew", pady=8
        )
        ttk.Button(
            biometric,
            text="Capture Face Dataset",
            style="Accent.TButton",
            command=self.capture_dataset,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 8))
        ttk.Button(
            biometric,
            text="Train LBPH Model",
            style="Secondary.TButton",
            command=self.train_model,
        ).grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            biometric,
            text=(
                "Captured images are saved into a sanitized folder under datasets/ using the staff ID."
            ),
            style="CardText.TLabel",
            wraplength=300,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))

        roster = ttk.LabelFrame(
            parent,
            text="Registered Staff Directory",
            style="Card.TLabelframe",
            padding=16,
        )
        roster.grid(row=0, column=1, rowspan=2, sticky="nsew")
        roster.rowconfigure(1, weight=1)
        roster.columnconfigure(0, weight=1)

        roster_top = ttk.Frame(roster, style="Surface.TFrame")
        roster_top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        roster_top.columnconfigure(0, weight=1)
        ttk.Label(roster_top, text="Current enrolled operators", style="SectionTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            roster_top,
            text="Refresh",
            style="Secondary.TButton",
            command=self.refresh_all,
        ).grid(row=0, column=1, sticky="e")

        columns = ("staff_id", "full_name", "role", "face_samples")
        self.users_tree = ttk.Treeview(roster, columns=columns, show="headings", height=18)
        headings = {
            "staff_id": "Staff ID",
            "full_name": "Full Name",
            "role": "Role",
            "face_samples": "Face Samples",
        }
        widths = {
            "staff_id": 120,
            "full_name": 240,
            "role": 150,
            "face_samples": 100,
        }
        for column in columns:
            self.users_tree.heading(column, text=headings[column])
            self.users_tree.column(column, width=widths[column], anchor="w")
        self.users_tree.grid(row=1, column=0, sticky="nsew")

    def _build_verification_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=2)

        verification = ttk.LabelFrame(
            parent,
            text="Unified Access Verification",
            style="Card.TLabelframe",
            padding=16,
        )
        verification.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        verification.columnconfigure(1, weight=1)

        ttk.Label(
            verification,
            text="Both password and live face recognition must succeed for access to be granted.",
            style="CardText.TLabel",
            wraplength=560,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(verification, text="Staff ID").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Entry(verification, textvariable=self.verification_staff_id_var).grid(
            row=1, column=1, sticky="ew", pady=8
        )
        ttk.Label(verification, text="Password").grid(row=2, column=0, sticky="w", pady=8)
        ttk.Entry(verification, textvariable=self.verification_password_var, show="*").grid(
            row=2, column=1, sticky="ew", pady=8
        )
        ttk.Button(
            verification,
            text="Run Full Verification",
            style="Accent.TButton",
            command=self.run_combined_access,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 14))

        result_card = tk.Frame(verification, bg="#f5fbf7", bd=1, relief="solid", padx=16, pady=14)
        result_card.grid(row=4, column=0, columnspan=2, sticky="nsew")
        verification.rowconfigure(4, weight=1)
        tk.Label(
            result_card,
            textvariable=self.verification_state_var,
            bg="#f5fbf7",
            fg="#173127",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            result_card,
            textvariable=self.verification_result_var,
            bg="#f5fbf7",
            fg="#355247",
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=560,
            pady=8,
        ).pack(fill="x")

        guide = ttk.LabelFrame(
            parent,
            text="Verification Guide",
            style="Card.TLabelframe",
            padding=16,
        )
        guide.grid(row=0, column=1, sticky="nsew")

        ttk.Label(
            guide,
            text=(
                "Verification flow\n\n"
                "1. Enter the staff ID and password.\n"
                "2. The system validates the password.\n"
                "3. A live blink is required for anti-spoofing.\n"
                "4. The recognized face must match the same registered staff member.\n"
                "5. Access is granted only when both factors agree."
            ),
            style="CardText.TLabel",
            wraplength=320,
            justify="left",
        ).pack(anchor="w")

        ttk.Separator(guide).pack(fill="x", pady=14)

        ttk.Label(
            guide,
            text="Operational notes",
            style="SectionTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            guide,
            text=(
                "The result pane shows the recognized user, final decision, and LBPH confidence score.\n"
                "If the password is correct but the face belongs to another person, access is denied."
            ),
            style="CardText.TLabel",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _build_logs_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        controls = ttk.Frame(parent, style="App.TFrame")
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.columnconfigure(0, weight=1)
        ttk.Label(
            controls,
            text="Unified access event history",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            controls,
            text="Refresh Logs",
            style="Secondary.TButton",
            command=self.refresh_all,
        ).grid(row=0, column=1, sticky="e")

        columns = ("time", "name", "staff_id", "method", "status", "confidence", "message")
        self.log_tree = ttk.Treeview(parent, columns=columns, show="headings", height=22)
        headings = {
            "time": "Timestamp",
            "name": "Name",
            "staff_id": "Staff ID",
            "method": "Method",
            "status": "Status",
            "confidence": "Confidence",
            "message": "Message",
        }
        widths = {
            "time": 150,
            "name": 180,
            "staff_id": 120,
            "method": 130,
            "status": 90,
            "confidence": 90,
            "message": 430,
        }
        for column in columns:
            self.log_tree.heading(column, text=headings[column])
            self.log_tree.column(column, width=widths[column], anchor="w")
        self.log_tree.grid(row=1, column=0, sticky="nsew")

    def register_user(self) -> None:
        full_name = " ".join(self.register_name_var.get().split())
        staff_id = self.register_staff_id_var.get().strip().upper()
        role = self.register_role_var.get().strip() or "Farm Staff"
        password = self.register_password_var.get()

        if not full_name or not staff_id or not password:
            messagebox.showwarning("Missing Data", "Full name, staff ID, and password are required.")
            return
        if len(password) < 6:
            messagebox.showwarning("Weak Password", "Use a password with at least 6 characters.")
            return

        try:
            password_hash, password_salt = hash_password(password)
            self.database.create_user(staff_id, full_name, role, password_hash, password_salt)
        except DuplicateUserError as error:
            messagebox.showerror("Duplicate User", str(error))
            self.status_var.set(str(error))
            return
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate User", "That staff ID already exists.")
            self.status_var.set("Registration blocked because the staff ID already exists.")
            return

        self.logger.info("Registered new user %s (%s).", full_name, staff_id)
        self.status_var.set(f"Registered {full_name} with staff ID {staff_id}.")
        self.capture_staff_id_var.set(staff_id)
        self.verification_staff_id_var.set(staff_id)
        self.register_name_var.set("")
        self.register_staff_id_var.set("")
        self.register_password_var.set("")
        self.refresh_all()
        messagebox.showinfo("User Registered", f"{full_name} is ready for face capture.")

    def capture_dataset(self) -> None:
        staff_id = self.capture_staff_id_var.get().strip().upper()
        if not staff_id:
            messagebox.showwarning("Missing Staff ID", "Enter a staff ID before capturing faces.")
            return

        user = self.database.get_user_by_staff_id(staff_id)
        if not user:
            messagebox.showerror("User Not Found", "Register the user before face capture.")
            return

        self.status_var.set(f"Capturing dataset for {user['full_name']}...")
        try:
            result = self.face_engine.capture_dataset(user)
        except FaceRecognitionError as error:
            messagebox.showerror("Capture Failed", str(error))
            self.status_var.set(str(error))
            return

        self.logger.info(
            "Captured %s face samples for %s (%s).",
            result["captured"],
            user["full_name"],
            user["staff_id"],
        )
        self.status_var.set(
            f"Captured {result['captured']} face samples for {user['full_name']}."
        )
        self.refresh_all()
        messagebox.showinfo(
            "Dataset Capture Complete",
            f"Saved {result['captured']} images for {user['full_name']}.\n"
            f"Folder: datasets/{staff_id_storage_key(user['staff_id'])}",
        )

    def train_model(self) -> None:
        self.status_var.set("Training LBPH face recognizer...")
        try:
            result = self.face_engine.train_model()
        except FaceRecognitionError as error:
            messagebox.showerror("Training Failed", str(error))
            self.status_var.set(str(error))
            return

        self.logger.info(
            "Trained LBPH model with %s images across %s users.",
            result["images_used"],
            result["users_trained"],
        )
        self.status_var.set("LBPH model trained successfully.")
        self.refresh_all()
        messagebox.showinfo(
            "Training Complete",
            f"Model trained with {result['images_used']} images across "
            f"{result['users_trained']} users.",
        )

    def run_combined_access(self) -> None:
        staff_id = self.verification_staff_id_var.get().strip().upper()
        password = self.verification_password_var.get()

        if not staff_id or not password:
            messagebox.showwarning("Missing Credentials", "Enter both staff ID and password.")
            return

        claimed_user = self.database.get_user_by_staff_id(staff_id)
        if not claimed_user or not verify_password(
            password,
            claimed_user["password_hash"] if claimed_user else "",
            claimed_user["password_salt"] if claimed_user else "",
        ):
            self.database.log_access(
                user_id=claimed_user["id"] if claimed_user else None,
                access_point="Unified Verification Gate",
                method="FACE+PASSWORD",
                status="DENIED",
                confidence=None,
                spoof_detected=False,
                message="Password verification failed before face recognition.",
            )
            self.verification_state_var.set("Access Denied")
            self.verification_result_var.set(
                "Claimed user: Unknown\n"
                "Password check: Failed\n"
                "Face verification: Not started\n"
                "Final decision: Access denied"
            )
            self.status_var.set("Access denied because the password check failed.")
            self.verification_password_var.set("")
            self.logger.warning("Unified verification denied for staff ID %s.", staff_id)
            self.refresh_all()
            return

        self.status_var.set(
            f"Password verified for {claimed_user['full_name']}. Waiting for live face scan..."
        )

        try:
            face_result = self.face_engine.recognize_with_liveness(
                access_point="Unified Verification Gate",
                persist_log=False,
            )
        except FaceRecognitionError as error:
            messagebox.showerror("Face Verification Failed", str(error))
            self.status_var.set(str(error))
            return

        confidence = face_result.get("confidence")
        spoof_detected = bool(face_result.get("spoof_detected"))

        if face_result["status"] != "GRANTED":
            self.database.log_access(
                user_id=claimed_user["id"],
                access_point="Unified Verification Gate",
                method="FACE+PASSWORD",
                status="DENIED",
                confidence=confidence,
                spoof_detected=spoof_detected,
                message=face_result["message"],
            )
            self.verification_state_var.set("Access Denied")
            self.verification_result_var.set(
                f"Claimed user: {claimed_user['full_name']}\n"
                "Password check: Passed\n"
                f"Recognized user: {face_result['name']}\n"
                f"Confidence: {confidence if confidence is not None else 'N/A'}\n"
                f"Final decision: Access denied\n"
                f"Reason: {face_result['message']}"
            )
            self.status_var.set("Access denied during face verification.")
            self.verification_password_var.set("")
            self.logger.warning(
                "Unified verification denied for %s due to face stage failure.",
                claimed_user["staff_id"],
            )
            self.refresh_all()
            return

        if face_result.get("user_id") != claimed_user["id"]:
            recognized_name = face_result.get("name") or "Unknown"
            message = (
                f"Credential mismatch. Password belongs to {claimed_user['full_name']} "
                f"but face recognition matched {recognized_name}."
            )
            self.database.log_access(
                user_id=claimed_user["id"],
                access_point="Unified Verification Gate",
                method="FACE+PASSWORD",
                status="DENIED",
                confidence=confidence,
                spoof_detected=spoof_detected,
                message=message,
            )
            self.verification_state_var.set("Access Denied")
            self.verification_result_var.set(
                f"Claimed user: {claimed_user['full_name']}\n"
                "Password check: Passed\n"
                f"Recognized user: {recognized_name}\n"
                f"Confidence: {confidence if confidence is not None else 'N/A'}\n"
                "Final decision: Access denied\n"
                "Reason: Face and password belong to different users"
            )
            self.status_var.set("Access denied because the face did not match the password owner.")
            self.verification_password_var.set("")
            self.logger.warning(
                "Unified verification mismatch for %s; face matched %s.",
                claimed_user["staff_id"],
                recognized_name,
            )
            self.refresh_all()
            return

        message = f"Access granted to {claimed_user['full_name']} after full verification."
        self.database.log_access(
            user_id=claimed_user["id"],
            access_point="Unified Verification Gate",
            method="FACE+PASSWORD",
            status="GRANTED",
            confidence=confidence,
            spoof_detected=False,
            message=message,
        )
        self.verification_state_var.set("Access Granted")
        self.verification_result_var.set(
            f"Allowed user: {claimed_user['full_name']}\n"
            f"Staff ID: {claimed_user['staff_id']}\n"
            "Password check: Passed\n"
            f"Recognized user: {face_result['name']}\n"
            f"LBPH confidence: {confidence if confidence is not None else 'N/A'}\n"
            "Final decision: Access granted"
        )
        self.status_var.set(message)
        self.verification_password_var.set("")
        self.logger.info(
            "Unified verification granted for %s (%s) with confidence %s.",
            claimed_user["full_name"],
            claimed_user["staff_id"],
            confidence,
        )
        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_dashboard()
        self.refresh_registered_users()
        self.refresh_logs()

    def refresh_dashboard(self) -> None:
        self.users_metric_var.set(str(self.database.count_users()))
        self.enrolled_metric_var.set(str(self.database.count_enrolled_users()))
        self.logs_metric_var.set(str(self.database.count_logs()))
        self.model_metric_var.set("Ready" if MODEL_PATH.exists() else "Not Trained")

    def refresh_registered_users(self) -> None:
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        for user in self.database.list_users():
            self.users_tree.insert(
                "",
                "end",
                values=(
                    user["staff_id"],
                    user["full_name"],
                    user["role"],
                    user["face_samples"],
                ),
            )

    def refresh_logs(self) -> None:
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        for log_row in self.database.get_recent_logs():
            confidence = "" if log_row["confidence"] is None else f"{log_row['confidence']:.2f}"
            self.log_tree.insert(
                "",
                "end",
                values=(
                    log_row["created_at"],
                    log_row["full_name"] or "Unknown",
                    log_row["staff_id"] or "-",
                    log_row["method"],
                    log_row["status"],
                    confidence,
                    log_row["message"],
                ),
            )

    def run(self) -> None:
        self.root.mainloop()
