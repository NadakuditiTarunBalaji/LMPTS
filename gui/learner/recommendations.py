"""
recommendations.py
------------------
Course recommendations screen for learners.
"""

import tkinter as tk
from tkinter import ttk
from core.user import User
from gui.dialogs.confirm_dialog import show_error, show_info


CONTENT_BG = "#f0f4f8"
CARD_BG    = "#ffffff"


class RecommendationsScreen(tk.Frame):
    """
    Shows personalized course recommendations.
    """

    def __init__(self, parent, user: User, services: dict):
        super().__init__(parent, bg=CONTENT_BG)
        self._user       = user
        self._services   = services
        self._learner_id = None
        self._build()
        self._find_learner()
        self._load_recommendations()

    def _build(self):
        title_frame = tk.Frame(self, bg=CONTENT_BG, pady=15)
        title_frame.pack(fill="x", padx=20)
        tk.Label(
            title_frame, text="Course Recommendations",
            font=("Segoe UI", 16, "bold"),
            bg=CONTENT_BG, fg="#1a3a5c",
        ).pack(side="left")

        # Filter row
        filter_frame = tk.Frame(self, bg=CONTENT_BG)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(
            filter_frame, text="Difficulty preference:",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, fg="#666666",
        ).pack(side="left")

        self._diff_var = tk.StringVar(value="BEGINNER")
        for level in ("BEGINNER", "INTERMEDIATE", "ADVANCED"):
            ttk.Radiobutton(
                filter_frame, text=level,
                variable=self._diff_var, value=level,
                command=self._load_recommendations,
            ).pack(side="left", padx=5)

        tk.Button(
            filter_frame, text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg=CONTENT_BG, relief="flat", cursor="hand2",
            command=self._load_recommendations,
        ).pack(side="right")

        # Recommendations list (scrollable cards)
        self._container = tk.Frame(self, bg=CONTENT_BG)
        self._container.pack(
            fill="both", expand=True, padx=20, pady=10
        )

        canvas = tk.Canvas(
            self._container, bg=CONTENT_BG, highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            self._container, orient="vertical", command=canvas.yview
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._cards_frame = tk.Frame(canvas, bg=CONTENT_BG)
        self._canvas_win  = canvas.create_window(
            (0, 0), window=self._cards_frame, anchor="nw"
        )

        self._cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                self._canvas_win, width=e.width
            )
        )

    def _find_learner(self):
        """Find the learner profile for current user."""
        try:
            learner_repo = self._services.get("learner_repo")
            if learner_repo:
                learner = learner_repo.get_learner_by_user_id(
                    self._user.id
                )
                if learner:
                    self._learner_id = learner.id
        except Exception:
            pass

    def _load_recommendations(self):
        """Load and display recommendations."""
        for widget in self._cards_frame.winfo_children():
            widget.destroy()

        if self._learner_id is None:
            tk.Label(
                self._cards_frame,
                text="Learner profile not found.",
                font=("Segoe UI", 10),
                bg=CONTENT_BG,
                fg="#666666",
            ).pack(pady=20)
            return

        try:
            rec_svc = self._services.get("recommendation_service")
            if rec_svc is None:
                return

            recs = rec_svc.get_recommendations(
                learner_id            = self._learner_id,
                difficulty_preference = self._diff_var.get(),
                limit                 = 8,
            )

            if not recs:
                tk.Label(
                    self._cards_frame,
                    text=(
                        "No recommendations available.\n"
                        "You may have completed all available courses!"
                    ),
                    font=("Segoe UI", 11),
                    bg=CONTENT_BG,
                    fg="#666666",
                    justify="center",
                ).pack(pady=40)
                return

            for rec in recs:
                self._add_recommendation_card(rec)

        except Exception as e:
            show_error(self, "Error", str(e))

    def _add_recommendation_card(self, rec: dict):
        """Add a single recommendation card."""
        card = tk.Frame(
            self._cards_frame,
            bg=CARD_BG,
            padx=20, pady=12,
            relief="flat", bd=1,
        )
        card.pack(fill="x", pady=4)

        # Header row
        header = tk.Frame(card, bg=CARD_BG)
        header.pack(fill="x")

        tk.Label(
            header,
            text=rec["course_code"],
            font=("Segoe UI", 12, "bold"),
            bg=CARD_BG,
            fg="#1a3a5c",
        ).pack(side="left")

        score_colour = (
            "#27ae60" if rec["score"] >= 70
            else "#e67e22" if rec["score"] >= 40
            else "#c0392b"
        )
        tk.Label(
            header,
            text=f"Score: {rec['score']:.1f}",
            font=("Segoe UI", 9, "bold"),
            bg=CARD_BG,
            fg=score_colour,
        ).pack(side="right")

        # Course name
        tk.Label(
            card,
            text=rec["course_name"],
            font=("Segoe UI", 10),
            bg=CARD_BG,
            fg="#333333",
        ).pack(anchor="w")

        # Reasons
        reasons_text = "  •  ".join(rec.get("reasons", []))
        if reasons_text:
            tk.Label(
                card,
                text=reasons_text,
                font=("Segoe UI", 8),
                bg=CARD_BG,
                fg="#888888",
                wraplength=600,
                justify="left",
            ).pack(anchor="w", pady=(3, 0))

        # Enroll button
        enroll_btn = tk.Button(
            card,
            text="➕ Enroll Now",
            font=("Segoe UI", 8),
            bg="#1a3a5c",
            fg="#ffffff",
            relief="flat",
            cursor="hand2",
            padx=8, pady=3,
            command=lambda code=rec["course_code"]: self._enroll(code),
        )
        enroll_btn.pack(anchor="e", pady=(5, 0))

    def _enroll(self, course_code: str):
        """Enroll in the recommended course."""
        if self._learner_id is None:
            show_error(self, "Error", "Learner profile not found.")
            return
        try:
            enrollment_svc = self._services.get("enrollment_service")
            if enrollment_svc is None:
                return
            result = enrollment_svc.enroll_learner(
                self._learner_id, course_code
            )
            if result.success:
                show_info(self, "Enrolled", result.message)
                self._load_recommendations()
            else:
                show_error(self, "Failed", result.message)
        except Exception as e:
            show_error(self, "Error", str(e))