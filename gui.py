"""
gui.py
------
Desktop GUI (Tkinter) for the NaCROP ET & Irrigation pipeline.

Design principles:
  - The only two inputs anywhere in this app are today's TEMPERATURE and HUMIDITY.
    Every tab recomputes from those two values via
    nacrop.main.run_temperature_anchored_pipeline().
  - Any result that has no underlying data is removed from the display automatically
    (no "DATA NOT AVAILABLE" placeholder rows/labels left sitting in the UI) -- see the
    _populate_* methods below, each of which only packs/inserts a widget when a value
    is actually present.

Double-click / run:  python gui.py
"""
import os
import sys
import threading
import webbrowser
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, filedialog
except ImportError:
    print("Tkinter is not installed for this Python.\n"
          "  Ubuntu/Debian:  sudo apt install python3-tk\n"
          "  Fedora:         sudo dnf install python3-tkinter\n"
          "  macOS/Windows:  Tkinter ships with the standard python.org installer "
          "(reinstall Python from python.org if missing).")
    sys.exit(1)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

try:
    from PIL import Image, ImageTk, ImageSequence
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

from nacrop import main as pipeline
from nacrop import report as rpt
from nacrop import thermal_model as tm
from nacrop import logo as logo_mod
from nacrop import icons as icon_mod
from nacrop import visualization as viz
from nacrop import config as cfg

OUT_DIR = os.path.join(APP_DIR, "outputs")
FIG_DIR = os.path.join(OUT_DIR, "figures")

BG = "#f4f5f6"             # soft neutral gray workspace background
CARD_BG = "#ffffff"
ACCENT = "#2e7d4f"        # canopy-green
ACCENT_DARK = "#123524"   # sleek dark forest green (header bar)
WATER = "#1f6f8b"
GRAIN = "#c9a227"
SOIL = "#8a5a34"
ROW2_BG = "#1f3324"
FOOTER_BG = "#12261a"
CYAN = "#00A8E8"           # vibrant primary-action cyan-blue (e.g. Generate & Save Full Report)
CYAN_HOVER = "#0090c8"
CHARCOAL = "#36454F"       # description/metadata label text

# Compact spacing constants -- used by the newer Simulation tab and available
# and available to retrofit into older tabs; halves the old ad-hoc pady/padx values.
PAD_S = 4
PAD_M = 8


class Card(tk.Frame):
    """A small compact stat tile: icon + label + value."""
    def __init__(self, parent, icon_path=None, label="", accent=None, **kw):
        super().__init__(parent, bg=CARD_BG, relief="solid", bd=1, **kw)
        row = tk.Frame(self, bg=CARD_BG)
        row.pack(fill="x", padx=8, pady=(6, 0))
        if icon_path and os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path).subsample(4, 4)
            self._icon_ref = img
            tk.Label(row, image=img, bg=CARD_BG).pack(side="left", padx=(0, 6))
        tk.Label(row, text=label, bg=CARD_BG, font=("Segoe UI", 8, "bold"),
                 fg="#555").pack(side="left")
        self.value_var = tk.StringVar(value="-")
        tk.Label(self, textvariable=self.value_var, bg=CARD_BG, font=("Segoe UI", 12, "bold"),
                 fg=ACCENT_DARK, anchor="w", justify="left", wraplength=200).pack(fill="x", padx=8, pady=(0, 6), anchor="w")

    def set(self, text):
        self.value_var.set(text)


class NaCROPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NaCROP — Nigeria Irrigation DSS")
        self.geometry("1440x880")
        self.configure(bg=BG)
        self.minsize(1120, 700)
        self._set_app_icon()

        self.results = None
        self.area_ha = 1.0
        self.model = None
        self.season = None
        self.today_multi = None
        self.downstream = None
        self._photo_refs = {}
        self._last_report_path = None
        self._overview_map_path = None
        self._ov_current_figure_path = None
        # single shared water-flow-direction value -- bound to BOTH the Overview
        # tab's and the Save Report tab's entry widgets so they can never drift
        # apart into two different "sources of truth" for the same input.
        self.flow_direction_var = tk.StringVar(value="200")

        self.icons = icon_mod.generate_all()
        self._build_toolbar()
        self._build_author_footer()
        self._build_statusbar()
        self._build_notebook()

    # ------------------------------------------------------------------
    # Toolbar — the two live inputs live here, always visible
    # ------------------------------------------------------------------
    def _set_app_icon(self):
        """Sets the window/taskbar icon from assets/icons/ (falls back gracefully if
        the icon files aren't present, e.g. on a fresh checkout before they're built)."""
        icon_dir = os.path.join(APP_DIR, "assets", "icons")
        try:
            if sys.platform.startswith("win"):
                ico_path = os.path.join(icon_dir, "app_icon.ico")
                if os.path.exists(ico_path):
                    self.iconbitmap(ico_path)
                    return
            png_path = os.path.join(icon_dir, "app_icon_256.png")
            if os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=ACCENT_DARK)
        bar.pack(side="top", fill="x")

        row1 = tk.Frame(bar, bg=ACCENT_DARK, height=52)
        row1.pack(side="top", fill="x")
        row2 = tk.Frame(bar, bg="#1f3324", height=40)
        row2.pack(side="top", fill="x")

        try:
            logo_path = logo_mod.generate_logo()
            self._logo_img = tk.PhotoImage(file=logo_path).subsample(8, 8)
            tk.Label(row1, image=self._logo_img, bg=ACCENT_DARK).pack(side="left", padx=(10, 4), pady=4)
        except Exception:
            pass

        tk.Label(row1, text="NaCROP — Nigeria Irrigation DSS", bg=ACCENT_DARK,
                 fg="white", font=("Segoe UI", 13, "bold")).pack(side="left", padx=8)

        input_frame = tk.Frame(row1, bg=ACCENT_DARK)
        input_frame.pack(side="right", padx=10, pady=6)

        self.update_btn = tk.Button(input_frame, text="Update All Results  →", command=self._update_all_async,
                                     bg=ACCENT, fg="white", font=("Segoe UI", 10, "bold"),
                                     relief="flat", padx=12, pady=6, bd=0)
        self.update_btn.pack(side="right", padx=(10, 0))

        self.rh_entry = tk.Entry(input_frame, font=("Segoe UI", 13, "bold"), width=6, justify="center")
        self.rh_entry.pack(side="right")
        self.rh_entry.bind("<Return>", lambda e: self._update_all_async())
        tk.Label(input_frame, text="Humidity (%):", bg=ACCENT_DARK, fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 6))

        self.temp_entry = tk.Entry(input_frame, font=("Segoe UI", 13, "bold"), width=6, justify="center")
        self.temp_entry.pack(side="right")
        self.temp_entry.bind("<Return>", lambda e: self._update_all_async())
        tk.Label(input_frame, text="Temperature (\u00b0C):", bg=ACCENT_DARK, fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 6))

        from nacrop import crops as crops_mod
        self.crop_var = tk.StringVar(value=crops_mod.CROP_LABELS["maize"])
        crop_menu = ttk.Combobox(input_frame, textvariable=self.crop_var, state="readonly",
                                  values=list(crops_mod.CROP_LABELS.values()), width=16,
                                  font=("Segoe UI", 10))
        crop_menu.pack(side="right", padx=(0, 14))
        tk.Label(input_frame, text="Crop:", bg=ACCENT_DARK, fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side="right", padx=(0, 6))
        self._crop_label_to_key = {v: k for k, v in crops_mod.CROP_LABELS.items()}

        # ---- Row 2: Farm Owner + Area + Location -- the ONE place these are entered ----
        row2_inner = tk.Frame(row2, bg="#1f3324")
        row2_inner.pack(side="left", padx=10, pady=6)

        tk.Label(row2_inner, text="Farm Owner:", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.owner_entry = tk.Entry(row2_inner, font=("Segoe UI", 9), width=16)
        self.owner_entry.pack(side="left", padx=(0, 14))
        self.owner_entry.bind("<Return>", lambda e: self._refresh_report_summary())
        self.owner_entry.bind("<FocusOut>", lambda e: self._refresh_report_summary())

        tk.Label(row2_inner, text="Area (ha):", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.area_entry = tk.Entry(row2_inner, font=("Segoe UI", 9, "bold"), width=7, justify="center")
        self.area_entry.pack(side="left", padx=(0, 14))
        self.area_entry.bind("<Return>", lambda e: self._sync_area_and_location())
        self.area_entry.bind("<FocusOut>", lambda e: self._sync_area_and_location())

        tk.Label(row2_inner, text="Latitude:", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.lat_entry = tk.Entry(row2_inner, font=("Segoe UI", 9), width=8, justify="center")
        self.lat_entry.insert(0, "11.1500")
        self.lat_entry.pack(side="left", padx=(0, 10))
        self.lat_entry.bind("<Return>", lambda e: self._sync_area_and_location())
        self.lat_entry.bind("<FocusOut>", lambda e: self._sync_area_and_location())

        tk.Label(row2_inner, text="Longitude:", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.lon_entry = tk.Entry(row2_inner, font=("Segoe UI", 9), width=8, justify="center")
        self.lon_entry.insert(0, "7.6500")
        self.lon_entry.pack(side="left", padx=(0, 10))
        self.lon_entry.bind("<Return>", lambda e: self._sync_area_and_location())
        self.lon_entry.bind("<FocusOut>", lambda e: self._sync_area_and_location())

        tk.Label(row2_inner, text="Location:", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.location_name_var = tk.StringVar(value="Samaru, Zaria, Kaduna State, Nigeria")
        self.location_name_entry = tk.Entry(row2_inner, font=("Segoe UI", 9), width=22,
                                             textvariable=self.location_name_var)
        self.location_name_entry.pack(side="left", padx=(0, 6))
        # Editing the name directly marks it as user-set, so changing Lat/Lon
        # afterwards won't silently overwrite whatever the user typed.
        self.location_name_entry.bind("<KeyRelease>", lambda e: setattr(self, "_location_name_user_set", True))
        self._location_name_user_set = False

        tk.Button(row2_inner, text="\U0001F4CD Auto", command=self._auto_detect_location_name,
                  bg="#1f3324", fg="#8fd0c9", font=("Segoe UI", 8, "bold"), relief="flat",
                  bd=0, cursor="hand2", activebackground="#2c4a37", activeforeground="white"
                  ).pack(side="left", padx=(0, 4))
        tk.Button(row2_inner, text="\U0001F310 My Location", command=self._detect_real_location,
                  bg="#1f3324", fg="#8fd0c9", font=("Segoe UI", 8, "bold"), relief="flat",
                  bd=0, cursor="hand2", activebackground="#2c4a37", activeforeground="white"
                  ).pack(side="left", padx=(0, 10))

        self.location_status_var = tk.StringVar(value="")  # kept for report-summary compatibility only

        maps_btn = tk.Button(row2, text="\U0001F4CD Google Maps", command=self._open_in_google_maps,
                              bg="#1f3324", fg="#8fd0c9", font=("Segoe UI", 8, "bold"), relief="flat",
                              bd=0, cursor="hand2", activebackground="#2c4a37", activeforeground="white")
        maps_btn.pack(side="right", padx=(0, 4))
        maps_btn.bind("<Enter>", lambda e: maps_btn.config(fg="white"))
        maps_btn.bind("<Leave>", lambda e: maps_btn.config(fg="#8fd0c9"))

    def _open_in_google_maps(self):
        """Opens this farm's own entered coordinates in Google Maps in the default
        web browser -- a real, working link (not a mock), using only the standard
        library's webbrowser module, no API key or account required."""
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
        except ValueError:
            messagebox.showinfo("Invalid coordinates",
                                 "Enter a valid Latitude and Longitude in the top bar first.")
            return
        url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        webbrowser.open(url, new=2)

        self.area_ha = 1.0
        self._sync_area_and_location()

    def _sync_area_and_location(self):
        """Single source of truth for area/farm-owner/location, read from the toolbar
        (Row 2) and propagated to every tab -- avoids re-asking the same values in
        multiple places (Irrigation Schedule, Save Report) that could drift apart.

        The location NAME is genuinely changeable with the coordinates: unless the
        user has typed their own name into the Location field, it's auto-suggested
        (nearest known Nigerian town) every time Latitude/Longitude changes -- it
        is no longer hard-coded to 'Zaria, Kaduna State, Nigeria' regardless of
        what coordinates are entered."""
        try:
            self.area_ha = max(float(self.area_entry.get()), 0.0001)
        except ValueError:
            pass
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            if not getattr(self, "_location_name_user_set", False):
                from nacrop import nigeria_locations as nloc
                self.location_name_var.set(nloc.nearest_location_name(lat, lon))
            loc_name = self.location_name_var.get()
            self.location_status_var.set(f"Location: Lat {lat:.4f}, Lon {lon:.4f} ({loc_name})")
        except ValueError:
            pass
        if hasattr(self, "area_ha_entry"):
            self.area_ha_entry.config(state="normal")
            self.area_ha_entry.delete(0, "end"); self.area_ha_entry.insert(0, f"{self.area_ha:g}")
            self.area_ha_entry.config(state="readonly")
            self.area_m2_entry.config(state="normal")
            self.area_m2_entry.delete(0, "end"); self.area_m2_entry.insert(0, f"{self.area_ha * 10000:.1f}")
            self.area_m2_entry.config(state="readonly")
        self._refresh_report_summary()
        self._refresh_connectivity_hub()
        self._redraw_overview_map()
        if self.results is not None:
            self._populate_schedule(self.results)

    def _auto_detect_location_name(self):
        """'Auto' button: forces a re-suggestion from the current Lat/Lon even if
        the user had previously typed a custom name (an explicit override)."""
        self._location_name_user_set = False
        self._sync_area_and_location()

    def _detect_real_location(self):
        """'Use My Real Location' button: a genuine IP-based geolocation lookup
        (no GPS access from a desktop Python app, so IP-geolocation is the
        standard real-world approach) -- works for ANY country, not just Nigeria.
        Uses ip-api.com's free, no-API-key endpoint. Requires this machine to have
        internet access; if it's offline or the request fails, this fails
        honestly with a clear message instead of silently keeping a stale value.
        Threaded so a slow/failed network call never freezes the window."""
        self.status_var.set("Detecting your real location from your internet connection\u2026")
        threading.Thread(target=self._detect_real_location_worker, daemon=True).start()

    def _detect_real_location_worker(self):
        # Two free, no-API-key providers tried in order -- ip-api.com requires a
        # real User-Agent header (a bare urllib request gets a 403 from it), and
        # having a second HTTPS-capable fallback (ipapi.co) means one provider
        # being down/blocked/rate-limited on a given network doesn't silently
        # kill the whole feature.
        import urllib.request
        import json
        providers = [
            ("https://ipapi.co/json/", lambda d: d.get("latitude") is not None and d.get("error") is not True),
            ("http://ip-api.com/json/", lambda d: d.get("status") == "success"),
        ]
        last_error = None
        for url, is_ok in providers:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (NaCROP desktop app)"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode())
                if not is_ok(data):
                    last_error = data.get("reason") or data.get("message") or "lookup returned no location"
                    continue
                lat = data.get("lat", data.get("latitude"))
                lon = data.get("lon", data.get("longitude"))
                city = data.get("city", "")
                region = data.get("regionName", data.get("region", ""))
                country = data.get("country", data.get("country_name", ""))
                name = ", ".join(p for p in (city, region, country) if p)
                self.after(0, lambda: self._apply_detected_location(lat, lon, name))
                return
            except Exception as e:
                last_error = e
                continue
        self.after(0, lambda: self.status_var.set(
            f"Could not detect your real location ({last_error}). This needs an active internet "
            f"connection reaching ipapi.co or ip-api.com; if you're offline or a firewall blocks both, "
            f"enter coordinates manually instead."))

    def _apply_detected_location(self, lat, lon, name):
        self.lat_entry.delete(0, "end"); self.lat_entry.insert(0, f"{lat:.4f}")
        self.lon_entry.delete(0, "end"); self.lon_entry.insert(0, f"{lon:.4f}")
        self.location_name_var.set(name or f"Lat {lat:.4f}, Lon {lon:.4f}")
        self._location_name_user_set = True  # this IS the real detected name; don't overwrite it
        self._sync_area_and_location()
        self.status_var.set(f"\u2713 Detected your real location: {name} (Lat {lat:.4f}, Lon {lon:.4f}).")

    def _build_author_footer(self):
        bar = tk.Frame(self, bg=FOOTER_BG, height=42)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        left = tk.Frame(bar, bg=FOOTER_BG)
        left.pack(side="left", padx=10, pady=4)

        photo_path = os.path.join(APP_DIR, "assets", "author_naziru_halilu.png")
        photo_loaded = False
        if os.path.exists(photo_path):
            try:
                img = tk.PhotoImage(file=photo_path)
                factor = max(1, img.height() // 32)
                if factor > 1:
                    img = img.subsample(factor, factor)
                self._author_photo = img
                tk.Label(left, image=img, bg=FOOTER_BG, bd=0).pack(side="left", padx=(0, 8))
                photo_loaded = True
            except Exception as e:
                print(f"[author footer] could not load {photo_path}: {e}")
        if not photo_loaded:
            # Guaranteed-visible fallback avatar so something always shows even if the
            # photo file is missing or this Tk build can't decode this PNG.
            avatar = tk.Canvas(left, width=32, height=32, bg=FOOTER_BG, highlightthickness=0)
            avatar.create_oval(2, 2, 30, 30, fill=ACCENT, outline="#8fae9c")
            avatar.create_text(16, 16, text="NH", fill="white", font=("Segoe UI", 9, "bold"))
            avatar.pack(side="left", padx=(0, 8))

        tk.Label(left, text="Author: Naziru Halilu", bg=FOOTER_BG, fg="white",
                 font=("Segoe UI", 10, "bold")).pack(side="left")

    def _build_statusbar(self):
        self.status_var = tk.StringVar(
            value="Enter Farm Owner, Area, Temperature and Humidity above, then click 'Update All Results'.")
        bar = tk.Frame(self, bg="#e0e0e0")
        bar.pack(side="bottom", fill="x")
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        self.progress.pack(side="right", padx=8, pady=3)
        tk.Label(bar, textvariable=self.status_var, bg="#e0e0e0", anchor="w",
                 font=("Segoe UI", 9)).pack(side="left", padx=8, pady=3, fill="x")

    # ------------------------------------------------------------------
    # Notebook / tabs
    # ------------------------------------------------------------------
    def _build_notebook(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # Compact ttk theming -- smaller tab padding & row heights throughout, so the
        # whole notebook reads denser without having to hand-edit every tab's widgets.
        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(2, 2, 2, 0))
        style.configure("TNotebook.Tab", padding=(9, 4), font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", CARD_BG)],
                  foreground=[("selected", ACCENT_DARK)])
        style.configure("Treeview", rowheight=20, font=("Segoe UI", 9), background=CARD_BG,
                         fieldbackground=CARD_BG)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TCombobox", padding=2)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=4)

        self.tab_overview = tk.Frame(self.nb, bg=BG)
        self.tab_growth = tk.Frame(self.nb, bg=BG)
        self.tab_simulation = tk.Frame(self.nb, bg=BG)
        self.tab_methods = tk.Frame(self.nb, bg=BG)
        self.tab_soil = tk.Frame(self.nb, bg=BG)
        self.tab_schedule = tk.Frame(self.nb, bg=BG)
        self.tab_efficiency = tk.Frame(self.nb, bg=BG)
        self.tab_report = tk.Frame(self.nb, bg=BG)
        self.tab_save_report = tk.Frame(self.nb, bg=BG)

        # Tab order == pipeline order, with the NEW "NaCROP Simulation" stage
        # appended right after Growth Simulation, the point it occurs in the
        # pipeline -- every pre-existing tab keeps its original relative order.
        # Labels kept short (e.g. "ET Methods" not "ET Methods (today)") so they
        # never truncate regardless of window width.
        for tab, label in [(self.tab_overview, "Overview"), (self.tab_growth, "Growth Sim"),
                            (self.tab_simulation, "NaCROP Simulation"),
                            (self.tab_methods, "ET Methods"),
                            (self.tab_soil, "Soil Water"), (self.tab_schedule, "Irrigation"),
                            (self.tab_efficiency, "Efficiency"),
                            (self.tab_report, "Report Preview"),
                            (self.tab_save_report, "Save Report")]:
            self.nb.add(tab, text=label)

        self._build_overview_tab()
        self._build_growth_tab()
        self._build_simulation_tab()
        self._build_methods_tab()
        self._build_soil_tab()
        self._build_schedule_tab()
        self._build_efficiency_tab()
        self._build_report_tab()
        self._build_save_report_tab()

    def _section_header(self, parent, icon_key, text):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=10, pady=(8, 2))
        icon_path = self.icons.get(icon_key)
        if icon_path and os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path).subsample(4, 4)
            lbl = tk.Label(row, image=img, bg=BG)
            lbl.image = img
            lbl.pack(side="left", padx=(0, 8))
        tk.Label(row, text=text, bg=BG, font=("Segoe UI", 12, "bold"), fg=ACCENT_DARK).pack(side="left")
        return row

    # ---------------- Overview: compact stat cards + two small figures ----------------
    def _build_overview_tab(self):
        outer = tk.Frame(self.tab_overview, bg=BG)
        outer.pack(fill="both", expand=True)

        # slim info ribbon (replaces the old 7-card row -- same live data, compact)
        info_bar = tk.Frame(outer, bg="#e2e5e3", height=26)
        info_bar.pack(side="top", fill="x")
        info_bar.pack_propagate(False)
        self.overview_info_var = tk.StringVar(value="Click 'Update All Results' above to populate this farm's data.")
        tk.Label(info_bar, textvariable=self.overview_info_var, bg="#e2e5e3", fg=CHARCOAL,
                 font=("Segoe UI", 9), anchor="w").pack(side="left", padx=10, fill="x")

        body = ttk.PanedWindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=ACCENT_DARK, width=250)
        center = tk.Frame(body, bg=BG, width=740)
        right = tk.Frame(body, bg=ACCENT_DARK, width=300)
        left.pack_propagate(False)
        center.pack_propagate(False)
        right.pack_propagate(False)
        body.add(left, weight=0)
        body.add(center, weight=1)
        body.add(right, weight=0)

        self._build_overview_left(left)
        self._build_overview_center(center)
        self._build_overview_right(right)

        body.update_idletasks()
        try:
            body.sashpos(0, 250)
            body.sashpos(1, 1010)
        except Exception:
            pass

    # ---------------- Overview left: Layers Panel + all report figures ----------------
    def _build_overview_left(self, parent):
        tk.Label(parent, text="\U0001F5BC Report Figures", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold"), anchor="w", padx=8, pady=5).pack(fill="x")
        self.ov_figures_tree = ttk.Treeview(parent, show="tree", height=14)
        ov_figs_vsb = ttk.Scrollbar(parent, orient="vertical", command=self.ov_figures_tree.yview)
        self.ov_figures_tree.configure(yscrollcommand=ov_figs_vsb.set)
        self.ov_figures_tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        ov_figs_vsb.pack(side="right", fill="y", pady=6)
        self._ov_figure_nodes = {}  # tree-item-id -> figure filename (no path yet, resolved on click)
        groups = [
            ("Climate & ET", [("Daily Crop ET vs Thermal Unit", "thermal_unit_regression.png"),
                               ("ETc Today by Method", "today_method_comparison.png"),
                               ("Rainfall vs ETc", "rainfall_vs_etc.png"),
                               ("Cumulative ETc", "cumulative_etc.png")]),
            ("Soil & Water", [("Soil-Water Profile", None),  # generated per-farm; resolved dynamically
                               ("Soil Depletion vs RAW", "soil_depletion.png"),
                               ("Water Budget", "water_budget.png"),
                               ("Efficiency Breakdown", "efficiency_breakdown.png")]),
            ("Crop Growth", [("Crop Growth Simulation", None),
                              ("NaCROP Simulation (4-step)", None),
                              ("How NaCROP Computed This Season", None)]),
        ]
        for group_name, items in groups:
            node = self.ov_figures_tree.insert("", "end", text=group_name, open=True)
            for label, fname in items:
                leaf = self.ov_figures_tree.insert(node, "end", text="  " + label)
                self._ov_figure_nodes[leaf] = fname
        self.ov_figures_tree.bind("<<TreeviewSelect>>", self._on_figure_select)

    def _resolve_figure_path(self, label, fname):
        """Most figures use a fixed filename; a few are named per-farm or use a
        different naming convention depending on which tab generated them (the
        GUI tabs and the Word-report generator don't always share one filename
        pattern for the same figure) -- try every real candidate and return the
        first one that actually exists on disk, instead of guessing a single name."""
        if fname:
            return fname
        owner = (self.owner_entry.get().strip() or "farm").replace(" ", "_")
        crop_key = self.results["crop"]["key"] if self.results else "maize"
        candidates = {
            "Soil-Water Profile": [f"soil_profile_{owner}.png"],
            "Crop Growth Simulation": ["growth_simulation.png", f"growth_simulation_{owner}.png"],
            "NaCROP Simulation (4-step)": [f"nacrop_simulation_{crop_key}.png",
                                            f"nacrop_simulation_{owner}.png"],
            "How NaCROP Computed This Season": [f"nacrop_system_diagram_{owner}.png"],
            "Farm Map / Boundary": [f"overview_map_{owner}.png"],
            "Terrain Characterisation": [f"terrain_layout_{owner}.png"],
        }
        for candidate in candidates.get(label, []):
            if os.path.exists(os.path.join(FIG_DIR, candidate)):
                return candidate
        # nothing found yet -- return the first candidate anyway so the caller's
        # "not generated yet" message can name a sensible file
        opts = candidates.get(label, [])
        return opts[0] if opts else None

    def _on_figure_select(self, event):
        sel = self.ov_figures_tree.selection()
        if not sel:
            return
        item = sel[0]
        if item not in self._ov_figure_nodes:
            return  # a group header was clicked, not a leaf
        label = self.ov_figures_tree.item(item, "text").strip()
        fname = self._resolve_figure_path(label, self._ov_figure_nodes[item])
        path = os.path.join(FIG_DIR, fname) if fname else None
        if not path or not os.path.exists(path):
            self.status_var.set(f"'{label}' hasn't been generated yet \u2014 click 'Update All Results' "
                                 f"(and, for the crop-growth figures, run them on their own tabs first).")
            return
        self._ov_view_mode = "figure"
        self._ov_current_figure_path = path
        self.ov_center_title_var.set(f"\U0001F5BC {label}")
        self.ov_back_to_map_btn.pack(side="right", padx=8)
        self._display_image_fit(self.overview_map_canvas, path, "ov_fig")

    # ---------------- Overview center: map / figure viewer ----------------
    def _build_overview_center(self, parent):
        map_toolbar = tk.Frame(parent, bg="#e2e5e3", height=28)
        map_toolbar.pack(side="top", fill="x")
        map_toolbar.pack_propagate(False)
        self.ov_center_title_var = tk.StringVar(value="\U0001F5FA Farm Map")
        tk.Label(map_toolbar, textvariable=self.ov_center_title_var,
                 bg="#e2e5e3", fg=CHARCOAL, font=("Segoe UI", 9, "bold")).pack(side="left", padx=8)
        self.ov_maps_btn = tk.Button(map_toolbar, text="\U0001F4CD Open in Google Maps",
                                      command=self._open_in_google_maps,
                                      bg="#e2e5e3", fg="#1f6f8b", font=("Segoe UI", 8, "bold"), relief="flat",
                                      cursor="hand2")
        self.ov_maps_btn.pack(side="right", padx=8)
        self.ov_back_to_map_btn = tk.Button(map_toolbar, text="\u2190 Back to Map",
                                             command=self._show_overview_map,
                                             bg="#e2e5e3", fg="#1f6f8b", font=("Segoe UI", 8, "bold"),
                                             relief="flat", cursor="hand2")
        # not packed initially -- only shown once a report figure is being viewed

        self.overview_map_canvas = tk.Canvas(parent, bg="white", highlightthickness=0)
        self.overview_map_canvas.pack(fill="both", expand=True)
        self.overview_map_canvas.create_text(
            370, 260, text="No results yet.\nEnter Farm Owner, Area, Temperature and Humidity above,\n"
                            "then click 'Update All Results' to generate this farm's map.",
            fill="#9aa89f", font=("Segoe UI", 11), justify="center", tags=("empty_state",))
        self._ov_view_mode = "map"
        self.overview_map_canvas.bind("<Configure>", lambda e: self._display_image_fit(
            self.overview_map_canvas,
            self._ov_current_figure_path if self._ov_view_mode == "figure" else self._overview_map_path,
            "ov_view"
        ) if getattr(self, "_overview_map_path", None) or getattr(self, "_ov_current_figure_path", None)
        else None)

    def _show_overview_map(self):
        self._ov_view_mode = "map"
        self.ov_center_title_var.set("\U0001F5FA Farm Map")
        self.ov_back_to_map_btn.pack_forget()
        if getattr(self, "_overview_map_path", None):
            self._display_image_fit(self.overview_map_canvas, self._overview_map_path, "ov_view")

    def _redraw_overview_map(self):
        """Only draws once this farm's real results exist -- no default/placeholder
        map is shown before 'Update All Results' has actually been run."""
        if not hasattr(self, "overview_map_canvas") or self.results is None:
            return
        try:
            from nacrop import dashboard_map as dm
            farm_owner = self.owner_entry.get().strip() or "This Farm"
            area_ha = self.area_ha if hasattr(self, "area_ha") else 1.0
            try:
                lat = float(self.lat_entry.get())
                lon = float(self.lon_entry.get())
            except (ValueError, tk.TclError):
                lat, lon = 11.15, 7.65
            path = dm.save_dashboard_map_png(
                farm_owner, area_ha, lat, lon,
                fname=f"overview_map_{farm_owner.replace(' ', '_')}.png")
            self._overview_map_path = path
            if self._ov_view_mode == "map":
                self._display_image_fit(self.overview_map_canvas, path, "ov_view")
        except Exception as e:
            print(f"[overview map] could not generate: {e}")

    # ---------------- Overview right: Connectivity Hub + Reports & Outputs ----------------
    def _build_overview_right(self, parent):
        canvas = tk.Canvas(parent, bg=ACCENT_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=ACCENT_DARK)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=298)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        tk.Label(inner, text="\U0001F517 Connectivity Hub", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold"), anchor="w", padx=8, pady=5).pack(fill="x")
        self._hub_var = tk.StringVar()
        tk.Label(inner, textvariable=self._hub_var, bg=ACCENT_DARK, fg="#d7e7de",
                 font=("Segoe UI", 9), justify="left", anchor="w",
                 wraplength=240).pack(fill="x", padx=8, pady=6)
        self._hub_calibration_var = tk.StringVar()
        tk.Label(inner, textvariable=self._hub_calibration_var, bg="#3a2a12", fg="#f0c674",
                 font=("Segoe UI", 8, "bold"), justify="left", anchor="w", wraplength=240
                 ).pack(fill="x", padx=8, pady=(0, 6))
        self._refresh_connectivity_hub()

        tk.Label(inner, text="\U0001F4C4 Save Report", bg="#1f3324", fg="white",
                 font=("Segoe UI", 9, "bold"), anchor="w", padx=8, pady=5).pack(fill="x", pady=(10, 0))
        tk.Label(inner, text="Saves the full report to your computer (you pick the folder). "
                             "Cloud-account uploads (Google Drive, OneDrive, GitHub, etc.) aren't "
                             "available in this app -- save to PC, then upload it yourself if needed.",
                 bg=ACCENT_DARK, fg="#a9c9b8", font=("Segoe UI", 8, "italic"), wraplength=260,
                 justify="left", anchor="w").pack(fill="x", padx=8, pady=(4, 10))

        tk.Label(inner, text="Water flow direction (\u00b0, 0=N,90=E,180=S,270=W):", bg=ACCENT_DARK,
                 fg="#d7e7de", font=("Segoe UI", 8, "bold"), wraplength=240, justify="left",
                 anchor="w").pack(fill="x", padx=8, pady=(2, 2))
        self.ov_flow_entry = tk.Entry(inner, font=("Segoe UI", 9), width=8, justify="center",
                                       textvariable=self.flow_direction_var)
        self.ov_flow_entry.pack(anchor="w", padx=8, pady=(0, 10))

        gen_btn = tk.Button(inner, text="Generate & Save to PC \u2192",
                             command=self._generate_report_async,
                             bg=CYAN, fg="white", font=("Segoe UI", 9, "bold"), relief="flat",
                             padx=10, pady=8, bd=0, cursor="hand2",
                             activebackground=CYAN_HOVER, activeforeground="white")
        gen_btn.pack(fill="x", padx=8, pady=(0, 6))
        tk.Button(inner, text="\U0001F4C2 Open Reports Folder", command=self._open_reports_folder,
                  bg="#234438", fg="#e7f3ee", font=("Segoe UI", 8, "bold"), relief="flat",
                  padx=8, pady=5, cursor="hand2").pack(fill="x", padx=8, pady=(0, 10))
        gen_btn.bind("<Enter>", lambda e: gen_btn.config(bg=CYAN_HOVER))
        gen_btn.bind("<Leave>", lambda e: gen_btn.config(bg=CYAN))

    def _refresh_connectivity_hub(self):
        if not hasattr(self, "_hub_var"):
            return
        try:
            owner = self.owner_entry.get().strip() or "(not entered)"
            area = self.area_entry.get().strip() or "1"
            lat_s = self.lat_entry.get().strip()
            lon_s = self.lon_entry.get().strip()
            loc_name = self.location_name_var.get()
        except (tk.TclError, AttributeError):
            owner, area, lat_s, lon_s, loc_name = "(not entered)", "1", "11.1500", "7.6500", \
                "Samaru, Zaria, Kaduna State, Nigeria"
        self._hub_var.set(
            f"Farm Owner: {owner}\nArea (ha): {area}\nLatitude: {lat_s}\nLongitude: {lon_s}\n"
            f"Location: {loc_name}"
        )
        # Persistent (not a transient status-bar message that gets overwritten)
        # reminder that the underlying crop-water model is calibrated on Samaru,
        # Zaria's own weather data specifically -- shown whenever the entered/
        # detected coordinates are far from there, so predictions for a distant
        # location are never silently presented as if locally calibrated.
        try:
            from nacrop import nigeria_locations as nloc
            lat_f, lon_f = float(lat_s), float(lon_s)
            km = nloc.distance_from_zaria_km(lat_f, lon_f)
            if km > 50:
                self._hub_calibration_var.set(
                    f"\u26a0 {km:,.0f} km from Samaru, Zaria \u2014 the site this app's crop-water "
                    f"model is actually calibrated on. The location NAME/coordinates follow this farm; "
                    f"the ETo/ETc predictions themselves do not re-calibrate for other climates.")
            else:
                self._hub_calibration_var.set("")
        except (ValueError, tk.TclError):
            self._hub_calibration_var.set("")

    def _open_reports_folder(self):
        """Opens the local folder this app saves reports/figures into -- a real,
        working action (no cloud account needed)."""
        folder = OUT_DIR
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
            self.status_var.set(f"Opened local reports folder: {folder}")
        except Exception as e:
            self.status_var.set(f"Could not open the reports folder ({e}). It is at: {folder}")

    def _build_methods_tab(self):
        self._section_header(self.tab_methods, "et", "ET Methods")
        tk.Label(self.tab_methods, bg=BG, anchor="w", justify="left", font=("Segoe UI", 9, "italic"),
                 text=("Temperature = Tmean; Tmax/Tmin reconstructed from the site's typical diurnal range.\n"
                       "Humidity = as entered. Wind/solar radiation/Kc come from the trained 28-year climatology.\n"
                       "Methods without enough data for today are omitted automatically."),
                 fg=CHARCOAL).pack(anchor="w", padx=10, pady=(0, 6))

        selector_row = tk.Frame(self.tab_methods, bg=BG)
        selector_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(selector_row, text="View:", bg=BG, font=("Segoe UI", 10, "bold"),
                 fg=ACCENT_DARK).pack(side="left", padx=(0, 8))
        from nacrop import et_method_info as emi
        self._method_names = ["All Methods (Comparison)"] + list(emi.METHOD_INFO.keys())
        self.method_selector_var = tk.StringVar(value=self._method_names[0])
        method_combo = ttk.Combobox(selector_row, textvariable=self.method_selector_var, state="readonly",
                                     values=self._method_names, width=38, font=("Segoe UI", 9))
        method_combo.pack(side="left")
        method_combo.bind("<<ComboboxSelected>>", self._on_method_view_changed)

        # ---- scrollable content area (item 14) ----
        outer_canvas = tk.Canvas(self.tab_methods, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self.tab_methods, orient="vertical", command=outer_canvas.yview)
        self.methods_content_frame = tk.Frame(outer_canvas, bg=BG)
        self.methods_content_frame.bind(
            "<Configure>", lambda e: outer_canvas.configure(scrollregion=outer_canvas.bbox("all")))
        outer_canvas.create_window((0, 0), window=self.methods_content_frame, anchor="nw")
        outer_canvas.configure(yscrollcommand=vsb.set)
        outer_canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(0, 10))
        vsb.pack(side="right", fill="y", pady=(0, 10))
        outer_canvas.bind("<Enter>", lambda e: outer_canvas.bind_all(
            "<MouseWheel>", lambda ev: outer_canvas.yview_scroll(int(-ev.delta / 120), "units")))
        outer_canvas.bind("<Leave>", lambda e: outer_canvas.unbind_all("<MouseWheel>"))

        # ---- sub-view 1: All Methods comparison (table + bar chart) ----
        self.methods_all_frame = tk.Frame(self.methods_content_frame, bg=BG)
        cols = ("Method", "ETo today (mm/d)", "ETc today (mm/d)", "Diff vs Predicted (mm/d)")
        self.methods_tree = ttk.Treeview(self.methods_all_frame, columns=cols, show="headings", height=11)
        for c in cols:
            self.methods_tree.heading(c, text=c)
            self.methods_tree.column(c, width=220, anchor="center")
        self.methods_tree.tag_configure("closest", background="#eaf5ec", font=("Segoe UI", 9, "bold"))
        self.methods_tree.pack(fill="x", padx=0, pady=(0, 10))
        tk.Label(self.methods_all_frame, text="\u2605 Highlighted row = closest to this farm's own "
                 "season-trend-model predicted ETc (the value used elsewhere in the app).",
                 bg=BG, fg=CHARCOAL, font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(0, 8))
        chart_shadow = tk.Frame(self.methods_all_frame, bg="white", relief="sunken", bd=1, height=320)
        chart_shadow.pack(fill="x", pady=(0, 10))
        chart_shadow.pack_propagate(False)
        self.overview_canvas_bar = tk.Canvas(chart_shadow, bg="white")
        self.overview_canvas_bar.pack(fill="both", expand=True)
        self.overview_canvas_bar.bind("<Configure>", lambda e: self._display_image_fit(
            self.overview_canvas_bar, self._ov_chart2_path, "ov2"
        ) if getattr(self, "_ov_chart2_path", None) else None)

        # ---- sub-view 2: single-method detail (equation, variables, own chart, soil column) ----
        self.methods_detail_frame = tk.Frame(self.methods_content_frame, bg=BG)
        self.method_detail_title_var = tk.StringVar(value="")
        tk.Label(self.methods_detail_frame, textvariable=self.method_detail_title_var, bg=BG,
                 font=("Segoe UI", 13, "bold"), fg=ACCENT_DARK).pack(anchor="w", pady=(0, 4))
        self.method_detail_desc_var = tk.StringVar(value="")
        tk.Label(self.methods_detail_frame, textvariable=self.method_detail_desc_var, bg=BG,
                 fg=CHARCOAL, font=("Segoe UI", 9), wraplength=950, justify="left"
                 ).pack(anchor="w", pady=(0, 8))

        eq_shadow = tk.Frame(self.methods_detail_frame, bg="white", relief="solid", bd=1)
        eq_shadow.pack(fill="x", pady=(0, 8))
        tk.Label(eq_shadow, text="Governing equation", bg="white", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT_DARK).pack(anchor="w", padx=10, pady=(6, 0))
        self.method_detail_eq_var = tk.StringVar(value="")
        tk.Label(eq_shadow, textvariable=self.method_detail_eq_var, bg="white", font=("Consolas", 11),
                 fg=INK if False else "#16241c", wraplength=950, justify="left"
                 ).pack(anchor="w", padx=10, pady=(2, 10))

        var_shadow = tk.Frame(self.methods_detail_frame, bg="white", relief="solid", bd=1)
        var_shadow.pack(fill="x", pady=(0, 10))
        tk.Label(var_shadow, text="Variables / inputs used", bg="white", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT_DARK).pack(anchor="w", padx=10, pady=(6, 2))
        self.method_detail_vars_var = tk.StringVar(value="")
        tk.Label(var_shadow, textvariable=self.method_detail_vars_var, bg="white", font=("Segoe UI", 9),
                 fg="#333", wraplength=950, justify="left").pack(anchor="w", padx=10, pady=(0, 10))

        figs_row = tk.Frame(self.methods_detail_frame, bg=BG)
        figs_row.pack(fill="x", pady=(0, 10))
        left_fig = tk.Frame(figs_row, bg="white", relief="sunken", bd=1, height=300, width=500)
        left_fig.pack(side="left", fill="both", expand=True, padx=(0, 6))
        left_fig.pack_propagate(False)
        self.method_trend_canvas = tk.Canvas(left_fig, bg="white")
        self.method_trend_canvas.pack(fill="both", expand=True)
        right_fig = tk.Frame(figs_row, bg="white", relief="sunken", bd=1, height=300, width=320)
        right_fig.pack(side="left", fill="y", padx=(6, 0))
        right_fig.pack_propagate(False)
        self.method_soilcol_canvas = tk.Canvas(right_fig, bg="white")
        self.method_soilcol_canvas.pack(fill="both", expand=True)

        self.methods_all_frame.pack(fill="both", expand=True)  # default view

    def _on_method_view_changed(self, event=None):
        selection = self.method_selector_var.get()
        if selection == "All Methods (Comparison)":
            self.methods_detail_frame.pack_forget()
            self.methods_all_frame.pack(fill="both", expand=True)
        else:
            self.methods_all_frame.pack_forget()
            self.methods_detail_frame.pack(fill="both", expand=True)
            self._populate_method_detail(selection)

    def _populate_method_detail(self, method_name):
        if self.results is None:
            self.method_detail_title_var.set(method_name)
            self.method_detail_desc_var.set("Click 'Update All Results' above to compute this method's "
                                             "own equation output, trend, and soil-column figure for this farm.")
            self.method_detail_eq_var.set("")
            self.method_detail_vars_var.set("")
            return
        from nacrop import et_method_info as emi
        from nacrop import et_method_figure as emf
        from nacrop import thermal_model as tm
        info = emi.get_info(method_name)
        self.method_detail_title_var.set(info.display_name)
        self.method_detail_desc_var.set(info.description)
        self.method_detail_eq_var.set(info.equation)
        self.method_detail_vars_var.set("  \u2022  ".join(info.variables))

        try:
            temp_c = float(self.temp_entry.get())
            rh_pct = float(self.rh_entry.get())
        except (ValueError, tk.TclError):
            return
        crop_key = self.results["crop"]["key"]
        model = self.model or tm.load_or_build_model()
        season_len = self.results["et"].get("growing_season_days") or 120
        from datetime import date, timedelta
        base = date.today()
        days, eto_series, etc_series, calendar_dates = [], [], [], []
        step = max(1, season_len // 90)  # denser sampling for a smoother monthly aggregate
        for i in range(0, season_len, step):
            r = tm.multi_method_et(temp_c, rh_pct, as_of=base + timedelta(days=i), model=model, crop_key=crop_key)
            m = r["methods"].get(method_name)
            if not m or m.get("status") != "OK":
                continue
            days.append(i)
            eto_series.append(m["et0_mm_day"])
            etc_series.append(m["etc_mm_day"])
            calendar_dates.append(base + timedelta(days=i))
        today_idx = 0 if days and days[0] == 0 else -1  # day offset 0 == today, always the first sampled point
        if days:
            date_by_day = dict(zip(days, calendar_dates))
            trend_path = emf.plot_method_seasonal_chart(
                method_name, days, eto_series, etc_series, today_idx,
                fname=f"et_trend_{info.key}.png",
                day_to_month_label=lambda d: date_by_day[d].strftime("%b"))
            self._method_trend_path = trend_path
            self._display_image_fit(self.method_trend_canvas, trend_path, "method_trend")

        today_row = next((m for m in self.results["et"]["all_methods"] if m["method"] == method_name), None)
        if today_row:
            zr = self.results.get("soil_water", {}).get("root_zone_depth_m", 1.0)
            soilcol_path = emf.plot_method_soil_column(
                method_name, today_row.get("mean_etc") or 0.0, today_row.get("mean_et0") or 0.0,
                root_zone_depth_m=zr or 1.0, fname=f"et_soilcol_{info.key}.png")
            self._method_soilcol_path = soilcol_path
            self._display_image_fit(self.method_soilcol_canvas, soilcol_path, "method_soilcol")

    def _build_soil_tab(self):
        self._section_header(self.tab_soil, "soil", "Soil Water Parameters")
        outer = tk.Frame(self.tab_soil, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=(4, 20))

        frame = tk.Frame(outer, bg=BG, width=340)
        frame.pack(side="left", fill="y", anchor="n")
        frame.pack_propagate(False)
        self.soil_rows = {}
        self.soil_frame = frame

        profile_frame = tk.Frame(outer, bg="white", relief="sunken", bd=1)
        profile_frame.pack(side="left", fill="both", expand=True, padx=(16, 0))
        self.soil_profile_canvas = tk.Canvas(profile_frame, bg="white")
        self.soil_profile_canvas.pack(fill="both", expand=True)
        # Re-render at the correct scale once the canvas is actually mapped/resized
        # (fixes figures rendering tiny when populated while this tab isn't visible yet).
        self.soil_profile_canvas.bind("<Configure>", lambda e: self._display_image_fit(
            self.soil_profile_canvas, self._soil_profile_path, "soil_profile"
        ) if getattr(self, "_soil_profile_path", None) else None)

    def _build_schedule_tab(self):
        self._section_header(self.tab_schedule, "irrigation", "Irrigation Schedule")

        area_row = tk.Frame(self.tab_schedule, bg=BG)
        area_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(area_row, text="Farm Area:", bg=BG, font=("Segoe UI", 10, "bold")).pack(side="left")
        self.area_ha_entry = tk.Entry(area_row, font=("Segoe UI", 10, "bold"), width=8, justify="center",
                                       state="readonly", readonlybackground="#eef3ea")
        self.area_ha_entry.pack(side="left", padx=(4, 2))
        tk.Label(area_row, text="ha  =", bg=BG, font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.area_m2_entry = tk.Entry(area_row, font=("Segoe UI", 10, "bold"), width=10, justify="center",
                                       state="readonly", readonlybackground="#eef3ea")
        self.area_m2_entry.pack(side="left", padx=(0, 6))
        tk.Label(area_row, text="m\u00b2   (set once in the top bar \u2014 not re-entered here)",
                 bg=BG, fg="#777", font=("Segoe UI", 8, "italic")).pack(side="left")

        info = tk.Frame(self.tab_schedule, bg=BG)
        info.pack(fill="x", padx=10, pady=(0, 4))
        self.schedule_summary_var = tk.StringVar(value="No schedule computed yet.")
        tk.Label(info, textvariable=self.schedule_summary_var, bg=BG, anchor="w",
                 font=("Segoe UI", 10, "italic"), justify="left", wraplength=1100).pack(fill="x")

        cols = ("Day", "Stage", "Net Irrigation (mm)", "Gross Irrigation (mm)", "Net Volume (m\u00b3)", "Gross Volume (m\u00b3)")
        self.schedule_tree = ttk.Treeview(self.tab_schedule, columns=cols, show="headings", height=8)
        for c in cols:
            self.schedule_tree.heading(c, text=c)
            self.schedule_tree.column(c, width=130, anchor="center")
        self.schedule_tree.pack(fill="both", expand=True, padx=10, pady=(4, 6))

        tk.Label(self.tab_schedule, text="Water Required by Irrigation Method — This Farm's Season Total",
                 bg=BG, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        cols2 = ("Method", "Application Eff. (%)", "Gross Depth (mm)", "Gross Volume (m\u00b3)")
        self.methods_water_tree = ttk.Treeview(self.tab_schedule, columns=cols2, show="headings", height=4)
        for c in cols2:
            self.methods_water_tree.heading(c, text=c)
            self.methods_water_tree.column(c, width=180, anchor="center")
        self.methods_water_tree.pack(fill="x", padx=10, pady=(0, 10))

    def _build_efficiency_tab(self):
        self._section_header(self.tab_efficiency, "efficiency", "Efficiency & Water Budget")
        frame = tk.Frame(self.tab_efficiency, bg=BG)
        frame.pack(fill="x", padx=20, pady=(4, 10), anchor="n")

        tk.Label(frame, text=("System Efficiency  —  Source: standard irrigation-engineering "
                               "assumptions for the configured system (NOT measured for this farm)"),
                 bg=BG, font=("Segoe UI", 9, "italic"), fg=CHARCOAL).pack(anchor="w", pady=(0, 4))
        eff_row = tk.Frame(frame, bg=BG)
        eff_row.pack(fill="x", pady=(0, 10))
        self.eff_cards = {}
        for key in ["Ec", "Ed", "Ea", "Ep"]:
            c = Card(eff_row, None, key + " (%)")
            c.pack(side="left", fill="x", expand=True, padx=3)
            self.eff_cards[key] = c

        tk.Label(frame, text=("Water Budget (mm)  —  Source: predicted from the entered temperature/"
                               "humidity via the trained weather/ET model, combined with the system "
                               "efficiency assumptions above"),
                 bg=BG, font=("Segoe UI", 9, "italic"), fg=CHARCOAL, wraplength=650,
                 justify="left").pack(anchor="w", pady=(0, 4))
        self.wb_text = tk.Text(frame, height=8, width=70, font=("Consolas", 10))
        self.wb_text.pack(anchor="w", pady=(4, 8))

        self.wue_label_frame = tk.Frame(frame, bg=BG)
        self.wue_label_frame.pack(anchor="w", fill="x")
        self.wue_var = tk.StringVar(value="")
        self.wue_label = tk.Label(self.wue_label_frame, textvariable=self.wue_var, bg=BG, font=("Segoe UI", 10))

    def _build_report_tab(self):
        self._section_header(self.tab_report, "et", "Report Preview \u2014 scroll to review everything before saving")
        outer = tk.Frame(self.tab_report, bg=BG)
        outer.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        canvas = tk.Canvas(outer, bg="white", highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.report_preview_frame = tk.Frame(canvas, bg="white")
        self._report_preview_window = canvas.create_window((0, 0), window=self.report_preview_frame, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.report_preview_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            canvas.itemconfig(self._report_preview_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows/macOS
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-2, "units"))  # Linux scroll up
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(2, "units"))   # Linux scroll down

        self.report_canvas = canvas
        self._report_preview_images = []  # keep PhotoImage refs alive

    def _refresh_report_summary(self):
        if not hasattr(self, "report_summary_var"):
            return
        owner = self.owner_entry.get().strip() or "(not entered)"
        try:
            lat = float(self.lat_entry.get()); lon = float(self.lon_entry.get())
            loc = f"Lat {lat:.4f}, Lon {lon:.4f}"
        except (ValueError, AttributeError):
            loc = "Zaria, Kaduna State"
        self.report_summary_var.set(
            f"Report will use \u2014 Owner: {owner}   |   Area: {self.area_ha:g} ha   |   "
            f"Location: {loc}   (all set in the top bar)")

    def _build_growth_tab(self):
        self._section_header(self.tab_growth, "et", "Crop Growth Simulation \u2014 Nursery to Harvest")
        outer = tk.Frame(self.tab_growth, bg=BG)
        outer.pack(fill="both", expand=True, padx=14, pady=(0, 6))

        top_row = tk.Frame(outer, bg=BG)
        top_row.pack(fill="x", pady=(0, 3))
        tk.Button(top_row, text="Generate Growth Simulation", command=self._generate_growth_video_async,
                  bg=SOIL, fg="white", font=("Segoe UI", 9, "bold"), relief="flat",
                  padx=10, pady=4).pack(side="left")
        self.gif_play_btn = tk.Button(top_row, text="\u25b6 Play", command=self._toggle_gif_playback,
                                       bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                                       relief="flat", padx=10, pady=4, state="disabled")
        self.gif_play_btn.pack(side="left", padx=(6, 0))
        self.gif_save_btn = tk.Button(top_row, text="Save GIF As...", command=self._save_growth_gif_as,
                                       bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                                       relief="flat", padx=10, pady=4, state="disabled")
        self.gif_save_btn.pack(side="left", padx=(6, 14))

        tk.Label(top_row, text="Showing:", bg=BG, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.gif_which_var = tk.StringVar(value="growth")
        tk.Radiobutton(top_row, text="Crop Growth", variable=self.gif_which_var,
                        value="growth", bg=BG, font=("Segoe UI", 9), command=self._switch_gif_view
                        ).pack(side="left", padx=(4, 8))
        tk.Radiobutton(top_row, text="Irrigation Schedule", variable=self.gif_which_var,
                        value="irrigation", bg=BG, font=("Segoe UI", 9), command=self._switch_gif_view
                        ).pack(side="left")

        self.gif_stage_var = tk.StringVar(value="Click 'Generate Growth Simulation' after 'Update All Results'.")
        tk.Label(outer, textvariable=self.gif_stage_var, bg=BG, font=("Segoe UI", 8, "italic"),
                 fg=ACCENT_DARK).pack(anchor="w", pady=(0, 3))

        gif_frame = tk.Frame(outer, bg="white", relief="sunken", bd=1)
        gif_frame.pack(fill="both", expand=True)
        self.gif_canvas = tk.Canvas(gif_frame, bg="white")
        self.gif_canvas.pack(fill="both", expand=True)
        self.gif_canvas.bind("<Configure>", self._on_gif_canvas_resize)

        self.growth_status_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self.growth_status_var, bg=BG, font=("Segoe UI", 8),
                 fg=CHARCOAL, wraplength=1100, justify="left").pack(anchor="w", pady=(2, 0))

    # ---------------- Simulation: NEW 4-step crop-growth pipeline stage ----------------
    def _build_simulation_tab(self):
        self._section_header(self.tab_simulation, "et",
                              "NaCROP Simulation \u2014 4-step scheme (CC \u2192 Tr \u2192 Biomass \u2192 Yield)")
        outer = tk.Frame(self.tab_simulation, bg=BG)
        outer.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        top_row = tk.Frame(outer, bg=BG)
        top_row.pack(fill="x", pady=(0, 6))
        self.sim_run_btn = tk.Button(top_row, text="Run NaCROP Simulation...",
                                      command=self._run_simulation_async,
                                      bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                                      relief="flat", padx=10, pady=5)
        self.sim_run_btn.pack(side="left")
        self.sim_status_var = tk.StringVar(
            value="Click 'Update All Results' first, then run the simulation for the selected crop.")
        tk.Label(top_row, textvariable=self.sim_status_var, bg=BG, font=("Segoe UI", 8, "italic"),
                 fg="#556").pack(side="left", padx=12)

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        fig_frame = tk.Frame(body, bg="white", relief="sunken", bd=1)
        fig_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.sim_canvas = tk.Canvas(fig_frame, bg="white")
        self.sim_canvas.pack(fill="both", expand=True)
        self.sim_canvas.bind("<Configure>", lambda e: self._display_image_fit(
            self.sim_canvas, self._sim_fig_path, "sim_fig") if getattr(self, "_sim_fig_path", None) else None)

        stats = tk.Frame(body, bg=CARD_BG, relief="solid", bd=1)
        stats.grid(row=0, column=1, sticky="nsew")
        tk.Label(stats, text="Simulation summary", bg=CARD_BG, font=("Segoe UI", 10, "bold"),
                 fg=ACCENT_DARK).pack(anchor="w", padx=8, pady=(8, 4))
        self.sim_summary_var = tk.StringVar(value="\u2014")
        tk.Label(stats, textvariable=self.sim_summary_var, bg=CARD_BG, font=("Segoe UI", 9),
                 fg=ACCENT_DARK, justify="left", wraplength=260, anchor="nw"
                 ).pack(anchor="nw", padx=8, pady=(0, 8), fill="both", expand=True)

    def _run_simulation_async(self):
        if self.results is None or self.model is None:
            messagebox.showinfo("Run 'Update All Results' first",
                                 "The NaCROP Simulation stage reuses this farm's own climate/soil "
                                 "pipeline output \u2014 click 'Update All Results' at the top first.")
            return
        # One consolidated dialog (all questions as dropdowns, single submit) instead
        # of asking one Tkinter popup per parameter -- must run on the main thread;
        # only the numeric simulation + figure rendering is pushed to a worker thread.
        from nacrop import interactive_inputs as qa
        answers = qa.ask_all_gui(
            ["plant_density", "cc0_per_seedling_pct", "ccx_pct", "base_temperature_c",
             "reference_harvest_index_pct", "wp_star_g_m2"],
            title="NaCROP Simulation \u2014 confirm parameters", parent=self)
        if not answers:
            return
        crop_key = self.results["crop"]["key"]
        self.sim_run_btn.config(state="disabled")
        self.sim_status_var.set("Simulating\u2026")
        threading.Thread(target=self._run_simulation_worker, args=(crop_key,), daemon=True).start()

    def _run_simulation_worker(self, crop_key):
        try:
            from nacrop import simulation as sim
            from nacrop import simulation_figure as simfig
            dwb = self.downstream["dwb"] if self.downstream else None
            depletion = [d.depletion_mm for d in dwb] if dwb else None
            taw = self.downstream["taw_raw"]["TAW_mm"] if self.downstream else None
            result = sim.simulate_nacrop_season(
                crop_key, self.model.doy_climatology, cfg.DEFAULT_SITE.latitude_deg,
                farm_area_ha=self.area_ha, dwb_depletion_series=depletion,
                dwb_taw_series=taw, ask_questions=False,  # already asked on main thread above
            )
            path = simfig.plot_nacrop_simulation(result)
            self._sim_result = result
            self._sim_fig_path = path
            self.after(0, lambda: self._populate_simulation(result, path))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Simulation error", str(e)))
        finally:
            self.after(0, lambda: (self.sim_run_btn.config(state="normal"),
                                    self.sim_status_var.set("Done.")))

    def _populate_simulation(self, result, path):
        self._display_image_fit(self.sim_canvas, path, "sim_fig")
        p = result.params
        self.sim_summary_var.set(
            f"Crop: {result.crop_name}\n"
            f"Season length: {result.season_length_days} days\n\n"
            f"CC0: {p['CC0_pct']}%   CCx: {p['CCx_pct']}%\n"
            f"CGC: {p['CGC_per_day']}/day   CDC: {p['CDC_per_day']}/day\n"
            f"KcTr,x: {p['KcTr_x']}\n"
            f"WP*: {p['WP_star_g_m2']} g/m\u00b2\n"
            f"Base temperature: {p['base_temperature_c']}\u00b0C\n\n"
            f"Final biomass: {result.final_biomass_kg_ha:,.0f} kg/ha\n"
            f"Reference HIo: {result.reference_hi_pct}%\n"
            f"Actual HI (stress-adjusted): {result.actual_hi_pct}%\n\n"
            f"Yield: {result.yield_kg_ha:,.0f} kg/ha  ({result.yield_t_ha:.2f} t/ha)\n\n"
            f"Farm area: {result.farm_area_ha:g} ha\n"
            f"Farm total yield: \u2248{result.farm_total_yield_kg:,.0f} kg"
        )

    def _build_save_report_tab(self):
        self._section_header(self.tab_save_report, "et", "Save Full Farm Report (Word document)")
        outer = tk.Frame(self.tab_save_report, bg=BG)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(outer, bg=BG, justify="left", anchor="w", font=("Segoe UI", 9),
                 fg="#444", wraplength=1000, text=(
                     "Generates a single Word (.docx) document covering: Overview (with plain-language "
                     "explanation), Dashboard, Soil Water, Irrigation Schedule (with volumes for your farm "
                     "area), Efficiency & Water Budget, all figures, and a farm-location map with an "
                     "irrigation-method recommendation. Run 'Update All Results' first so there is "
                     "something to report.")).pack(anchor="w", pady=(0, 12))

        try:
            import docx  # noqa: F401
        except ImportError:
            tk.Label(outer, bg="#fff3e0", fg=SOIL, font=("Segoe UI", 9, "bold"),
                     justify="left", anchor="w", wraplength=1000, relief="solid", bd=1,
                     padx=8, pady=6, text=(
                         "\u26a0 The 'python-docx' package is not installed, so report generation will fail. "
                         "Install it first:   pip install python-docx   (then restart this app).")
                     ).pack(anchor="w", fill="x", pady=(0, 12))

        form = tk.Frame(outer, bg=BG)
        form.pack(anchor="w", fill="x")

        def _field(row, label, default="", textvariable=None):
            tk.Label(form, text=label, bg=BG, font=("Segoe UI", 10, "bold"), width=38,
                     anchor="w", justify="left", wraplength=300).grid(row=row, column=0, sticky="w", pady=4)
            if textvariable is not None:
                e = tk.Entry(form, font=("Segoe UI", 10), width=20, textvariable=textvariable)
            else:
                e = tk.Entry(form, font=("Segoe UI", 10), width=20)
                if default:
                    e.insert(0, default)
            e.grid(row=row, column=1, sticky="w", pady=4)
            return e

        self.report_summary_var = tk.StringVar(value="")
        tk.Label(form, textvariable=self.report_summary_var, bg="#eef3ea", fg=ACCENT_DARK,
                 font=("Segoe UI", 9, "bold"), anchor="w", justify="left", wraplength=650,
                 relief="solid", bd=1, padx=6, pady=4).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.report_flow_entry = _field(1, "Water flow direction (\u00b0, 0=N,90=E,180=S,270=W):",
                                         textvariable=self.flow_direction_var)

        gen_btn = tk.Button(form, text="Generate & Save Full Report \u2192", command=self._generate_report_async,
                             bg=CYAN, fg="white", font=("Segoe UI", 11, "bold"), relief="flat",
                             activebackground=CYAN_HOVER, activeforeground="white",
                             padx=18, pady=10, bd=0, cursor="hand2")
        gen_btn.grid(row=2, column=0, columnspan=2, pady=(14, 6), sticky="w")
        gen_btn.bind("<Enter>", lambda e: gen_btn.config(bg=CYAN_HOVER))
        gen_btn.bind("<Leave>", lambda e: gen_btn.config(bg=CYAN))
        tk.Label(form, bg=BG, fg=CHARCOAL, font=("Segoe UI", 8, "italic"), justify="left", wraplength=600,
                 text=("Produces the full report, including a terrain-characterisation layout clipped to "
                       "an irregular boundary sized exactly to your entered farm area, plus every other "
                       "figure and table. The crop growth-stage video simulation has its own tab "
                       "(\"Growth Simulation\", next to Overview) with a compact player.")
                 ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.report_status_var = tk.StringVar(value="")
        tk.Label(outer, textvariable=self.report_status_var, bg=BG, font=("Segoe UI", 10),
                 fg=ACCENT_DARK, wraplength=1000, justify="left").pack(anchor="w", pady=(6, 0))
        self._refresh_report_summary()

    def _generate_report_async(self):
        if self.results is None:
            messagebox.showwarning("No results yet", "Click 'Update All Results' first.")
            return
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            flow_deg = float(self.flow_direction_var.get())
        except (ValueError, AttributeError):
            messagebox.showerror("Invalid input", "Latitude, longitude and flow direction must be numeric.")
            return
        area_ha = self.area_ha  # single source of truth: the top bar's area field
        owner = self.owner_entry.get().strip()

        default_name = f"{(owner or 'farm_report').replace(' ', '_')}_irrigation_report.docx"
        save_path = filedialog.asksaveasfilename(
            title="Save Farm Irrigation Report As", defaultextension=".docx",
            initialfile=default_name, filetypes=[("Word document", "*.docx"), ("All files", "*.*")])
        if not save_path:
            return  # user cancelled -- don't save anywhere

        self.report_status_var.set("Generating report...")
        threading.Thread(target=self._generate_report_worker,
                          args=(owner, area_ha, lat, lon, flow_deg, save_path), daemon=True).start()

    def _prompt_save_copy(self, src_path, default_name):
        """Asks the user where to save a copy of a just-generated figure (they can
        cancel to leave it only in the app's working outputs folder)."""
        if not src_path or not os.path.exists(src_path):
            return
        if not messagebox.askyesno("Save a copy?", f"Save a copy of this figure to a location you choose?\n"
                                                     f"(It has also been kept in the app's outputs folder.)"):
            return
        ext = os.path.splitext(src_path)[1] or ".png"
        save_path = filedialog.asksaveasfilename(
            title="Save Figure As", defaultextension=ext, initialfile=default_name,
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")])
        if not save_path:
            return
        try:
            import shutil
            shutil.copyfile(src_path, save_path)
            self.report_status_var.set(f"\u2713 Copy saved to: {save_path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _generate_growth_video_async(self):
        if self.results is None:
            messagebox.showwarning("No results yet", "Click 'Update All Results' first.")
            return
        owner = self.owner_entry.get().strip() or "This Farm"
        self.growth_status_var.set("Simulating crop growth: nursery \u2192 harvest...")
        threading.Thread(target=self._generate_growth_video_worker, args=(owner,), daemon=True).start()

    def _generate_growth_video_worker(self, owner):
        try:
            from nacrop import growth_video as gv
            crop_key = self.results["crop"]["key"]
            crop_display = self.results["crop"]["display_name"]
            stage_rows = gv.compute_stage_water_balance(crop_key, self.area_ha, self.model, self.downstream)
            filmstrip_path = gv.generate_filmstrip(crop_key, crop_display, owner, stage_rows,
                                                    fname=f"growth_filmstrip_{owner.replace(' ', '_')}.png")
            gif_result = gv.generate_growth_gif(crop_key, crop_display, owner, stage_rows,
                                                 fname=f"growth_simulation_{owner.replace(' ', '_')}.gif")
            self._growth_stage_rows = stage_rows
            self._growth_gif_path = gif_result.get("path")
            self._growth_gif_frames = gif_result.get("n_frames", 0)

            irr_result = gv.generate_irrigation_schedule_animation(
                crop_key, crop_display, owner, self.results["recommended_schedule"], self.area_ha,
                fname=f"irrigation_schedule_animation_{owner.replace(' ', '_')}.gif")
            self._irrigation_gif_path = irr_result.get("path") if irr_result.get("status") == "OK" else None

            if gif_result["status"] == "OK":
                msg = (f"\u2713 Growth simulation ready: {filmstrip_path}\n"
                       f"Animated GIF ({gif_result['n_frames']} frames): {gif_result['path']}")
            else:
                msg = (f"\u2713 Filmstrip ready: {filmstrip_path}\n"
                       f"(GIF skipped: {gif_result['reason']})")
            if irr_result.get("status") == "OK":
                msg += f"\n\u2713 Irrigation schedule animation ready ({irr_result['n_frames']} events)."
            elif irr_result.get("reason"):
                msg += f"\n(Irrigation animation skipped: {irr_result['reason']})"
            self.after(0, lambda: self.growth_status_var.set(msg))
            self.after(0, lambda: self._populate_report(self.results) if self.results else None)
            self.after(0, self._load_gif_player)
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.growth_status_var.set(f"Error generating growth video: {err}"))

    def _save_growth_gif_as(self):
        which_val = self.gif_which_var.get() if hasattr(self, "gif_which_var") else "growth"
        if which_val == "irrigation":
            src = getattr(self, "_irrigation_gif_path", None)
            suffix = "irrigation_schedule_animation"
        else:
            src = getattr(self, "_growth_gif_path", None)
            suffix = "growth_simulation"
        if not src or not os.path.exists(src):
            messagebox.showwarning("No simulation yet", "Generate the simulation first.")
            return
        owner = self.owner_entry.get().strip() or "farm"
        default_name = f"{owner.replace(' ', '_')}_{suffix}.gif"
        save_path = filedialog.asksaveasfilename(
            title="Save Animation As", defaultextension=".gif",
            initialfile=default_name, filetypes=[("GIF animation", "*.gif"), ("All files", "*.*")])
        if not save_path:
            return
        try:
            import shutil
            shutil.copyfile(src, save_path)
            self.growth_status_var.set(f"\u2713 GIF saved to: {save_path}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _load_gif_player(self):
        which = getattr(self, "gif_which_var", None)
        which_val = which.get() if which else "growth"
        if which_val == "irrigation":
            path = getattr(self, "_irrigation_gif_path", None)
        else:
            path = getattr(self, "_growth_gif_path", None)
        if not path or not os.path.exists(path):
            self.gif_stage_var.set("This animation isn't available for the current run "
                                    "(e.g. no irrigation events were needed).")
            self.gif_play_btn.config(state="disabled")
            self.gif_save_btn.config(state="disabled")
            return

        # Load every frame at FULL quality (PIL, if available) so the animation stays
        # crisp -- scaling to fit the visible canvas happens separately at DISPLAY
        # time in _show_gif_frame, so nothing is ever cropped off the top/bottom
        # regardless of window size, and it rescales live if the window is resized.
        self._gif_pil_frames = None
        self._gif_frame_images = []
        if _PIL_AVAILABLE:
            try:
                im = Image.open(path)
                self._gif_pil_frames = [f.copy().convert("RGB") for f in ImageSequence.Iterator(im)]
            except Exception as e:
                print(f"[gif player] PIL load failed, falling back: {e}")
                self._gif_pil_frames = None
        if self._gif_pil_frames is None:
            i = 0
            while True:
                try:
                    img = tk.PhotoImage(file=path, format=f"gif -index {i}")
                except Exception:
                    break
                self._gif_frame_images.append(img)
                i += 1

        self._gif_frame_idx = 0
        self._gif_playing = False
        self.gif_play_btn.config(state="normal", text="\u25b6 Play")
        self.gif_save_btn.config(state="normal")
        n_frames = len(self._gif_pil_frames) if self._gif_pil_frames else len(self._gif_frame_images)
        if n_frames:
            self._show_gif_frame(0)

    def _switch_gif_view(self):
        self._load_gif_player()

    def _show_gif_frame(self, idx):
        pil_frames = getattr(self, "_gif_pil_frames", None)
        legacy_frames = getattr(self, "_gif_frame_images", None)
        n_frames = len(pil_frames) if pil_frames else (len(legacy_frames) if legacy_frames else 0)
        if not n_frames:
            return
        idx = idx % n_frames
        self._gif_frame_idx = idx

        self.gif_canvas.delete("all")
        cw = self.gif_canvas.winfo_width() or 700
        ch = self.gif_canvas.winfo_height() or 500
        pad = 16

        if pil_frames:
            src = pil_frames[idx]
            scale = min((cw - pad) / src.width, (ch - pad) / src.height, 1.0)
            if scale < 1.0:
                new_size = (max(1, int(src.width * scale)), max(1, int(src.height * scale)))
                shown = src.resize(new_size, Image.LANCZOS)
            else:
                shown = src
            photo = ImageTk.PhotoImage(shown)
            self._gif_current_photo = photo  # keep a ref alive
            self.gif_canvas.create_image(cw // 2, ch // 2, anchor="center", image=photo)
        else:
            img = legacy_frames[idx]
            self.gif_canvas.create_image(cw // 2, ch // 2, anchor="center", image=img)

        rows = getattr(self, "_growth_stage_rows", [])
        frames_per_stage = max(1, n_frames // max(1, len(rows)))
        stage_i = min(idx // frames_per_stage, len(rows) - 1) if rows else 0
        if rows:
            self.gif_stage_var.set(f"Frame {idx + 1}/{n_frames} \u2014 {rows[stage_i]['label']}")

    def _on_gif_canvas_resize(self, event):
        # Redraw the current frame scaled to the new canvas size (debounced isn't
        # necessary here -- redrawing one already-loaded PIL frame is cheap).
        if getattr(self, "_gif_pil_frames", None) or getattr(self, "_gif_frame_images", None):
            self._show_gif_frame(getattr(self, "_gif_frame_idx", 0))

    def _toggle_gif_playback(self):
        self._gif_playing = not getattr(self, "_gif_playing", False)
        self.gif_play_btn.config(text="\u23f8 Pause" if self._gif_playing else "\u25b6 Play")
        if self._gif_playing:
            self._animate_gif()

    def _animate_gif(self):
        if not getattr(self, "_gif_playing", False):
            return
        self._show_gif_frame(self._gif_frame_idx + 1)
        self.after(400, self._animate_gif)

    def _generate_report_worker(self, owner, area_ha, lat, lon, flow_deg, save_path):
        try:
            from nacrop import report_docx as rd
        except ImportError:
            self.after(0, lambda: self.report_status_var.set(
                "The 'python-docx' package is not installed. Install it and try again:\n"
                "    pip install python-docx\n"
                "(then restart the app)."))
            return
        try:
            path = rd.generate_full_report(
                self.results, self.downstream, self.today_multi, self.season, self.model,
                farm_owner_name=owner, area_ha=area_ha, farm_lat=lat, farm_lon=lon,
                water_flow_direction_deg=flow_deg, output_path=save_path)
            self._last_report_path = path
            self.after(0, lambda: self.report_status_var.set(f"\u2713 Report saved: {path}"))
            self.after(0, lambda: self.status_var.set(f"\u2713 Report saved: {path}"))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.report_status_var.set(f"Error generating report: {err}"))

    # ------------------------------------------------------------------
    # The single action: read temperature+humidity, recompute everything, repaint tabs
    # ------------------------------------------------------------------
    def _update_all_async(self):
        owner = self.owner_entry.get().strip()
        area_txt = self.area_entry.get().strip()
        temp_txt = self.temp_entry.get().strip()
        rh_txt = self.rh_entry.get().strip()

        missing = []
        if not owner:
            missing.append("Farm Owner")
        if not area_txt:
            missing.append("Area (ha)")
        if not temp_txt:
            missing.append("Temperature")
        if not rh_txt:
            missing.append("Humidity")
        if missing:
            messagebox.showwarning(
                "Missing information",
                "Please fill in before running anything:\n\n  \u2022 " + "\n  \u2022 ".join(missing) +
                "\n\nAll four are entered in the top bar.")
            return

        try:
            temp = float(temp_txt)
            rh = float(rh_txt)
            area_ha = float(area_txt)
        except ValueError:
            messagebox.showerror("Invalid input", "Temperature, Humidity and Area must be numeric.")
            return
        if not (0 <= rh <= 100):
            messagebox.showerror("Invalid input", "Humidity must be between 0 and 100%.")
            return
        if area_ha <= 0:
            messagebox.showerror("Invalid input", "Area must be greater than 0.")
            return
        # Hard block on physically impossible values (catches typos like "230" instead
        # of "23.0" before they silently propagate into every downstream calculation,
        # producing nonsensical results such as VPD in the thousands of kPa).
        if not (-10 <= temp <= 55):
            messagebox.showerror("Invalid input",
                                  f"{temp}\u00b0C is outside any physically plausible air temperature "
                                  f"range (-10 to 55\u00b0C). Please check for a typo.")
            return
        # Soft warning for values that are numerically valid but far outside what Zaria
        # actually experiences -- almost always a typo, but the user can confirm to
        # proceed anyway for deliberate edge-case testing.
        unusual = []
        if not (15 <= temp <= 48):
            unusual.append(f"Temperature {temp}\u00b0C is well outside Zaria's typical range (~15-48\u00b0C).")
        if rh < 5:
            unusual.append(f"Humidity {rh}% is extremely low even for peak Harmattan dry season.")
        if unusual:
            proceed = messagebox.askyesno(
                "Unusual value entered",
                "\n".join(unusual) + "\n\nThis is usually a typo. Continue anyway with these exact values?")
            if not proceed:
                return

        crop_key = self._crop_label_to_key.get(self.crop_var.get(), "maize")
        self.update_btn.config(state="disabled")
        self.status_var.set(f"Recomputing every tab for {self.crop_var.get()}, T={temp}\u00b0C, RH={rh}%...")
        self.progress.start(12)
        threading.Thread(target=self._update_all_worker, args=(temp, rh, crop_key), daemon=True).start()

    def _update_all_worker(self, temp, rh, crop_key):
        try:
            results, model, season, today_multi, downstream = pipeline.run_temperature_anchored_pipeline(
                temp, rh, crop_key=crop_key)
            self.results = results
            self.model = model
            self.season = season
            self.today_multi = today_multi
            self.downstream = downstream
            self._export_figures(temp, rh)
            self.after(0, lambda: self.status_var.set(
                f"Building the report preview (this may take a few seconds)..."))
            self._generate_docx_preview()
            self.after(0, self._populate_all_tabs)
            self.after(0, lambda: self.status_var.set(
                f"Updated for T={temp}\u00b0C, RH={rh}% on {results['temperature_input']['date']}."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Computation error", str(e)))
            self.after(0, lambda: self.status_var.set("Error — see popup."))
        finally:
            self.after(0, self._update_finished)

    def _update_finished(self):
        self.progress.stop()
        self.update_btn.config(state="normal")

    def _generate_docx_preview(self):
        """Builds the ACTUAL Word report (same code path as 'Generate & Save Full
        Report') to a scratch file, then renders it to page images via LibreOffice +
        poppler so the in-app preview looks exactly like the real document -- header,
        footer, formatted tables, and figures -- not an approximation. Falls back
        gracefully (self._preview_page_images = None) if those tools aren't installed,
        in which case _populate_report shows a simpler text+figures preview instead."""
        import shutil as _shutil
        import subprocess
        self._preview_page_images = None
        if not (_shutil.which("soffice") and _shutil.which("pdftoppm")):
            return
        try:
            from nacrop import report_docx as rd
            owner = self.owner_entry.get().strip() or "Preview"
            try:
                lat = float(self.lat_entry.get())
                lon = float(self.lon_entry.get())
            except ValueError:
                lat, lon = 11.15, 7.65
            try:
                flow_deg = float(self.report_flow_entry.get())
            except (ValueError, AttributeError):
                flow_deg = 200.0

            preview_dir = os.path.join(OUT_DIR, ".preview")
            os.makedirs(preview_dir, exist_ok=True)
            for f in os.listdir(preview_dir):
                try:
                    os.remove(os.path.join(preview_dir, f))
                except OSError:
                    pass
            docx_path = os.path.join(preview_dir, "preview.docx")
            rd.generate_full_report(
                self.results, self.downstream, self.today_multi, self.season, self.model,
                farm_owner_name=owner, area_ha=self.area_ha, farm_lat=lat, farm_lon=lon,
                water_flow_direction_deg=flow_deg, output_path=docx_path)

            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir",
                             preview_dir, docx_path], timeout=60, capture_output=True)
            pdf_path = os.path.join(preview_dir, "preview.pdf")
            if not os.path.exists(pdf_path):
                return
            subprocess.run(["pdftoppm", "-jpeg", "-r", "110", pdf_path,
                             os.path.join(preview_dir, "page")], timeout=60, capture_output=True)
            pages = sorted(f for f in os.listdir(preview_dir)
                            if f.startswith("page") and f.lower().endswith(".jpg"))
            if pages:
                self._preview_page_images = [os.path.join(preview_dir, p) for p in pages]
        except Exception as e:
            print(f"[docx preview] falling back to simple preview: {e}")
            self._preview_page_images = None

    def _export_figures(self, temp, rh):
        # Clear ALL previously-generated figures first -- these were named with a
        # farm-owner suffix (e.g. process_diagram_<Name>.png) to avoid overwriting
        # between reports, but that meant files from a PREVIOUS session/owner never
        # got removed and kept showing up alongside the current run's figures in the
        # Figures tab -- a real bug (duplicate/stale figures shown together). Every
        # "Update All Results" run now starts from a clean figures folder, so only
        # this run's own figures are ever visible.
        if os.path.isdir(FIG_DIR):
            for fname in os.listdir(FIG_DIR):
                if fname.lower().endswith((".png", ".gif")):
                    try:
                        os.remove(os.path.join(FIG_DIR, fname))
                    except OSError:
                        pass

        model, season, today = self.model, self.season, self.today_multi
        days, etc_series, rainfall_series = season["days"], season["etc_series"], season["rainfall_series"]
        dwb = self.downstream["dwb"]
        sched = self.downstream["schedule"]
        taw_raw = self.downstream["taw_raw"]
        wb = self.downstream["water_budget"]
        eff = self.downstream["efficiency"]

        viz.plot_thermal_unit_regression(
            model.gdd_pooled, model.etc_pooled, model.coeffs, model.r_squared,
            current_point=(season["today_prediction"]["cumulative_gdd"],
                            season["today_prediction"]["ensemble_etc_today_mm_day"]),
            fname="thermal_unit_regression.png")

        names = [n for n, r in today["methods"].items() if r["status"] == "OK"]
        etcs = [today["methods"][n]["etc_mm_day"] for n in names]
        viz.plot_water_budget_bar(names, etcs, "today_method_comparison.png",
                                   title=f"ETc Today by Method (T={temp}\u00b0C, RH={rh}%)")

        viz.plot_seasonal_et_vs_reference(
            days, etc_series, season["et0_series"],
            current_dap=season["dap_today"], current_etc=season["today_prediction"]["predicted_etc_mm_day"],
            fname="seasonal_et_vs_reference.png")
        viz.plot_cumulative_et(days, {"ETc (trained climatology)": etc_series}, "cumulative_etc.png")

        irrig_days = [e["day"] for e in sched["events"]]
        depletion = [d.depletion_mm for d in dwb]
        viz.plot_soil_depletion(days, depletion, taw_raw["RAW_mm"], taw_raw["TAW_mm"], irrig_days,
                                 "soil_depletion.png")
        viz.plot_rainfall_vs_etc(days, rainfall_series, etc_series, "rainfall_vs_etc.png")
        viz.plot_efficiency_breakdown(eff["Ec"], eff["Ed"], eff["Ea"], eff["Ep"], "efficiency_breakdown.png")
        viz.plot_water_budget_bar(
            ["Rainfall", "Eff. Rainfall", "ETc used", "Runoff", "Deep Perc."],
            [wb["rainfall_mm"], wb["effective_rainfall_mm"], wb["ETc_used_mm"],
             wb["runoff_mm"], wb["deep_percolation_mm"]], "water_budget.png")

        from nacrop import growth_simulation as gsim
        crop_key = self.results["crop"]["key"]
        crop_display = self.results["crop"]["display_name"]
        farm_owner = self.owner_entry.get().strip() if hasattr(self, "owner_entry") else ""
        gsim.plot_growth_simulation(crop_key, crop_display, farm_owner or "This Farm",
                                     model=model, fname="growth_simulation.png")

    # ------------------------------------------------------------------
    # Populate every tab — any missing value is simply not shown (no placeholders)
    # ------------------------------------------------------------------
    def _populate_all_tabs(self):
        r = self.results
        self._populate_overview(r)
        self._populate_methods(r)
        self._populate_soil(r)
        self._populate_schedule(r)
        self._populate_efficiency(r)
        self._populate_report(r)
        self.nb.select(self.tab_overview)

    def _display_image_fit(self, canvas, path, ref_key, pad=10):
        """
        Loads an image and displays it CENTERED in the given canvas, scaled down (by
        an integer factor, tk.PhotoImage's only scaling option) so the whole figure is
        visible without needing to scroll -- fixes figures that previously rendered
        anchored top-left and could run off the bottom of a smaller canvas.
        """
        if not os.path.exists(path):
            return
        try:
            img = tk.PhotoImage(file=path)
        except Exception:
            return
        canvas.update_idletasks()
        avail_w = max(canvas.winfo_width() - pad, 50)
        avail_h = max(canvas.winfo_height() - pad, 50)
        factor_w = max(1, -(-img.width() // avail_w))    # ceil division
        factor_h = max(1, -(-img.height() // avail_h))
        factor = max(factor_w, factor_h)
        if factor > 1:
            img = img.subsample(factor, factor)
        self._photo_refs[ref_key] = img
        canvas.delete("all")
        cx = max(avail_w, img.width()) // 2 + pad // 2
        cy = max(avail_h, img.height()) // 2 + pad // 2
        canvas.create_image(cx, cy, anchor="center", image=img)
        canvas.configure(scrollregion=(0, 0, max(avail_w + pad, img.width() + pad),
                                        max(avail_h + pad, img.height() + pad)))

    def _populate_overview(self, r):
        ti = r["temperature_input"]
        et = r["et"]
        crop = r["crop"]
        self.overview_info_var.set(
            f"Crop: {crop['display_name']}   |   Date: {ti['date']} (day {ti['day_of_year']})   |   "
            f"Kc today: {ti['kc_today']}   |   Predicted ETc: {et['today_predicted_etc']} mm/day   |   "
            f"Season: {crop['season_label'].replace('/', ' / ')}"
        )
        self.status_var.set(
            f"Updated at T={ti['temperature_c']}\u00b0C, RH={ti['humidity_pct']}% on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self._redraw_overview_map()

    def _populate_methods(self, r):
        self.methods_tree.delete(*self.methods_tree.get_children())
        predicted = r["et"].get("today_predicted_etc")
        rows = r["et"]["all_methods"]  # already filtered to OK-only in main.py
        diffs = []
        for m in rows:
            etc = m.get("mean_etc")
            diff = abs(etc - predicted) if (etc is not None and predicted is not None) else None
            diffs.append(diff)
        min_diff = min((d for d in diffs if d is not None), default=None)
        for m, diff in zip(rows, diffs):
            tag = "closest" if (diff is not None and min_diff is not None and diff == min_diff) else ""
            name = ("\u2605 " + m["method"]) if tag else m["method"]
            self.methods_tree.insert("", "end", values=(
                name, m.get("mean_et0"), m.get("mean_etc"),
                f"{diff:.3f}" if diff is not None else "\u2013"
            ), tags=(tag,) if tag else ())

        p2 = os.path.join(FIG_DIR, "today_method_comparison.png")
        self._ov_chart2_path = p2
        self._display_image_fit(self.overview_canvas_bar, p2, "ov2")

        # refresh the per-method detail view too, if that's the currently active one
        if getattr(self, "method_selector_var", None) and self.method_selector_var.get() != "All Methods (Comparison)":
            self._populate_method_detail(self.method_selector_var.get())

    def _populate_soil(self, r):
        for w in self.soil_frame.winfo_children():
            w.destroy()
        sw = r["soil_water"]
        labels = [("field_capacity_pct", "Field Capacity (%)"), ("pwp_pct", "Permanent Wilting Point (%)"),
                  ("root_zone_depth_m", "Root Zone Depth (m)"), ("MAD", "Max. Allowable Depletion"),
                  ("TAW_mm", "Total Available Water (mm)"), ("RAW_mm", "Readily Available Water (mm)")]
        for key, label in labels:
            val = sw.get(key)
            if val is None:
                continue  # auto-remove: no placeholder for missing values
            row = tk.Frame(self.soil_frame, bg=BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label + ":", width=28, anchor="w", bg=BG,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(row, text=str(val), anchor="w", bg=BG, font=("Segoe UI", 10)).pack(side="left")

        try:
            from nacrop import soil_profile as sp
            crop_key = r["crop"]["key"]
            dwb = self.downstream["dwb"]
            today_idx = self.season.get("dap_today", -1) if self.season else -1
            today_dwb = dwb[today_idx] if dwb and -len(dwb) <= today_idx < len(dwb) else None
            zr_series = self.downstream.get("zr_series")
            zr_today = (zr_series[today_idx] if zr_series and -len(zr_series) <= today_idx < len(zr_series)
                        else None)
            kc_today = r["temperature_input"]["kc_today"]
            maturity = max(0.05, min(1.0, kc_today / 1.2)) if kc_today else 0.5
            path = sp.plot_soil_profile(
                crop_key, r["crop"]["display_name"], self.owner_entry.get().strip() or "This Farm",
                cfg.DEFAULT_SOIL, self.downstream["taw_raw"],
                storage_mm=today_dwb.storage_mm if today_dwb else None,
                depletion_mm=today_dwb.depletion_mm if today_dwb else None,
                root_zone_depth_m=zr_today, maturity=maturity,
                fname=f"soil_profile_{(self.owner_entry.get().strip() or 'farm').replace(' ', '_')}.png")
            self._soil_profile_path = path
            self._display_image_fit(self.soil_profile_canvas, path, "soil_profile")
        except Exception as e:
            print(f"[soil profile] could not generate: {e}")

    def _populate_schedule(self, r):
        rec = r["recommended_schedule"]
        area_ha = getattr(self, "area_ha", 1.0)
        mm_to_m3 = area_ha * 10  # 1 mm depth over 1 ha = 10 m3
        self.schedule_tree.delete(*self.schedule_tree.get_children())
        if rec["n_events"] == 0:
            self.schedule_summary_var.set(
                "No irrigation recommended for the entered conditions — rainfall/soil moisture meets "
                "crop demand across the growing season. (No placeholder rows shown.)")
        else:
            net_total_mm = rec["net_seasonal_irrigation_mm"]
            gross_total_mm = rec["gross_seasonal_irrigation_mm"]
            si = rec["stage_intervals_days"]
            self.schedule_summary_var.set(
                f"Interval by stage — Nursery: {si['Initial']}d, Vegetative: {si['Development']}d, "
                f"Flowering/Fruiting: {si['Mid-season']}d, Maturity: {si['Late-season']}d   |   "
                f"Events: {rec['n_events']}   |   "
                f"Net: {net_total_mm} mm ({net_total_mm * mm_to_m3:,.0f} m\u00b3 over {area_ha} ha)   |   "
                f"Gross: {gross_total_mm} mm ({gross_total_mm * mm_to_m3:,.0f} m\u00b3)   |   "
                f"\u26a0 Critical window: {rec['critical_window']}")
            for e in rec["events"]:
                net_vol = round(e["net_irrigation_mm"] * mm_to_m3, 1)
                gross_vol = round(e["gross_irrigation_mm"] * mm_to_m3, 1)
                self.schedule_tree.insert("", "end", values=(
                    e["day"], e["stage"], e["net_irrigation_mm"], e["gross_irrigation_mm"], net_vol, gross_vol))

        sched = r["schedule"]
        self.methods_water_tree.delete(*self.methods_water_tree.get_children())
        net_total_for_methods = rec.get("net_seasonal_irrigation_mm") or 0.0
        if net_total_for_methods > 0:
            from nacrop import irrigation_types as it
            for row in it.water_required_by_method(net_total_for_methods, area_ha):
                self.methods_water_tree.insert("", "end", values=(
                    row["method"], row["application_efficiency_pct"],
                    row["gross_depth_mm"], f"{row['gross_volume_m3']:,.1f}"))

    def _populate_efficiency(self, r):
        eff = r["efficiency"]
        for key, card in self.eff_cards.items():
            val = eff.get(key)
            card.set(f"{val}" if val is not None else "-")

        self.wb_text.delete("1.0", "end")
        for k, v in r["water_budget"].items():
            if v is None:
                continue
            self.wb_text.insert("end", f"{k:28s} {v}\n")

        wue = r["wue"]
        self.wue_label.pack_forget()
        if wue.get("status") == "OK":
            self.wue_var.set(f"Water Use Efficiency: {wue['WUEc_kg_per_mm_per_ha']} kg/mm/ha  ({wue['definition']})")
            self.wue_label.pack(anchor="w")
        # if not OK (e.g. no yield data), the label stays unpacked -- auto-removed, no placeholder text

    def _populate_report(self, r):
        """Fills the scrollable Report Preview tab. If LibreOffice/poppler are
        available, shows the ACTUAL generated Word document page by page (exactly as
        it will look when saved -- header, footer, formatted tables, figures, all of
        it). Otherwise falls back to a simpler dashboard-text + figures preview."""
        for widget in self.report_preview_frame.winfo_children():
            widget.destroy()
        self._report_preview_images = []

        page_images = getattr(self, "_preview_page_images", None)
        if page_images:
            tk.Label(self.report_preview_frame, text="Report Preview (exact document render)",
                     bg="white", font=("Segoe UI", 13, "bold"), fg=ACCENT_DARK, anchor="w"
                     ).pack(fill="x", padx=16, pady=(10, 2))
            tk.Label(self.report_preview_frame,
                     text=f"{len(page_images)} pages \u2014 scroll to review exactly what will be saved, "
                          f"then use the Save Farm Report tab to export.",
                     bg="white", font=("Segoe UI", 9, "italic"), fg="#777", anchor="w"
                     ).pack(fill="x", padx=16, pady=(0, 8))
            for i, img_path in enumerate(page_images):
                try:
                    if _PIL_AVAILABLE:
                        img = Image.open(img_path)
                        max_w = 850
                        if img.width > max_w:
                            ratio = max_w / img.width
                            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                    else:
                        photo = tk.PhotoImage(file=img_path)
                    self._report_preview_images.append(photo)
                    page_frame = tk.Frame(self.report_preview_frame, bg="white", relief="solid", bd=1)
                    page_frame.pack(padx=16, pady=(0, 14))
                    tk.Label(page_frame, image=photo, bg="white").pack()
                except Exception as e:
                    tk.Label(self.report_preview_frame, text=f"(could not render page {i + 1}: {e})",
                             bg="white", fg="#c94c4c", font=("Segoe UI", 8)).pack(padx=16, pady=2, anchor="w")
            return

        # --- fallback: LibreOffice/poppler not found -- simpler text + figures view ---
        pad = dict(padx=16, pady=(10, 4))
        header = tk.Label(self.report_preview_frame, text="Report Preview", bg="white",
                           font=("Segoe UI", 15, "bold"), fg=ACCENT_DARK, anchor="w")
        header.pack(fill="x", **pad)
        sub = tk.Label(self.report_preview_frame,
                        text="Install LibreOffice (free) for an exact page-by-page preview of the real "
                             "document. Showing a simpler text + figures preview instead. Everything below "
                             "reflects the current crop/inputs only.",
                        bg="white", font=("Segoe UI", 9, "italic"), fg="#777", anchor="w", justify="left",
                        wraplength=1000)
        sub.pack(fill="x", padx=16, pady=(0, 10))

        md = rpt.build_dashboard(r)
        txt = tk.Text(self.report_preview_frame, font=("Consolas", 9), bg="#f7f9f7", relief="flat",
                       height=min(40, md.count("\n") + 2), wrap="word")
        txt.insert("1.0", md)
        txt.configure(state="disabled")
        txt.pack(fill="x", padx=16, pady=(0, 12))

        # Preferred reading order for the figures that exist for this run
        preferred_order = [
            "process_diagram", "thermal_unit_regression", "today_method_comparison",
            "seasonal_et_vs_reference", "cumulative_etc", "soil_depletion", "rainfall_vs_etc",
            "efficiency_breakdown", "water_budget", "farm_map", "qgis_terrain", "qgis_comparison",
            "growth_simulation", "growth_filmstrip", "monitoring_chart",
            "panel_et_climate", "panel_soil_efficiency",
        ]
        fig_files = []
        if os.path.isdir(FIG_DIR):
            all_pngs = [f for f in os.listdir(FIG_DIR) if f.lower().endswith(".png")]
            for prefix in preferred_order:
                fig_files += sorted(f for f in all_pngs if f.startswith(prefix))
            remaining = sorted(f for f in all_pngs if f not in fig_files)
            fig_files += remaining

        if not fig_files:
            tk.Label(self.report_preview_frame, text="No figures generated yet for this run.",
                     bg="white", fg="#999", font=("Segoe UI", 9, "italic")).pack(padx=16, pady=8, anchor="w")
            return

        for fname in fig_files:
            path = os.path.join(FIG_DIR, fname)
            try:
                if _PIL_AVAILABLE:
                    img = Image.open(path)
                    max_w = 900
                    if img.width > max_w:
                        ratio = max_w / img.width
                        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                else:
                    photo = tk.PhotoImage(file=path)
                    if photo.width() > 900:
                        factor = max(1, photo.width() // 900)
                        photo = photo.subsample(factor, factor)
                self._report_preview_images.append(photo)
                cap = fname.replace("_", " ").replace(".png", "").title()
                tk.Label(self.report_preview_frame, text=cap, bg="white", font=("Segoe UI", 9, "bold"),
                         fg="#333", anchor="w").pack(fill="x", padx=16, pady=(6, 2))
                tk.Label(self.report_preview_frame, image=photo, bg="white").pack(padx=16, pady=(0, 10), anchor="w")
            except Exception as e:
                tk.Label(self.report_preview_frame, text=f"(could not preview {fname}: {e})",
                         bg="white", fg="#c94c4c", font=("Segoe UI", 8)).pack(padx=16, pady=2, anchor="w")


if __name__ == "__main__":
    app = NaCROPApp()
    app.mainloop()
