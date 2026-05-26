#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")

import os
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import textwrap

# --- WARMUP DIALOG ---
def warmup_filedialog(parent):
    # Prime the OS file dialog silently using the real app root
    try:
        filedialog.Open(parent)
    except Exception:
        pass


# --- SPLASH WINDOW ---
class Splash(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg="aliceblue")

        # Center splash
        w, h = 400, 200
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.target_val = 0
        self.current_val = 0

        tk.Label(self, text="PlotLite", font=("Segoe UI", 16, "bold"),
                 bg="aliceblue", fg="navy").grid(row=1, column=0, pady=10)

        # Custom dark blue style
        style = ttk.Style(self)
        style.configure("Blue.Horizontal.TProgressbar",
                        troughcolor="white",
                        bordercolor="lightgray",
                        background="darkblue",
                        lightcolor="darkblue",
                        darkcolor="darkblue")

        self.progress = ttk.Progressbar(self, mode="determinate",
                                        length=300, maximum=100,
                                        style="Blue.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, pady=5)

        self.percent = tk.Label(self, text="0%", bg="aliceblue")
        self.percent.grid(row=3, column=0, pady=5)
        self._update_loop()

    def _update_loop(self):
        diff = self.target_val - self.current_val
        if abs(diff) < 0.1:
            self.current_val = self.target_val
        else:
            self.current_val += diff * 0.1

        self.progress['value'] = self.current_val
        self.percent.config(text=f"{int(self.current_val)}%")
        self.after(33, self._update_loop)

    def set_target(self, value):
        self.target_val = value

# --- LOAD APP ---
class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, message="Working…"):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title("Please wait")
        self.resizable(False, False)

        ttk.Label(self, text=message).pack(padx=20, pady=(20, 10))
        self.pb = ttk.Progressbar(self, mode="indeterminate", length=250)
        self.pb.pack(padx=20, pady=(0, 20))
        self.pb.start(10)

        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def close(self):
        if hasattr(self, 'pb') and self.pb.winfo_exists():
            try:
                self.pb.stop()
            except Exception:
                pass

        self.destroy()


# --- CHOOSE TITLE FONT ---
FONT_FAMILIES = [
    "Arial", "Calibri", "Courier New", "Georgia", "Helvetica", "Times New Roman", "Verdana"
]

# --- SCROLLABLE FRAME ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="white")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        # Reset scroll region when inner frame changes size
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        for widget in (self.canvas, self.scrollable_frame):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)

    def _on_canvas_configure(self, event):
        """Syncs the inner frame width with the canvas width."""
        self.canvas.itemconfig(self.canvas_window, width=event.width - 2)

    def _on_mousewheel(self, event):
        """Universal scroll handler."""
        if event.num == 4:  
            direction = -1
        elif event.num == 5: 
            direction = 1
        elif hasattr(event, 'delta') and event.delta:
            direction = -1 if event.delta > 0 else 1
        else:
            return 

        self.canvas.yview_scroll(direction, "units")

# --- MAIN APP ---
def wrap_label(text, width=10):
    wrapper = textwrap.TextWrapper(width=width, break_long_words=False, break_on_hyphens=False)
    wrapped_text = wrapper.fill(str(text))
    return wrapped_text.replace('\n', '<br>')

class PlotApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  
        self.title("PlotLite")
        self.configure(bg="white")

        style = ttk.Style()
        style.theme_use("vista")

    def _center_window(self):
        self.update_idletasks()
        portrait_width = 630 
        req_height = self.winfo_reqheight()
        min_height = 800 
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = portrait_width
        height = min(max(req_height + 60, min_height), int(screen_height * 0.9))
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(520, 600)

    def _finish_init(self):
        self._center_window()
        self.deiconify()

        # ---- DATA AND STYLE DEFAULTS ----
        self.df            = None
        self.chart_var     = tk.StringVar(value="bar")
        self.chart_types   = ["scatter", "line", "bar", "box"]

        self.color          = "#1f77b4"
        self.whisker_color  = "#000000"
        self.outlier_color  = "#ff0000"
        self.plot_bg_color  = "#ffffff"
        self.paper_bg_color = "#ffffff"
        self.label_color    = "#000000"
        self.title_color    = "#000000"
        self.grid_color     = "#e1e1e1"
        self.vlabel_color   = "#000000"

        self.show_xgrid = tk.BooleanVar(value=True)
        self.show_ygrid = tk.BooleanVar(value=True)

        self.show_xgrid.trace_add("write", lambda *args: self._update_grid_color_visibility())
        self.show_ygrid.trace_add("write", lambda *args: self._update_grid_color_visibility())

        self.marker_size = tk.IntVar(value=10)
        self.line_width  = tk.IntVar(value=2)
        self.bar_width   = tk.DoubleVar(value=0.7)
        self.box_width   = tk.DoubleVar(value=0.2)
        self.bar_radius  = tk.IntVar(value=15)

        self.agg_var = tk.StringVar(value="Sum")
        self.agg_options = ["Count", "Mean", "Median", "Sum", "None"]

        self.label_font_family = tk.StringVar(value="Calibri")
        self.label_font_size = tk.IntVar(value=16)
        self.label_font_var = self.label_font_family
        self.label_size_var = self.label_font_size
        self.label_decimals = tk.IntVar(value=0)

        scroll_frame = ScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True)
        container = scroll_frame.scrollable_frame

        self._build_file_frame(container)
        self._build_controls_frame(container)
        self._build_title_frame(container)
        self._build_column_axis_frame(container)
        self._build_color_frame(container)
        self._build_plot_button(container)

        self.after_idle(self._on_chart_type_change)


    # --- DATA ---
    def set_dataframe(self, df):
        self.df = df
        if df is not None:
            self.all_cols = list(df.columns) 
            self.custom_sort_list = []   

            if hasattr(self, 'x_col_dropdown'):
                self.x_col_dropdown['values'] = self.all_cols
                # Reset X selection to the first column of the new file
                if self.all_cols:
                    self.x_col_var.set(self.all_cols[0])

            if hasattr(self, 'y_col_dropdown'):
                self._update_agg_visibility() 

            self._on_chart_type_change()

    def _build_file_frame(self, parent):
        frm = tk.LabelFrame(parent, text="Data", bg="aliceblue", fg="black", bd=1, relief="ridge",
                            highlightbackground="lightgray")
        frm.pack(fill="x", padx=10, pady=(10, 7))

        # Load Data button
        self.load_btn = ttk.Button(frm, text="Load Data (.csv or .xlsx)", command=self.load_data)
        self.load_btn.pack(side="left", padx=7, pady=7)

        # Label showing file status
        self.file_label = tk.Label(frm, text="No file loaded", bg="aliceblue", fg="black")
        self.file_label.pack(side="left", padx=5)

    # --- CHART SETTINGS ---
    def _build_controls_frame(self, parent):
        # Chart Settings Frame
        frm = tk.LabelFrame(parent, text="Chart Settings", bg="aliceblue", fg="black", bd=1, relief="ridge", \
                           highlightbackground="lightgray")
        frm.pack(fill="x", padx=10, pady=(10, 8))
        frm.columnconfigure(0, minsize=120, uniform="label_col") 
        frm.columnconfigure(1, weight=1)

        # Chart type
        tk.Label(frm, text="Chart Type:", bg="aliceblue", fg="black")\
            .grid(row=0, column=0, sticky="w", padx=7, pady=(6,4))
        self.chart_dropdown = ttk.Combobox(
            frm,
            textvariable=self.chart_var,
            values=self.chart_types,
            state="readonly",
            width=10
        )
        self.chart_dropdown.bind("<<ComboboxSelected>>", self._on_chart_type_change)
        self.chart_dropdown.grid(row=0, column=1, sticky="w", padx=0, pady=(6,4))
        frm.columnconfigure(1, weight=0)

        frm.columnconfigure(1, weight=0)

        # Gridline toggles
        tk.Label(frm, text="Gridlines:", bg="aliceblue", fg="black")\
            .grid(row=5, column=0, sticky="w", padx=7, pady=4)
        toggles = tk.Frame(frm, bg="aliceblue")
        toggles.grid(row=5, column=1, sticky="w", padx=0, pady=4)

        tk.Checkbutton(
            toggles,
            text="Vertical",
            variable=self.show_xgrid,
            bg="aliceblue",
            fg="black",
            activebackground="aliceblue",
            activeforeground="black",
            highlightthickness=0,
            bd=0
        ).pack(side="left", padx=(0, 10), pady=(0,3))

        tk.Checkbutton(
            toggles,
            text="Horizontal",
            variable=self.show_ygrid,
            bg="aliceblue",
            fg="black",
            activebackground="aliceblue",
            activeforeground="black",
            highlightthickness=0,
            bd=0
        ).pack(side="left", padx=5, pady=(0,3))

        # label position checkboxes
        self.vlabel_header = tk.Label(frm, text="Value Labels:", bg="aliceblue", fg="black")
        self.vlabel_header.grid(row=6, column=0, sticky="w", padx=(7,0), pady=(2,4))

        self.label_frame = tk.Frame(frm, bg="aliceblue") 
        self.label_frame.grid(row=6, column=1, sticky="w", padx=0, pady=(2,4))

        self.pos_container = tk.Frame(self.label_frame, bg="aliceblue")
        self.pos_container.pack(side="left")

        self.font_container = tk.Frame(self.label_frame, bg="aliceblue")
        self.font_container.pack(side="left")

        self.label_outside = tk.BooleanVar(value=False)
        self.label_inside = tk.BooleanVar(value=False)

        def toggle_outside():
            if self.label_outside.get():
                self.label_inside.set(False)
            self._update_label_font_visibility() 

        def toggle_inside():
            if self.label_inside.get():
                self.label_outside.set(False)
            self._update_label_font_visibility()

        self.cb_outside = tk.Checkbutton(
            self.pos_container,
            text="Outside",
            variable=self.label_outside,
            command=toggle_outside,
            bg="aliceblue", fg="black", activebackground="aliceblue",
            highlightthickness=0, bd=0
        )
        self.cb_outside.pack(side="left", padx=(0, 11))

        self.cb_inside = tk.Checkbutton(
            self.pos_container, 
            text="Inside",
            variable=self.label_inside,
            command=toggle_inside,
            bg="aliceblue", fg="black", activebackground="aliceblue",
            highlightthickness=0, bd=0
        )
        self.cb_inside.pack(side="left", padx=5)

        # Create dropdowns
        self.vlabel_font_cb = ttk.Combobox(
            self.font_container,
            textvariable=self.label_font_family,
            values=FONT_FAMILIES, 
            state="readonly", 
            width=12
        )
        self.vlabel_size_cb = ttk.Spinbox(
            self.font_container,
            textvariable=self.label_font_size,
            from_=6, to=30,
            width=7
        )

        self.decimal_label = tk.Label(self.font_container, text="Decimals:", bg="aliceblue")

        self.decimals_sb = ttk.Spinbox(
            self.font_container,
            textvariable=self.label_decimals,
            from_=0, to=5, 
            width=3
        )

        # Aggregates dropdown
        self.agg_label = tk.Label(frm, text="Aggregation:", bg="aliceblue", fg="black")
        self.agg_label.grid(row=7, column=0, sticky="w", padx=7, pady=4)
        self.agg_dropdown = ttk.Combobox(frm, textvariable=self.agg_var, values=self.agg_options, state="readonly")
        self.agg_dropdown.grid(row=7, column=1, sticky="w", padx=0, pady=4)
        self.agg_dropdown.bind("<<ComboboxSelected>>", self._on_chart_type_change)

        # Scatter controls
        self.marker_size_label = tk.Label(frm, text="Marker Size:", bg="aliceblue", fg="black")
        self.marker_size_spin = ttk.Spinbox(frm, from_=1, to=50, textvariable=self.marker_size, width=7)

        # Line controls
        self.line_width_label = tk.Label(frm, text="Line Width:", bg="aliceblue", fg="black")
        self.line_width_spin = ttk.Spinbox(frm, from_=1, to=20, textvariable=self.line_width, width=7)

        # Bar controls
        self.bar_width_label = tk.Label(frm, text="Bar Width:", bg="aliceblue", fg="black")
        self.bar_width_spin = ttk.Spinbox(frm, from_=0.1, to=1.0, increment=0.1, textvariable=self.bar_width, width=7)
        self.bar_radius_label = tk.Label(frm, text="Bar Roundness:", bg="aliceblue", fg="black")
        radius_values = [i for i in range(0, 55, 5)] 
        self.bar_radius_cb = ttk.Spinbox(
            frm, 
            textvariable=self.bar_radius, 
            values=radius_values, 
            width=7
        )

        # Box controls
        self.box_width_label = tk.Label(frm, text="Box Width:", bg="aliceblue", fg="black")
        self.box_width_spin = ttk.Spinbox(frm, from_=0.1, to=1.0, increment=0.05, textvariable=self.box_width, width=7)

        # Initial Hide
        for w in [self.marker_size_label, self.marker_size_spin, self.line_width_label, 
                  self.line_width_spin, self.bar_width_label, self.bar_width_spin, 
                  self.bar_radius_label, self.bar_radius_cb,
                  self.box_width_label, self.box_width_spin]:
            w.grid_remove()

        frm.columnconfigure(1, weight=0)


    def _update_label_font_visibility(self):
        any_label_active = self.label_inside.get() or self.label_outside.get()
        if any_label_active:
            self.vlabel_font_cb.pack(side="left", padx=(15, 5))
            self.vlabel_size_cb.pack(side="left", padx=5)
            self.decimal_label.pack(side="left", padx=(10, 2))
            self.decimals_sb.pack(side="left")
        else:
            self.vlabel_font_cb.pack_forget()
            self.vlabel_size_cb.pack_forget()
            self.decimal_label.pack_forget()
            self.decimals_sb.pack_forget()
        if hasattr(self, "vlabel_color_widgets"):
            for widget in self.vlabel_color_widgets:
                if any_label_active:
                    widget.grid()
                else:
                    widget.grid_remove()


    def _update_grid_color_visibility(self):
        show_x = self.show_xgrid.get() if hasattr(self, "show_xgrid") else True
        show_y = self.show_ygrid.get() if hasattr(self, "show_ygrid") else True

        any_grid = show_x or show_y

        if hasattr(self, "grid_widgets"):
            for widget in self.grid_widgets:
                if any_grid:
                    widget.grid()
                else:
                    widget.grid_remove()


    def _update_agg_visibility(self):
        chart = self.chart_var.get()
        agg = self.agg_var.get()

        #Boxplot logic
        if hasattr(self, 'all_cols'):
            if chart == "box":
                special_options = ["Distribution of X Column"] + self.all_cols
                self.y_col_dropdown['values'] = special_options

                # Distribution when switching to box
                if self.y_col_var.get() not in special_options or self.y_col_var.get() == "":
                    self.y_col_var.set("Distribution of X Column")
            else:
                # Remove distribution for Bar/Line/Scatter
                self.y_col_dropdown['values'] = self.all_cols
                if self.y_col_var.get() == "Distribution of X Column":
                    self.y_col_var.set(self.all_cols[0] if self.all_cols else "")

        current_y = self.y_col_var.get()
        is_single_dist_box = (chart == "box" and current_y == "Distribution of X Column")
        is_scatter = (chart == "scatter")

        #X axis order option
        if hasattr(self, 'sort_label'):
            if is_scatter or is_single_dist_box:
                self.sort_label.grid_remove()
                self.sort_dropdown.grid_remove()
                self.reorder_btn.grid_remove()
            else:
                self.sort_label.grid()
                self.sort_dropdown.grid()
                if self.sort_order_var.get() == "Custom":
                    self.reorder_btn.grid()

        # Update dropdown visibility
        if chart == "box":
            self.y_col_label.grid()
            self.y_col_dropdown.grid()
            self.y_count_static.grid_remove()
            self.agg_label.grid_remove()
            self.agg_dropdown.grid_remove()

        elif (chart in ("bar", "line") and agg == "Count"):
            self.y_col_dropdown.grid_remove()
            self.y_col_label.grid() 
            self.y_count_static.grid(row=6, column=1, sticky="w", padx=7, pady=4) 

        else:
            self.y_count_static.grid_remove()
            self.y_col_label.grid()
            self.y_col_dropdown.grid()

        if chart == "bar":
            self.agg_label.grid()
            self.agg_dropdown.grid()
            self.vlabel_header.grid()
            self.label_frame.grid()

            self.cb_outside.configure(text="Outside")
            self.cb_outside.pack(side="left", padx=(0, 8))
            self.cb_inside.pack(side="left", padx=(5, 5))

        elif chart in ("line", "scatter"):
            if chart == "line":
                self.agg_label.grid()
                self.agg_dropdown.grid()
            else: 
                self.agg_label.grid_remove()
                self.agg_dropdown.grid_remove()

            self.vlabel_header.grid()
            self.label_frame.grid()

            self.cb_outside.configure(text="Show Labels")
            self.cb_inside.pack_forget() 
            self.label_inside.set(False) 
            self.cb_outside.pack(side="left", padx=(0, 13))

        else: 
            self.agg_label.grid_remove()
            self.agg_dropdown.grid_remove()
            self.vlabel_header.grid_remove()
            self.label_frame.grid_remove()

        if chart in ("bar", "line", "scatter"):
            self.label_frame.grid() 
            self._update_label_font_visibility()
        else:
            self.vlabel_font_cb.pack_forget()
            self.vlabel_size_cb.pack_forget()

    def _on_chart_type_change(self, event=None):
        """Resets menus to show what is needed."""
        if not hasattr(self, 'marker_size_label'): return

        chart = self.chart_var.get()

        controls = [
            self.marker_size_label, self.marker_size_spin,
            self.line_width_label, self.line_width_spin,
            self.bar_width_label, self.bar_width_spin,
            self.bar_radius_label, self.bar_radius_cb,
            self.box_width_label, self.box_width_spin
        ]
        for w in controls: w.grid_remove()

        if hasattr(self, "vlabel_color_widgets"):
            for widget in self.vlabel_color_widgets:
                widget.grid_remove()

        color_widgets = []
        if hasattr(self, 'whisker_widgets'): color_widgets.extend(self.whisker_widgets)
        if hasattr(self, 'outlier_widgets'): color_widgets.extend(self.outlier_widgets)
        if hasattr(self, 'bar_color_widgets'): color_widgets.extend(self.bar_color_widgets)

        for w in color_widgets: w.grid_remove()

        if chart == "scatter":
            self.marker_size_label.grid(row=10, column=0, sticky="w", padx=(7,0), pady=4)
            self.marker_size_spin.grid(row=10, column=1, sticky="w", padx=0, pady=4)

        elif chart == "line":
            self.line_width_label.grid(row=10, column=0, sticky="w", padx=(7,0), pady=4)
            self.line_width_spin.grid(row=10, column=1, sticky="w", padx=0, pady=4)

        elif chart == "bar":
            self.bar_width_label.grid(row=10, column=0, sticky="w", padx=(7,0), pady=4)
            self.bar_width_spin.grid(row=10, column=1, sticky="w", padx=0, pady=4)
            self.bar_radius_label.grid(row=11, column=0, sticky="w", padx=(7,0), pady=4)
            self.bar_radius_cb.grid(row=11, column=1, sticky="w", padx=0, pady=4)

            if hasattr(self, 'bar_color_widgets'):
                self.trace_scale_cb.grid(row=0, column=3, padx=(10, 5), sticky="w")
                self.inline_preview.grid(row=0, column=4, sticky="w")

        elif chart == "box":
            self.box_width_label.grid(row=10, column=0, sticky="w", padx=(7,0), pady=4)
            self.box_width_spin.grid(row=10, column=1, sticky="w", padx=0, pady=4)

            if hasattr(self, 'whisker_widgets'):
                for w in self.whisker_widgets: w.grid()
            if hasattr(self, 'outlier_widgets'):
                for w in self.outlier_widgets: w.grid()

        # Refresh settings
        self._update_agg_visibility() 
        self._update_grid_color_visibility() 
        self.update_idletasks()

    # --- TITLE SETTINGS ---
    def _build_title_frame(self, parent):
        frm_title = tk.LabelFrame(
            parent,
            text="Title Settings",
            bg="aliceblue",
            fg="black",
            bd=1,
            relief="ridge",
            highlightbackground="lightgray"
        )
        frm_title.pack(fill="x", padx=10, pady=(5, 10))
        frm_title.columnconfigure(1, weight=1)

        tk.Label(frm_title, text="Chart Title:", bg="aliceblue", fg="black")\
            .grid(row=0, column=0, sticky="w", padx=7, pady=4)

        title_entry_subfrm = tk.Frame(frm_title, bg="aliceblue")
        title_entry_subfrm.grid(row=0, column=1, sticky="w", padx=15, pady=4)

        self.title_entry = tk.Entry(title_entry_subfrm, bg="white", width=50) 
        self.title_entry.insert(0, "My Plot")
        self.title_entry.pack(side="left", padx=(0, 5))

        self.bold_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            title_entry_subfrm,
            text="Bold Title",
            variable=self.bold_var,
            bg="aliceblue",
            fg="black",
            activebackground="aliceblue",
            activeforeground="black",
            highlightthickness=0,
            bd=0
        ).pack(side="left")

        tk.Label(frm_title, text="Title Font:", bg="aliceblue", fg="black")\
            .grid(row=1, column=0, sticky="w", padx=7, pady=4)

        #self.font_family = tk.StringVar(value=FONT_FAMILIES[0])
        self.font_family = tk.StringVar(value="Calibri")
        ttk.Combobox(frm_title, textvariable=self.font_family,
                     values=FONT_FAMILIES, state="readonly", width=25)\
            .grid(row=1, column=1, sticky="w", padx=15, pady=4)

        tk.Label(frm_title, text="Title Font Size:", bg="aliceblue", fg="black")\
            .grid(row=2, column=0, sticky="w", padx=7, pady=4)

        self.font_size = tk.IntVar(value=20)
        ttk.Spinbox(frm_title, from_=8, to=72, textvariable=self.font_size, width=7)\
            .grid(row=2, column=1, sticky="w", padx=15)

        tk.Label(frm_title, text="Title Alignment:", bg="aliceblue", fg="black")\
            .grid(row=3, column=0, sticky="w", padx=7, pady=4)

        align_subfrm = tk.Frame(frm_title, bg="aliceblue")
        align_subfrm.grid(row=3, column=1, sticky="w", padx=11, pady=4)

        self.align_var = tk.StringVar(value="center")
        for txt, val in [("Left", "left"), ("Center", "center"), ("Right", "right")]:
            tk.Radiobutton(
                align_subfrm, 
                text=txt,
                variable=self.align_var,
                value=val,
                bg="aliceblue",
                fg="black",
                activebackground="aliceblue",
                activeforeground="black",
                highlightthickness=0,
                bd=0
            ).pack(side="left", padx=4)

        frm_title.columnconfigure(1, weight=1)

    # --- COLUMN AND AXIS SETTINGS ---
    def _build_column_axis_frame(self, parent):
        self.custom_sort_list = []

        frm_cols = tk.LabelFrame(
            parent,
            text="Column and Axis Settings",
            bg="aliceblue",
            fg="black",
            bd=1,
            relief="ridge",
            highlightbackground="lightgray"
        )
        frm_cols.pack(fill="x", padx=10, pady=(5, 10))
        frm_cols.columnconfigure(1, weight=1)
        frm_cols.columnconfigure(4, weight=1)

        # Select x column
        self.x_col_var = tk.StringVar()
        self.x_col_label = tk.Label(frm_cols, text="X Column:", bg="aliceblue", fg="black")
        self.x_col_label.grid(row=0, column=0, sticky="w", padx=7, pady=7)
        self.x_col_dropdown = ttk.Combobox(frm_cols, textvariable=self.x_col_var, state="readonly")
        self.x_col_dropdown.grid(row=0, column=1, sticky="ew", padx=11, pady=4)
        self.x_col_dropdown.bind("<<ComboboxSelected>>", self._on_x_col_change)

        # X axis label
        tk.Label(frm_cols, text="X-Axis Label:", bg="aliceblue", fg="black")\
            .grid(row=1, column=0, sticky="w", padx=7, pady=4)
        self.xaxis_entry = tk.Entry(frm_cols, bg="white", fg="black", insertbackground="black")
        self.xaxis_entry.insert(0, "X Value")
        self.xaxis_entry.grid(row=1, column=1, sticky="ew", padx=11, pady=4)

        # X axis font
        font_choices = ["Arial","Calibri","Courier New","Georgia",
                        "Helvetica","Times New Roman","Verdana"]
        self.xaxis_font_label = tk.Label(frm_cols, text="X-Axis Font:", bg="aliceblue", fg="black")
        self.xaxis_font = tk.StringVar(value=font_choices[0])
        self.xaxis_font_cb = ttk.Combobox(
            frm_cols, textvariable=self.xaxis_font,
            values=font_choices, state="readonly", style="Custom.TCombobox"
        )
        self.xaxis_font_cb.set("Calibri")
        self.xaxis_font_label.grid(row=2, column=0, sticky="w", padx=7, pady=4)
        self.xaxis_font_cb.grid(row=2, column=1, sticky="w", padx=11, pady=4)

        # X axis font size
        size_choices = list(range(8, 25))
        self.xaxis_fs_label = tk.Label(frm_cols, text="X-Axis Font Size:", bg="aliceblue", fg="black")
        self.xaxis_fontsize = tk.IntVar(value=12)
        self.xaxis_fs_cb = ttk.Spinbox(
            frm_cols,
            from_=8, 
            to=72, 
            textvariable=self.xaxis_fontsize,
            width=7
        )

        self.xaxis_fs_cb.set("16")
        self.xaxis_fs_label.grid(row=3, column=0, sticky="w", padx=7, pady=4)
        self.xaxis_fs_cb.grid(row=3, column=1, sticky="w", padx=11, pady=4)

        # X-Axis Sort Order
        self.sort_label = tk.Label(frm_cols, text="X-Axis Order:", bg="aliceblue", fg="black") 
        self.sort_label.grid(row=4, column=0, sticky="w", padx=7, pady=4)

        self.sort_order_var = tk.StringVar(value="Alphabetical")
        self.sort_dropdown = ttk.Combobox(
            frm_cols, 
            textvariable=self.sort_order_var, 
            values=["Alphabetical", "Y-Value (Ascending)", "Y-Value (Descending)", "Custom"],
            state="readonly"
        )
        self.sort_dropdown.grid(row=4, column=1, sticky="ew", padx=11, pady=4)

        self.reorder_btn = ttk.Button(frm_cols, text="Arrange Categories", command=self._open_reorder_window)

        # Show or hide custom order button
        def toggle_reorder_btn(*args):
            if self.sort_order_var.get() == "Custom":
                self.reorder_btn.grid(row=4, column=2, padx=5)
            else:
                self.reorder_btn.grid_remove()

        self.sort_order_var.trace_add("write", toggle_reorder_btn)

        # Separate X and Y settings
        ttk.Separator(frm_cols, orient='horizontal').grid(row=5, column=0, columnspan=5, sticky="ew", padx=10, pady=10)

        # Select y column
        self.y_col_var = tk.StringVar()
        self.y_col_label = tk.Label(frm_cols, text="Y Column:", bg="aliceblue", fg="black")
        self.y_col_dropdown = ttk.Combobox(
            frm_cols, textvariable=self.y_col_var, state="readonly", style="Custom.TCombobox"
        )
        self.y_col_label.grid(row=6, column=0, sticky="w", padx=5, pady=4)
        self.y_col_dropdown.grid(row=6, column=1, sticky="ew", padx=11, pady=4)

        self.y_col_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_agg_visibility())

        # Static count
        self.y_count_static = tk.Label(frm_cols, text="Count", bg="aliceblue", fg="black", font=("Segoe UI", 9))

        # Y axis label
        self.yaxis_label = tk.Label(frm_cols, text="Y-Axis Label:", bg="aliceblue", fg="black")
        self.yaxis_entry = tk.Entry(frm_cols, bg="white", fg="black", insertbackground="black")
        self.yaxis_entry.insert(0, "Y Value")
        self.yaxis_label.grid(row=7, column=0, sticky="w", padx=7, pady=4)
        self.yaxis_entry.grid(row=7, column=1, sticky="ew", padx=11, pady=4)

        # Y axis font
        self.yaxis_font_label = tk.Label(frm_cols, text="Y-Axis Font:", bg="aliceblue", fg="black")
        self.yaxis_font = tk.StringVar(value=font_choices[0])
        self.yaxis_font_cb = ttk.Combobox(
            frm_cols, textvariable=self.yaxis_font,
            values=font_choices, state="readonly", style="Custom.TCombobox"
        )
        self.yaxis_font_cb.set("Calibri")
        self.yaxis_font_label.grid(row=8, column=0, sticky="w", padx=7, pady=4)
        self.yaxis_font_cb.grid(row=8, column=1, sticky="w", padx=11, pady=4)

        # Y axis font size
        self.yaxis_fs_label = tk.Label(frm_cols, text="Y-Axis Font Size:", bg="aliceblue", fg="black")
        self.yaxis_fontsize = tk.IntVar(value=16)
        self.yaxis_fs_cb = ttk.Spinbox(
            frm_cols, 
            from_=8, 
            to=72, 
            textvariable=self.yaxis_fontsize, 
            width=7  
        )
        self.yaxis_fs_label.grid(row=9, column=0, sticky="w", padx=(7, 10), pady=6)
        self.yaxis_fs_cb.grid(row=9, column=1, sticky="w", padx=11, pady=6)

        frm_cols.columnconfigure(1, weight=1)

    def _on_x_col_change(self, event=None):
        """Wipe the custom sort cache when the user picks a different column."""
        self.custom_sort_list = []
        if hasattr(self, '_update_agg_visibility'):
            self._update_agg_visibility()

    def _open_reorder_window(self):
        import pandas as pd 

        if self.df is None or not self.x_col_var.get():
            messagebox.showwarning("Warning", "Please load data and select an X column first.")
            return

        x_col = self.x_col_var.get()
        current_items = [str(i) for i in self.df[x_col].unique() if pd.notna(i)]

        if not self.custom_sort_list or set(self.custom_sort_list) != set(current_items):
            self.custom_sort_list = sorted(current_items)

        win = tk.Toplevel(self)
        win.title("Arrange Axis Order")
        win.geometry("340x450")
        win.grab_set()

        lbl_instr = tk.Label(win, text="Select an item and move it to change scale order:", wraplength=300)
        lbl_instr.pack(pady=5)

        lb = tk.Listbox(win, selectmode="single", font=("Segoe UI", 10))
        lb.pack(fill="both", expand=True, padx=20, pady=10)

        for item in self.custom_sort_list:
            lb.insert("end", item)

        def move_up():
            idx = lb.curselection()
            if not idx or idx[0] == 0: return
            text = lb.get(idx)
            lb.delete(idx)
            lb.insert(idx[0] - 1, text)
            lb.selection_set(idx[0] - 1)

        def move_down():
            idx = lb.curselection()
            if not idx or idx[0] == lb.size() - 1: return
            text = lb.get(idx)
            lb.delete(idx)
            lb.insert(idx[0] + 1, text)
            lb.selection_set(idx[0] + 1)

        def save_order():
            self.custom_sort_list = list(lb.get(0, "end"))
            win.destroy()

        btn_frm = tk.Frame(win)
        btn_frm.pack(fill="x", pady=10)
        ttk.Button(btn_frm, text="↑ Move Up", command=move_up).pack(side="left", expand=True, padx=5)
        ttk.Button(btn_frm, text="↓ Move Down", command=move_down).pack(side="left", expand=True, padx=5)

        ttk.Button(win, text="Apply", command=save_order).pack(fill="x", padx=20, pady=(0, 20))


    # --- COLOR SETTINGS ---
    def _generate_gradient(self, hex_color, steps=6):
        import colorsys
        hex_color = (hex_color or "#000000").lstrip("#")
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
        except Exception:
            r, g, b = (31/255.0, 119/255.0, 180/255.0) 
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        colors = []
        for i in range(steps):
            new_l = 0.92 - i * (0.6 / max(1, steps - 1))
            r2, g2, b2 = colorsys.hls_to_rgb(h, new_l, s)
            colors.append('#%02x%02x%02x' % (int(r2 * 255), int(g2 * 255), int(b2 * 255)))
        return colors

    def _update_trace_scale_from_color(self, *args):
        if not hasattr(self, "trace_widgets"):
            return

        trace_color = self.trace_widgets[1].cget("background")

        use_scale_var = getattr(self, "use_trace_scale", None)
        use_scale = use_scale_var.get() if use_scale_var is not None else False

        if use_scale:
            self.selected_trace_colors = self._generate_gradient(trace_color, steps=6)
        else:
            self.selected_trace_colors = [trace_color]

        # Update color scale preview
        if hasattr(self, "scale_preview"):
            for w in self.scale_preview.winfo_children():
                w.destroy()

            if use_scale:
                for color in self.selected_trace_colors:
                    sw = tk.Label(self.scale_preview, bg=color, width=2, height=1, relief="ridge", bd=1)
                    sw.pack(side="left", padx=1)

                if self.chart_var.get() == "bar":
                    self.scale_preview.grid(row=0, column=4, padx=(5, 0), sticky="w")
            else:
                # Hide preview if scale is turned off
                self.scale_preview.grid_remove()

    def _build_color_frame(self, parent):
        frm = tk.LabelFrame(parent, text="Color Settings", bg="aliceblue", fg="black", bd=1, relief="ridge", \
                           highlightbackground="lightgray")
        frm.pack(fill="x", padx=10, pady=11)

        frm.columnconfigure(3, weight=0) 
        frm.columnconfigure(4, weight=1)

        def add_picker(container, row, label, initial, handler):
            lbl = tk.Label(container, text=label, bg="aliceblue", fg="black")
            lbl.grid(row=row, column=0, sticky="w", padx=7, pady=4)
            sw = tk.Label(container, bg=initial, width=3, relief="groove", bd=1)
            sw.grid(row=row, column=1, padx=5)
            btn = ttk.Button(container, text="Choose", command=lambda: handler(sw))
            btn.grid(row=row, column=2, padx=7)
            return (lbl, sw, btn)

        # Trace Color 
        self.trace_widgets = add_picker(frm, 0, "Trace Color:", self.color, self._pick_trace_color)

        # Scale
        self.use_trace_scale = tk.BooleanVar(value=False)
        self.trace_scale_cb = tk.Checkbutton(
            frm, text="Color Scale", variable=self.use_trace_scale,
            command=self._update_trace_scale_from_color, bg="aliceblue", fg="black",
            activebackground="aliceblue", highlightthickness=0, bd=0
        )

        self.trace_scale_cb.grid(row=0, column=3, padx=(10, 5), sticky="w")
        self.inline_preview = tk.Frame(frm, bg="aliceblue") 
        self.scale_preview = self.inline_preview
        self.bar_color_widgets = [self.trace_scale_cb, self.inline_preview]

        # Other color pickers
        self.whisker_widgets = add_picker(frm, 1, "Whiskers:", self.whisker_color, self._pick_whisker_color)
        self.outlier_widgets = add_picker(frm, 2, "Outliers:", self.outlier_color, self._pick_outlier_color)
        self.plot_swatch  = add_picker(frm, 3, "Plot Background:", self.plot_bg_color, self._pick_plot_bg_color)
        self.paper_swatch = add_picker(frm, 4, "Paper Background:", self.paper_bg_color, self._pick_paper_bg_color)
        self.label_swatch = add_picker(frm, 5, "Axis Labels:", self.label_color, self._pick_label_color)
        self.title_swatch = add_picker(frm, 6, "Title Color:", self.title_color, self._pick_title_color)
        self.grid_widgets = add_picker(frm, 7, "Grid Lines:", self.grid_color, self._pick_grid_color)
        self.vlabel_color_widgets = add_picker(frm, 8, "Value Labels:", self.vlabel_color, self._pick_vlabel_color)

        # Hide unneeded color options until selected
        for w in self.whisker_widgets: w.grid_remove()
        for w in self.outlier_widgets: w.grid_remove()
        self.trace_scale_cb.grid_remove()
        self.inline_preview.grid_remove()
        for w in self.vlabel_color_widgets: w.grid_remove()

        self.selected_trace_colors = [self.color]
        self._update_trace_scale_from_color()
        self._update_grid_color_visibility()

   # --- PLOT BUTTON ---
    def _build_plot_button(self, parent):
        self.plot_btn = tk.Button(
            parent, 
            text="Plot!", 
            command=self.plot_data,
            bg="aliceblue",            
            fg="black",               
            activebackground="#d0e4f5", 
            font=("Segoe UI", 9), 
            relief="ridge",          
            bd=2,                    
            padx=10,                   
            pady=5                     
        )
        self.plot_btn.pack(pady=12)


    # --- BUILD THE PLOT ---
    def load_data(self):
        self._open_file_dialog()

    def _open_file_dialog(self):
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx;*.xls")]
        )

        if not path:
            self.file_label.config(text="No file selected")
            return

        self._process_file(path)

    def _process_file(self, path):
        self.file_label.config(text="Loading data…")

        def worker():
            import pandas as pd, openpyxl
            try:
                if path.lower().endswith(".csv"):
                    df = pd.read_csv(path)
                elif path.lower().endswith((".xlsx", ".xls")):
                    df = pd.read_excel(path)
                else:
                    raise ValueError("Unsupported file type")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Load Error", str(e)))
                return

            self.after(0, lambda: self._update_ui(df, path))

        threading.Thread(target=worker, daemon=True).start()


    def _update_ui(self, df, path):
        self.set_dataframe(df)
        self.all_cols = list(df.columns) 

        # --- Update Y Dropdown logic ---
        chart = self.chart_var.get()
        if chart == "box":
            self.y_col_dropdown['values'] = ["Distribution of X Column"] + self.all_cols
            self.y_col_var.set("Distribution of X Column")
        else:
            self.y_col_dropdown['values'] = self.all_cols

        self.x_col_dropdown['values'] = self.all_cols
        self.file_label.config(text=f"Loaded: {os.path.basename(path)}")
        self._on_chart_type_change()

    # Color picker callbacks
    def _pick_trace_color(self, sw):
        c = colorchooser.askcolor(title="Trace Color", initialcolor=self.color)[1]
        if c:
            self.color = c
            sw.configure(background=c)
            if hasattr(self, "_update_trace_scale_from_color"):
                self._update_trace_scale_from_color()

    def _pick_whisker_color(self, sw):
        c = colorchooser.askcolor(title="Whisker Color", initialcolor=self.whisker_color)[1]
        if c:
            self.whisker_color = c
            sw.configure(background=c)

    def _pick_outlier_color(self, sw):
        c = colorchooser.askcolor(title="Outlier Color", initialcolor=self.outlier_color)[1]
        if c:
            self.outlier_color = c
            sw.configure(background=c)


    def _pick_plot_bg_color(self, sw):
        c = colorchooser.askcolor(title="Plot Background", initialcolor=self.plot_bg_color)[1]
        if c:
            self.plot_bg_color = c
            sw.configure(background=c)

    def _pick_paper_bg_color(self, sw):
        c = colorchooser.askcolor(title="Paper Background", initialcolor=self.paper_bg_color)[1]
        if c:
            self.paper_bg_color = c
            sw.configure(background=c)

    def _pick_label_color(self, sw):
        c = colorchooser.askcolor(title="Axis Labels", initialcolor=self.label_color)[1]
        if c:
            self.label_color = c
            sw.configure(background=c)

    def _pick_title_color(self, sw):
        c = colorchooser.askcolor(title="Title Color", initialcolor=self.title_color)[1]
        if c:
            self.title_color = c
            sw.configure(background=c)

    def _pick_grid_color(self, sw):
        c = colorchooser.askcolor(title="Grid Lines", initialcolor=self.grid_color)[1]
        if c:
            self.grid_color = c
            sw.configure(background=c)

    def _pick_vlabel_color(self, sw):
        c = colorchooser.askcolor(title="Value Label Color", initialcolor=self.vlabel_color)[1]
        if c:
            self.vlabel_color = c
            sw.configure(background=c)

    def plot_data(self):
        if self.df is None:
            print(">>> no DataFrame")
            messagebox.showwarning("No Data", "Load a .csv, .xlsx, or .xls file.")
            return

        # Collect settings
        x_col = self.x_col_var.get()
        y_col = self.y_col_var.get()
        agg_mode = self.agg_var.get()

        if not x_col:
            messagebox.showerror("Missing Selection", "Please select an X column before plotting.")
            return

        if agg_mode != "Count" and not y_col:
            messagebox.showerror("Missing Selection", "Please select a Y column before plotting.")
            return

        title_txt  = self.title_entry.get()
        if self.bold_var.get():
            title_txt = f"<b>{title_txt}</b>"

        font_family = self.font_family.get()
        font_size   = self.font_size.get()
        x_f_family = self.xaxis_font.get()
        x_f_size = self.xaxis_fontsize.get()
        y_f_family = self.yaxis_font.get()
        y_f_size = self.yaxis_fontsize.get()
        align_map   = {"left": 0.025, "center": 0.5, "right": 0.975}
        title_align = align_map[self.align_var.get()]

        xlab       = self.xaxis_entry.get()
        ylab       = self.yaxis_entry.get()
        chart      = self.chart_var.get()

        show_vert  = self.show_xgrid.get()
        show_horiz = self.show_ygrid.get()

        msize      = self.marker_size.get()
        lwidth     = self.line_width.get()
        bwidth     = self.bar_width.get()

        dlg = ProgressDialog(self, message="Building chart…")

        def worker():
            import plotly.express as px
            import pandas as pd

            try:
                decimals = self.label_decimals.get()

                chart = self.chart_var.get()
                y_val = self.y_col_var.get()
                agg_mode = self.agg_var.get()
                label_inside = self.label_inside.get()
                label_outside = self.label_outside.get()

                v_font_family = self.label_font_family.get()
                v_font_size = self.label_font_size.get()

                # Axis font
                f_family = self.font_family.get()
                f_size = self.font_size.get()
                l_color = self.label_color

                # Preprocess data
                plot_df = self.df.copy()
                y_to_plot = y_col

                # Status flags for logic branching
                is_scatter = (chart == "scatter")
                is_special_box = (chart == "box" and y_to_plot == "Distribution of X Column")

                # Determine text position
                if chart in ("scatter", "line"):
                    textpos = "top center" if label_outside else None
                elif chart == "bar":
                    textpos = "inside" if label_inside else ("outside" if label_outside else None)
                else:
                    textpos = None

                # Aggregation
                if chart in ("line", "bar") and agg_mode != "None":
                    if agg_mode == "Count":
                        plot_df = plot_df.groupby(x_col).size().reset_index(name='Count')
                        y_to_plot = 'Count'
                    else:
                        method = agg_mode.lower()
                        plot_df = plot_df.groupby(x_col)[[y_col]].agg(method).reset_index()
                        y_to_plot = y_col
                    plot_df = plot_df.sort_values(by=x_col)

                # X axis sorting logic
                sort_mode = self.sort_order_var.get()

                if is_scatter or is_special_box:
                    final_category_order = None
                else:
                    if sort_mode == "Alphabetical":
                        plot_df = plot_df.sort_values(by=x_col, ascending=True)
                    elif sort_mode == "Y-Value (Ascending)":
                        plot_df = plot_df.sort_values(by=y_to_plot, ascending=True)
                    elif sort_mode == "Y-Value (Descending)":
                        plot_df = plot_df.sort_values(by=y_to_plot, ascending=False)
                    elif sort_mode == "Custom" and self.custom_sort_list:
                        # Force the column to be a categorical type with custom order
                        plot_df[x_col] = pd.Categorical(plot_df[x_col].astype(str), categories=self.custom_sort_list, ordered=True)
                        plot_df = plot_df.sort_values(by=x_col)

                    # Ensure X is string for Plotly discrete axis
                    plot_df[x_col] = plot_df[x_col].astype(str)
                    # Capture the categorical order
                    final_category_order = plot_df[x_col].unique().tolist()

                #Wrap long labels
                if y_to_plot in plot_df.columns:
                    plot_df['label_text'] = plot_df[y_to_plot].apply(
                        lambda x: wrap_label(f"{float(x):.{decimals}f}", width=25)
                    )
                else:
                    plot_df['label_text'] = ""

                x_ticks = plot_df[x_col].unique()
                x_tick_labels = [wrap_label(str(v), width=25) for v in x_ticks]


                # Build the plot
                v_label_style = dict(
                    family=self.label_font_family.get(),
                    size=self.label_font_size.get(),
                    color=self.vlabel_color 
                )

                if chart == "scatter":
                    fig = px.scatter(plot_df, x=x_col, y=y_to_plot, color_discrete_sequence=[self.color])
                    fig.update_traces(mode="markers+text" if textpos else "markers",
                                      marker_size=msize, text=plot_df['label_text'] if textpos else None,
                                      texttemplate="%{text}", textposition=textpos, textfont=v_label_style)

                elif chart == "line":
                    fig = px.line(plot_df, x=x_col, y=y_to_plot, color_discrete_sequence=[self.color])
                    fig.update_traces(mode="lines+markers+text" if textpos else "lines+markers",
                                      line_width=lwidth, text=plot_df['label_text'] if textpos else None,
                                      texttemplate="%{text}", textposition=textpos, textfont=v_label_style)

                elif chart == "bar":
                    fig = px.bar(plot_df, x=x_col, y=y_to_plot)
                    radius_str = f"{self.bar_radius.get()}%"

                    if self.use_trace_scale.get():
                        grad = self.selected_trace_colors
                        plotly_scale = [[i / (max(1, len(grad) - 1)), c] for i, c in enumerate(grad)]

                        vals = plot_df[y_to_plot]
                        v_min, v_max = vals.min(), vals.max()
                        #prevents lowest frequency bar from looking washed out
                        buffer = (v_max - v_min) * 0.15 if v_max != v_min else 0.1
                        cmin = v_min - buffer

                        # Map the Y values to the color scale
                        fig.update_traces(marker=dict(
                            color=plot_df[y_to_plot], 
                            colorscale=plotly_scale, 
                            showscale=False,
                            cornerradius=radius_str,
                            cmin=cmin,
                            cmax=v_max
                        ))
                    else:
                        # If scale is off, use selected trace color
                        fig.update_traces(marker_color=self.color,
                        marker_cornerradius=radius_str
                         )

                    trace_update = {
                        "width": bwidth,
                        "textposition": textpos,
                        "textfont": v_label_style
                    }

                    if textpos:
                        trace_update["text"] = plot_df['label_text']
                        trace_update["texttemplate"] = "%{text}"

                    fig.update_traces(**trace_update)


                elif chart == "box":
                    #For single distribution of x
                    if is_special_box:
                        user_x_label = self.xaxis_entry.get() if self.xaxis_entry.get() else "Distribution"
                        fig = px.box(self.df, y=x_col, x=[user_x_label] * len(self.df), 
                                     color_discrete_sequence=[self.color])
                        fig.update_xaxes(range=[-1, 1], showticklabels=False, title_text=user_x_label)
                        fig.update_traces(width=0.3)
                    else:
                        fig = px.box(self.df, x=x_col, y=y_val, color_discrete_sequence=[self.color])
                        fig.update_xaxes(title_text=None)
                        fig.update_xaxes(showticklabels=True)

                    fig.update_traces(
                        width=self.box_width.get(), 
                        fillcolor=self.color,
                        line=dict(color=self.whisker_color),
                        marker=dict(outliercolor=self.outlier_color, color=self.outlier_color)
                    )

                final_y_range = None
                fig.update_yaxes(autorange=True)

                fig.update_layout(
                    width=750,
                    height=450,
                    paper_bgcolor=self.paper_bg_color,
                    plot_bgcolor=self.plot_bg_color,
                    margin=dict(t=80, l=60, r=40, b=80), 

                    # Main title
                    title=dict(
                        text=title_txt, 
                        x=title_align, 
                        font=dict(
                            family=font_family, 
                            size=font_size, 
                            color=self.title_color
                        )
                    ),

                    # X axis
                    xaxis=dict(
                        title=dict(text=self.xaxis_entry.get(), font=dict(family=x_f_family, size=x_f_size, color=self.label_color)),
                        tickfont=dict(family=x_f_family, size=x_f_size, color=self.label_color),
                        gridcolor=self.grid_color,
                        showgrid=show_vert, 
                        tickvals=x_ticks,
                        ticktext=x_tick_labels,
                        # Order X axis
                        categoryorder='array' if final_category_order else None,
                        categoryarray=final_category_order if final_category_order else None
                    ),

                    # Y axis
                    yaxis=dict(
                        title=dict(text=self.yaxis_entry.get(), font=dict(family=y_f_family, size=y_f_size, color=self.label_color)),
                        tickfont=dict(family=y_f_family, size=y_f_size, color=self.label_color),
                        gridcolor=self.grid_color, 
                        showgrid=show_horiz, 
                        range=final_y_range
                    )
                )
                self.after(0, lambda: (fig.show(renderer="browser"), dlg.close()))

            except Exception as e:
                print(f"Plotting Error: {e}") # Log for debugging
                self.after(0, lambda e=e: [dlg.close(), messagebox.showerror("Plotting Error", f"An error occurred: {str(e)}")])
                return 

            self.after(0, dlg.close)

        threading.Thread(target=worker, daemon=True).start()

# --- WARMUP HELPER ---
def warmup_filedialog(parent):
    try:
        filedialog.Open(parent)
    except Exception:
        pass

# --- LIBRARY PRELOAD ---
def preload_libs():
    import pandas, openpyxl, colorsys, textwrap, plotly.express

# --- STARTUP SEQUENCE ---
if __name__ == "__main__":
    app = PlotApp()

    splash = Splash(app)
    splash.set_target(10)

    #Two startup tasks, warmup, and library preload
    startup_tasks = 2
    state = {"completed": 0}
    lock = threading.Lock()

    def task_done(next_target):
        with lock:
            state["completed"] += 1
            splash.set_target(next_target)
            done = state["completed"] == startup_tasks

        if done:
            splash.set_target(100)
            splash.after(1000, finish_startup)

    def finish_startup():
        splash.destroy()
        app._finish_init() 

    def run_preload_libs():
        preload_libs()
        splash.after(0, lambda: task_done(90))

    def run_warmup_logic():
        splash.after(0, lambda: task_done(50))

    threading.Thread(target=run_warmup_logic, daemon=True).start()
    threading.Thread(target=run_preload_libs, daemon=True).start()

    app.mainloop()


# In[ ]:




