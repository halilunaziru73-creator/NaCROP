"""
interactive_inputs.py
----------------------
Small helper so every figure/simulation that needs a value NaCROP doesn't already
have (plant density, base temperature, etc.) asks the user a short, plain-language
question instead of silently guessing or hard-coding a number.

Two front-ends are supported automatically:
  - GUI (Tkinter running): a small dialog box, pre-filled with a sensible published
    crop-science default the user can just accept by pressing Enter.
  - CLI / headless (no Tkinter root, e.g. `python -m nacrop.main`): a plain
    `input()` prompt with the same default.

Every answer is cached for the session (`ANSWERS`) so the same question is never
asked twice, and every question documents WHERE the default came from (a published
crop-science reference, or [DEMO/ASSUMED]) so the provenance discipline in
README.md ("No-fabrication policy") is preserved even for interactively-supplied
values.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any

ANSWERS: Dict[str, float] = {}


@dataclass
class Question:
    key: str                      # cache key, e.g. "maize.plant_density_per_ha"
    prompt: str                   # short, plain-language question
    default: float                # sensible published crop-science default
    unit: str = ""
    source_note: str = ""         # provenance of the default value
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    options: Optional[list] = None  # preset dropdown choices shown in the combined dialog


def _tk_root_available() -> bool:
    try:
        import tkinter as tk
        return tk._default_root is not None
    except Exception:
        return False


def ask(q: Question, force: bool = False) -> float:
    """Return the cached/previously-given answer, or ask the user (GUI or CLI)."""
    if not force and q.key in ANSWERS:
        return ANSWERS[q.key]

    value = None
    if _tk_root_available():
        try:
            from tkinter import simpledialog
            label = f"{q.prompt}\n\nUnit: {q.unit}\nDefault ({q.source_note}): {q.default}"
            value = simpledialog.askfloat(
                "NaCROP needs one more value", label,
                initialvalue=q.default, minvalue=q.minimum, maxvalue=q.maximum,
            )
        except Exception:
            value = None
    if value is None:
        try:
            raw = input(
                f"\n[NaCROP] {q.prompt}  (unit: {q.unit}; "
                f"default = {q.default}, {q.source_note}; press Enter to accept)\n> "
            ).strip()
            value = float(raw) if raw else q.default
        except Exception:
            value = q.default

    ANSWERS[q.key] = value
    return value


# ---------------------------------------------------------------------------------
# Standard question bank -- one entry per published crop-science input NaCROP does not
# already carry in crops.py/config.py. Defaults are published crop-science reference
# Chapter 4 "conservative parameter" values (or Annex I crop-file defaults) so a
# user who just presses Enter reproduces the documented FAO defaults.
# ---------------------------------------------------------------------------------
QUESTION_BANK: Dict[str, Question] = {
    "plant_density": Question(
        key="plant_density", unit="plants / ha",
        prompt="What plant density (population) is this field sown at?",
        default=75000, minimum=1000, maximum=300000,
        source_note="typical maize plant density (agronomic reference)",
        options=[40000, 53000, 65000, 75000, 90000, 110000],
    ),
    "cc0_per_seedling_pct": Question(
        key="cc0_per_seedling_pct", unit="% ground cover per seedling at emergence",
        prompt="What is the initial canopy cover per seedling (cc0) at 90% emergence?",
        default=0.5, minimum=0.05, maximum=3.0,
        source_note="cc0 = 0.1-1.5% typical range at seedling emergence",
        options=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5],
    ),
    "ccx_pct": Question(
        key="ccx_pct", unit="% maximum green canopy cover",
        prompt="What maximum green canopy cover (CCx) does this crop/field typically reach?",
        default=95, minimum=30, maximum=99,
        source_note="CCx commonly 75-100% at full canopy closure",
        options=[75, 80, 85, 90, 95, 99],
    ),
    "base_temperature_c": Question(
        key="base_temperature_c", unit="\u00b0C",
        prompt="What base temperature should be used for growing-degree-day (GDD) accumulation?",
        default=10.0, minimum=0.0, maximum=15.0,
        source_note="C4 summer crops (maize) commonly use 8-10\u00b0C",
        options=[0, 5, 7, 8, 10, 12],
    ),
    "reference_harvest_index_pct": Question(
        key="reference_harvest_index_pct", unit="% (HIo)",
        prompt="What reference Harvest Index (HIo) should be used for this crop/cultivar?",
        default=48, minimum=15, maximum=80,
        source_note="modern maize cultivars HIo \u2248 48% (Hsiao et al., 2009)",
        options=[33, 40, 45, 48, 51, 55],
    ),
    "wp_star_g_m2": Question(
        key="wp_star_g_m2", unit="g biomass / m\u00b2 (normalized water productivity, WP*)",
        prompt="What normalized biomass water productivity (WP*) should be used?",
        default=33.7, minimum=10.0, maximum=40.0,
        source_note="C4 crops (maize) WP* \u2248 33-34 g/m\u00b2",
        options=[13, 18, 28, 33, 33.7, 38],
    ),
    "root_zone_depletion_upper_threshold": Question(
        key="root_zone_depletion_upper_threshold", unit="fraction of TAW (0-1)",
        prompt="At what fraction of Total Available Water (TAW) depletion should canopy "
               "expansion begin to slow (upper stress threshold, p-upper)?",
        default=0.14, minimum=0.0, maximum=0.9,
        source_note="leaf-growth p-upper is the most water-stress-sensitive threshold",
        options=[0.05, 0.10, 0.14, 0.20, 0.30, 0.50],
    ),
    "farm_area_ha_for_simulation": Question(
        key="farm_area_ha_for_simulation", unit="hectares",
        prompt="What is the farm/field area to scale the simulation outputs to?",
        default=1.0, minimum=0.01, maximum=10000,
        source_note="user-entered farm area (also used elsewhere in NaCROP)",
        options=[0.5, 1.0, 2.0, 5.0, 10.0, 25.0],
    ),
}


def ask_bank(key: str, override_default: Optional[float] = None) -> float:
    q = QUESTION_BANK[key]
    if override_default is not None:
        q = Question(**{**q.__dict__, "default": override_default})
    return ask(q)


def reset_answers():
    """Clear cached answers -- call when the user switches crop or farm."""
    ANSWERS.clear()


def ask_all_gui(keys, title="NaCROP needs a few values", parent=None) -> Dict[str, float]:
    """Single consolidated dialog: every question in `keys` shown at once as a
    dropdown (combobox, editable -- pick a preset or type a custom number), with
    one 'Run' button, instead of a separate popup per question. Falls back to the
    sequential CLI/GUI `ask()` flow if no Tkinter root is available.

    Returns {key: float} for every key in `keys`, and also updates ANSWERS.
    """
    if not _tk_root_available():
        return {k: ask_bank(k) for k in keys}

    import tkinter as tk
    from tkinter import ttk

    questions = [QUESTION_BANK[k] for k in keys]
    result: Dict[str, float] = {}

    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg="#f2f5f1")
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()

    tk.Label(win, text="NaCROP Simulation \u2014 confirm or change these values",
             bg="#f2f5f1", font=("Segoe UI", 11, "bold"), fg="#16241c"
             ).grid(row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 2))
    tk.Label(win, text="Each dropdown offers common values; pick one or type your own. "
                       "Defaults follow standard published crop-science references.",
             bg="#f2f5f1", font=("Segoe UI", 8, "italic"), fg="#556",
             wraplength=440, justify="left").grid(row=1, column=0, columnspan=3, sticky="w",
                                                   padx=14, pady=(0, 10))

    vars_by_key = {}
    for i, q in enumerate(questions):
        r = i + 2
        tk.Label(win, text=q.prompt, bg="#f2f5f1", font=("Segoe UI", 9), fg="#16241c",
                 wraplength=300, justify="left", anchor="w"
                 ).grid(row=r, column=0, sticky="w", padx=(14, 8), pady=5)
        current = ANSWERS.get(q.key, q.default)
        var = tk.StringVar(value=str(current))
        vals = [str(v) for v in (q.options or [q.default])]
        if str(current) not in vals:
            vals = [str(current)] + vals
        combo = ttk.Combobox(win, textvariable=var, values=vals, width=10, font=("Segoe UI", 9))
        combo.grid(row=r, column=1, sticky="w", pady=5)
        tk.Label(win, text=q.unit, bg="#f2f5f1", font=("Segoe UI", 8), fg="#777",
                 wraplength=140, justify="left").grid(row=r, column=2, sticky="w", padx=(6, 14), pady=5)
        vars_by_key[q.key] = (var, q)

    status_var = tk.StringVar(value="")
    tk.Label(win, textvariable=status_var, bg="#f2f5f1", font=("Segoe UI", 8), fg="#c0392b"
             ).grid(row=len(questions) + 2, column=0, columnspan=3, sticky="w", padx=14)

    def on_submit():
        parsed = {}
        for key, (var, q) in vars_by_key.items():
            try:
                val = float(var.get())
            except ValueError:
                status_var.set(f"'{var.get()}' is not a number \u2014 please fix it.")
                return
            if q.minimum is not None and val < q.minimum:
                val = q.minimum
            if q.maximum is not None and val > q.maximum:
                val = q.maximum
            parsed[key] = val
        result.update(parsed)
        ANSWERS.update(parsed)
        win.destroy()

    def on_cancel():
        for key, (var, q) in vars_by_key.items():
            result[key] = ANSWERS.get(q.key, q.default)
        win.destroy()

    btn_row = len(questions) + 3
    btns = tk.Frame(win, bg="#f2f5f1")
    btns.grid(row=btn_row, column=0, columnspan=3, pady=(6, 14))
    tk.Button(btns, text="Run Simulation \u2192", command=on_submit, bg="#2e7d4f", fg="white",
              font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=6).pack(side="left", padx=6)
    tk.Button(btns, text="Use defaults", command=on_cancel, bg="#8a5a34", fg="white",
              font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=6).pack(side="left", padx=6)

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    win.update_idletasks()
    if parent is not None:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        win.geometry(f"+{px + 60}+{py + 60}")
    win.wait_window()
    return result
