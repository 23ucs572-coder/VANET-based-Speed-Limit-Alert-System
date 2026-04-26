from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from run_simulation import SimulationConfig, default_config, run_simulation


PRESETS = {
    "Balanced Demo": SimulationConfig(
        use_gui=True,
        step_delay_ms=650,
        vehicle_count=12,
        depart_gap_s=5,
        e0_limit_kmph=60,
        e1_limit_kmph=30,
        e2_limit_kmph=50,
        cautious_share=25,
        aggressive_share=35,
        rsu_range_m=140,
        v2v_range_m=120,
    ),
    "School Zone Stress": SimulationConfig(
        use_gui=True,
        step_delay_ms=700,
        vehicle_count=18,
        depart_gap_s=4,
        e0_limit_kmph=70,
        e1_limit_kmph=25,
        e2_limit_kmph=45,
        cautious_share=15,
        aggressive_share=50,
        rsu_range_m=170,
        v2v_range_m=140,
    ),
    "Calm Traffic": SimulationConfig(
        use_gui=True,
        step_delay_ms=550,
        vehicle_count=8,
        depart_gap_s=6,
        e0_limit_kmph=50,
        e1_limit_kmph=30,
        e2_limit_kmph=40,
        cautious_share=45,
        aggressive_share=15,
        rsu_range_m=130,
        v2v_range_m=100,
    ),
}


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("VANET Speed Limit Alert System")
        self.root.geometry("1080x760")
        self.root.configure(bg="#f6efe6")
        self.root.minsize(860, 640)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Shell.TFrame", background="#f6efe6")
        self.style.configure("Topbar.TFrame", background="#1f3c88")
        self.style.configure("Card.TFrame", background="#fffaf4", relief="flat")
        self.style.configure("Header.TLabel", background="#f6efe6", foreground="#1f2a44", font=("Bahnschrift SemiBold", 26))
        self.style.configure("Sub.TLabel", background="#f6efe6", foreground="#6a7280", font=("Segoe UI", 11))
        self.style.configure("CardTitle.TLabel", background="#fffaf4", foreground="#1f2a44", font=("Bahnschrift SemiBold", 14))
        self.style.configure("Body.TLabel", background="#fffaf4", foreground="#334155", font=("Segoe UI", 10))
        self.style.configure("TopTitle.TLabel", background="#1f3c88", foreground="#fff8f0", font=("Bahnschrift SemiBold", 14))
        self.style.configure("TopBody.TLabel", background="#1f3c88", foreground="#dbe7ff", font=("Segoe UI", 10))
        self.style.configure("Accent.TLabel", background="#fffaf4", foreground="#d97706", font=("Segoe UI Semibold", 9))
        self.style.configure(
            "Launch.TButton",
            font=("Segoe UI Semibold", 11),
            padding=11,
            background="#ef6c57",
            foreground="#fff8f0",
            borderwidth=1,
            focusthickness=0,
            relief="flat",
        )
        self.style.map(
            "Launch.TButton",
            background=[("active", "#ff8a6b"), ("pressed", "#d95a47")],
            foreground=[("active", "#fff8f0"), ("pressed", "#fff8f0")],
        )
        self.style.configure(
            "Preset.TButton",
            font=("Segoe UI Semibold", 10),
            padding=9,
            background="#ffe3c2",
            foreground="#1f2a44",
            borderwidth=1,
            relief="flat",
            focusthickness=1,
            focuscolor="#ef6c57",
        )
        self.style.map(
            "Preset.TButton",
            background=[("active", "#ffd19e"), ("pressed", "#ffbe76")],
            foreground=[("active", "#1f2a44"), ("pressed", "#1f2a44")],
            bordercolor=[("active", "#ef6c57"), ("pressed", "#d95a47")],
        )
        self.style.configure(
            "TSpinbox",
            arrowsize=16,
            padding=6,
            fieldbackground="#ffffff",
            foreground="#1f2a44",
            bordercolor="#d59a5b",
            lightcolor="#d59a5b",
            darkcolor="#d59a5b",
            arrowcolor="#1f2a44",
        )
        self.style.configure(
            "Horizontal.TScale",
            background="#fffaf4",
            troughcolor="#ffd9b5",
            bordercolor="#fffaf4",
            lightcolor="#ef6c57",
            darkcolor="#ef6c57",
        )

        self.vars = {
            "vehicle_count": tk.IntVar(value=default_config().vehicle_count),
            "depart_gap_s": tk.IntVar(value=default_config().depart_gap_s),
            "step_delay_ms": tk.IntVar(value=default_config().step_delay_ms),
            "e0_limit_kmph": tk.IntVar(value=default_config().e0_limit_kmph),
            "e1_limit_kmph": tk.IntVar(value=default_config().e1_limit_kmph),
            "e2_limit_kmph": tk.IntVar(value=default_config().e2_limit_kmph),
            "cautious_share": tk.IntVar(value=default_config().cautious_share),
            "aggressive_share": tk.IntVar(value=default_config().aggressive_share),
            "rsu_range_m": tk.IntVar(value=default_config().rsu_range_m),
            "v2v_range_m": tk.IntVar(value=default_config().v2v_range_m),
            "minimum_follow_distance_m": tk.IntVar(value=default_config().minimum_follow_distance_m),
            "seed": tk.IntVar(value=default_config().seed),
        }
        self.summary_var = tk.StringVar()
        for variable in self.vars.values():
            variable.trace_add("write", self._refresh_summary)

        self._build_ui()
        self._refresh_summary()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="Shell.TFrame")
        outer.pack(fill="both", expand=True)

        top_bar = ttk.Frame(outer, padding=(20, 14), style="Topbar.TFrame")
        top_bar.pack(fill="x")
        left_top = ttk.Frame(top_bar, style="Topbar.TFrame")
        left_top.pack(side="left", fill="x", expand=True)
        ttk.Label(left_top, text="Ready When You Are", style="TopTitle.TLabel").pack(anchor="w")
        ttk.Label(
            left_top,
            text="Shape the scenario, then launch SUMO with live VANET alerts and safety behavior.",
            style="TopBody.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Button(
            top_bar,
            text="Launch SUMO Simulation",
            style="Launch.TButton",
            command=self._launch,
        ).pack(side="right", padx=(14, 0))

        canvas = tk.Canvas(outer, bg="#f6efe6", highlightthickness=0)
        v_scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        shell = ttk.Frame(canvas, padding=24, style="Shell.TFrame")
        shell_window = canvas.create_window((0, 0), window=shell, anchor="nw")

        def _on_frame_configure(_event: object) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(shell_window, width=max(event.width, 920))

        shell.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event: tk.Event) -> None:
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")

        def _bind_mousewheel(widget: tk.Widget) -> None:
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_mousewheel(child)

        self.root.after(100, lambda: _bind_mousewheel(shell))

        header = ttk.Frame(shell, style="Shell.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="VANET Speed Limit Alert Simulator", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Build a road-safety scenario, shape the traffic mood, then launch a live VANET simulation.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(6, 14))

        preset_bar = ttk.Frame(shell, style="Card.TFrame")
        preset_bar.pack(fill="x", pady=(0, 12))
        ttk.Label(preset_bar, text="Quick presets", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(
            preset_bar,
            text="Use these starting moods, then fine-tune the sliders below.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        button_row = ttk.Frame(preset_bar, style="Card.TFrame")
        button_row.pack(anchor="w")
        for preset_name in PRESETS:
            ttk.Button(
                button_row,
                text=preset_name,
                style="Preset.TButton",
                command=lambda name=preset_name: self._apply_preset(name),
            ).pack(side="left", padx=(0, 8))

        content = ttk.Frame(shell, style="Card.TFrame")
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)

        self._build_card(
            content,
            0,
            0,
            "Traffic setup",
            [
                ("Vehicle count", "vehicle_count", 4, 40),
                ("Departure gap (s)", "depart_gap_s", 1, 12),
                ("Animation delay (ms)", "step_delay_ms", 0, 1500),
                ("Random seed", "seed", 1, 999),
            ],
        )
        self._build_card(
            content,
            0,
            1,
            "Road speed limits",
            [
                ("Edge e0 limit", "e0_limit_kmph", 20, 100),
                ("Edge e1 limit", "e1_limit_kmph", 10, 80),
                ("Edge e2 limit", "e2_limit_kmph", 20, 100),
            ],
        )
        self._build_card(
            content,
            1,
            0,
            "Driver mix",
            [
                ("Cautious drivers %", "cautious_share", 0, 80),
                ("Aggressive drivers %", "aggressive_share", 0, 80),
            ],
        )
        self._build_card(
            content,
            1,
            1,
            "Communication ranges",
            [
                ("RSU range (m)", "rsu_range_m", 40, 250),
                ("V2V range (m)", "v2v_range_m", 40, 250),
                ("Minimum follow distance (m)", "minimum_follow_distance_m", 5, 50),
            ],
        )

        summary_card = ttk.Frame(shell, padding=16, style="Card.TFrame")
        summary_card.pack(fill="x", pady=(14, 0))
        ttk.Label(summary_card, text="Simulation summary", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(summary_card, textvariable=self.summary_var, style="Body.TLabel", justify="left").pack(anchor="w", pady=(8, 10))
        ttk.Label(
            summary_card,
            text="Tip: orange/red traffic with a short departure gap makes the safety alerts easiest to observe.",
            style="Accent.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        ttk.Label(
            summary_card,
            text="The SUMO GUI will open with your chosen settings and live overlays.",
            style="Body.TLabel",
        ).pack(anchor="w")

    def _build_card(
        self,
        parent: ttk.Frame,
        row: int,
        column: int,
        title: str,
        items: list[tuple[str, str, int, int]],
    ) -> None:
        card = ttk.Frame(parent, padding=18, style="Card.TFrame")
        card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
        ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        divider = tk.Frame(card, bg="#ef6c57", height=3)
        divider.pack(fill="x", pady=(0, 12))

        for label_text, key, start, end in items:
            row_frame = ttk.Frame(card, style="Card.TFrame")
            row_frame.pack(fill="x", pady=8)
            ttk.Label(row_frame, text=label_text, style="Body.TLabel").pack(anchor="w")
            current_value = ttk.Label(
                row_frame,
                textvariable=self.vars[key],
                style="Accent.TLabel",
            )
            current_value.pack(anchor="e")
            scale = ttk.Scale(
                row_frame,
                from_=start,
                to=end,
                orient="horizontal",
                command=lambda value, name=key: self.vars[name].set(int(float(value))),
            )
            scale.pack(fill="x", pady=(8, 0))
            scale.set(self.vars[key].get())

            editor = ttk.Frame(row_frame, style="Card.TFrame")
            editor.pack(fill="x", pady=(8, 0))
            ttk.Spinbox(
                editor,
                from_=start,
                to=end,
                textvariable=self.vars[key],
                width=8,
                justify="center",
            ).pack(side="left")
            ttk.Label(
                editor,
                text=f"Range {start} to {end}",
                style="Accent.TLabel",
            ).pack(side="left", padx=(10, 0))

    def _apply_preset(self, preset_name: str) -> None:
        config = PRESETS[preset_name]
        for field_name, variable in self.vars.items():
            variable.set(getattr(config, field_name))

    def _collect_config(self) -> SimulationConfig:
        cautious_share = max(0, min(self.vars["cautious_share"].get(), 100))
        aggressive_share = max(0, min(self.vars["aggressive_share"].get(), 100 - cautious_share))
        return SimulationConfig(
            use_gui=True,
            step_delay_ms=max(0, self.vars["step_delay_ms"].get()),
            vehicle_count=max(1, self.vars["vehicle_count"].get()),
            depart_gap_s=max(1, self.vars["depart_gap_s"].get()),
            seed=max(1, self.vars["seed"].get()),
            e0_limit_kmph=max(10, self.vars["e0_limit_kmph"].get()),
            e1_limit_kmph=max(10, self.vars["e1_limit_kmph"].get()),
            e2_limit_kmph=max(10, self.vars["e2_limit_kmph"].get()),
            cautious_share=cautious_share,
            aggressive_share=aggressive_share,
            rsu_range_m=max(20, self.vars["rsu_range_m"].get()),
            v2v_range_m=max(20, self.vars["v2v_range_m"].get()),
            minimum_follow_distance_m=max(5, self.vars["minimum_follow_distance_m"].get()),
        )

    def _refresh_summary(self, *_args: object) -> None:
        config = self._collect_config()
        summary = (
            f"Vehicles: {config.vehicle_count}\n"
            f"Road limits: e0 {config.e0_limit_kmph} km/h, e1 {config.e1_limit_kmph} km/h, e2 {config.e2_limit_kmph} km/h\n"
            f"Driver mix: {config.cautious_share}% cautious, {config.normal_share}% normal, {config.aggressive_share}% aggressive\n"
            f"Communication: RSU {config.rsu_range_m} m, V2V {config.v2v_range_m} m, Min follow {config.minimum_follow_distance_m} m\n"
            f"Runtime: depart gap {config.depart_gap_s}s, GUI delay {config.step_delay_ms} ms, seed {config.seed}"
        )
        self.summary_var.set(summary)

    def _launch(self) -> None:
        config = self._collect_config()
        self.root.destroy()
        run_simulation(config)

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    app = LauncherApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
