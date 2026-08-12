"""
Cabal Online - Damage Optimizer
-------------------------------------------
A CustomTkinter-based GUI desktop application designed to calculate, simulate, 
and optimize player damage, stats efficiency, item comparisons, and battle mode 
buffs for Cabal Online.

License: MIT
"""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as cctk

# ==========================================
# APPEARANCE & COLOR PALETTE CONFIGURATION
# ==========================================
cctk.set_appearance_mode("dark")
cctk.set_default_color_theme("blue")

COLOR_AMP = "#B794F4"
COLOR_CRIT = "#F6AD55"
COLOR_DEF = "#63B3ED"
COLOR_ATK = "#D69E2E"
COLOR_BG_CARD = "#1E1E24"
COLOR_BG_DARK = "#121214"
COLOR_TITLE_P = "#4FD1C5"
COLOR_TITLE_M = "#FC8181"

# ==========================================
# PRESETS & CONSTANTS
# ==========================================
BOSS_PRESETS = {
    "Custom": {"defense": 0, "ign_perf": 0, "res_amp": 0, "res_crit": 0, "reduction": 0},
    "Common Monster (Map)": {"defense": 1200, "ign_perf": 100, "res_amp": 20, "res_crit": 30, "reduction": 150},
    "Boss - Hazardous Valley": {"defense": 3500, "ign_perf": 450, "res_amp": 60, "res_crit": 80, "reduction": 500},
    "Boss - Forgotten Temple B2F": {"defense": 4800, "ign_perf": 700, "res_amp": 90, "res_crit": 110, "reduction": 800},
    "Boss - Illusion Castle B3F": {"defense": 6500, "ign_perf": 1100, "res_amp": 130, "res_crit": 150, "reduction": 1200},
}

BM_DEFAULT_VALUES = {
    "Aura": {"attack": 100, "amp": 10, "crit_damage": 20, "crit_rate": 15, "penetration": 50},
    "BM2": {"attack": 250, "amp": 15, "crit_damage": 30, "crit_rate": 0, "penetration": 100},
    "BM3": {"attack": 400, "amp": 25, "crit_damage": 50, "crit_rate": 0, "penetration": 200}
}

TOOLTIPS = {
    "Attack (Physical/Magic)": "Primary damage base of the character.",
    "Skill Amp %": "Percentage multiplier applied directly to base attack.",
    "Critical Damage %": "Extra damage bonus applied on critical hits.",
    "Penetration": "Ignores a portion of the target's defense.",
    "Critical Rate %": "Percentage chance to land a critical hit.",
    "Max Critical Rate %": "Maximum allowed limit for Critical Rate.",
    "Ignore Damage Reduction": "Directly negates static damage reduction.",
    "Ignore Res. Crit Damage": "Negates target's Critical Damage Resistance.",
    "Ignore Res. Skill Amp": "Negates target's Skill Amp Resistance.",
    "Cancel Ignore Penetration": "Negates target's Ignore Penetration stat."
}


class ToolTip:
    """Helper class to create hover tooltips for UI elements."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background="#2D3748", foreground="#FFF",
            relief="solid", borderwidth=1,
            font=("Arial", 9, "normal"), padx=8, pady=5
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


def calculate_cabal_damage(player, monster):
    """Core calculation engine for damage simulation."""
    effective_ign_perf = max(0, monster['ign_perf'] - player.get('canc_ign_perf', 0))
    effective_perf = max(0, player['perf'] - effective_ign_perf)
    final_defense = max(0, monster['defense'] - effective_perf)

    effective_red = max(0, monster['reduction'] - player.get('ign_reduction', 0))
    effective_res_amp = max(0, monster['res_amp'] - player.get('ign_res_amp', 0))
    effective_amp = max(0, player['amp'] - effective_res_amp)
    effective_res_crit = max(0, monster['res_crit'] - player.get('ign_res_crit', 0))
    effective_crit = max(0, player['crit_damage'] - effective_res_crit)

    base_amp_damage = player['attack'] * (1 + (effective_amp / 100.0))

    normal_damage = max(1, base_amp_damage - final_defense - effective_red)
    normal_damage *= (1 + (player.get('inc_normal', 0) / 100.0))

    crit_damage_base = base_amp_damage * (1 + (effective_crit / 100.0))
    final_crit_damage = max(1, crit_damage_base - final_defense - effective_red)

    real_normal = (normal_damage * (1 + (player.get('inc_final', 0) / 100.0))) + player.get('add_damage', 0)
    real_crit = (final_crit_damage * (1 + (player.get('inc_final', 0) / 100.0))) + player.get('add_damage', 0)

    max_rate = player.get('max_rate', 50.0)
    raw_rate = player.get('crit_rate', 5.0)
    effective_rate = min(raw_rate, max_rate) / 100.0
    wasted_rate = max(0, raw_rate - max_rate)

    avg_damage = (real_normal * (1.0 - effective_rate)) + (real_crit * effective_rate)

    return (
        round(real_normal),
        round(real_crit),
        round(avg_damage),
        round(effective_rate * 100, 1),
        round(wasted_rate, 1)
    )


class CabalOptimizerApp(cctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cabal Online - Damage Optimizer")
        self.geometry("1020x840")
        self.configure(fg_color=COLOR_BG_DARK)

        if os.path.exists("cabal.ico"):
            try:
                self.iconbitmap("cabal.ico")
            except Exception:
                pass

        self.var_bm2 = cctk.BooleanVar(value=False)
        self.var_bm3 = cctk.BooleanVar(value=False)
        self.var_aura = cctk.BooleanVar(value=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = cctk.CTkTabview(
            self,
            fg_color=COLOR_BG_DARK,
            segmented_button_fg_color="#1A1A1E",
            segmented_button_selected_color="#319795",
            segmented_button_selected_hover_color="#2B6CB0",
            text_color="#FFFFFF"
        )
        self.tabview.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")

        self.tab1 = self.tabview.add(" Damage Panel ")
        self.tab_bm = self.tabview.add(" Modes & Aura ")
        self.tab2 = self.tabview.add(" Item Comparator ")
        self.tab3 = self.tabview.add(" Build Comparator ")
        self.tab4 = self.tabview.add(" Stat Efficiency ")

        self.setup_tab1()
        self.setup_tab_bm()
        self.setup_tab2()
        self.setup_tab3()
        self.setup_tab4()

        self.bind_auto_calculation()

    def create_input_field(self, master, label_text, color="#FFFFFF", default_val="0"):
        frame = cctk.CTkFrame(master, fg_color="transparent")

        lbl = cctk.CTkLabel(frame, text=label_text, text_color=color, font=("Arial", 11, "bold"), anchor="w")
        lbl.pack(fill="x", pady=(2, 0))

        if label_text in TOOLTIPS:
            ToolTip(lbl, TOOLTIPS[label_text])

        entry = cctk.CTkEntry(
            frame, fg_color="#121214", border_color="#2D3748",
            border_width=1, text_color="#FFF", justify="center", font=("Arial", 12)
        )
        entry.insert(0, default_val)
        entry.pack(fill="x", pady=(2, 5))

        return frame, entry

    def bind_auto_calculation(self):
        self.bind_class("Entry", "<KeyRelease>", lambda e: self.on_input_change())

    def on_input_change(self):
        self.calculate_base_damage()
        if hasattr(self, 'e_ef_atk'):
            self.analyze_stat_efficiency()

    # --- TAB 1: DAMAGE PANEL ---
    def setup_tab1(self):
        f_top = cctk.CTkFrame(self.tab1, fg_color="transparent")
        f_top.pack(fill="x", pady=(0, 10))

        cctk.CTkButton(f_top, text="Save Preset", font=("Arial", 11, "bold"), fg_color="#2B6CB0", hover_color="#2C5282", command=self.save_player_preset).pack(side="left", padx=5)
        cctk.CTkButton(f_top, text="Load Preset", font=("Arial", 11, "bold"), fg_color="#2B6CB0", hover_color="#2C5282", command=self.load_player_preset).pack(side="left", padx=5)
        cctk.CTkButton(f_top, text="Reset Stats", font=("Arial", 11, "bold"), fg_color="#E53E3E", hover_color="#C53030", command=self.reset_player_stats).pack(side="left", padx=5)

        f_cards = cctk.CTkFrame(self.tab1, fg_color="transparent")
        f_cards.pack(fill="both", expand=True)
        f_cards.columnconfigure(0, weight=1)
        f_cards.columnconfigure(1, weight=1)

        # PLAYER CARD
        card_p = cctk.CTkFrame(f_cards, fg_color=COLOR_BG_CARD, border_width=1, border_color="#319795", corner_radius=10)
        card_p.grid(row=0, column=0, padx=8, pady=5, sticky="nsew")

        cctk.CTkLabel(card_p, text="PLAYER BASE STATS", text_color=COLOR_TITLE_P, font=("Arial", 14, "bold")).pack(pady=10)

        f_p_grid = cctk.CTkFrame(card_p, fg_color="transparent")
        f_p_grid.pack(fill="both", expand=True, padx=10, pady=5)
        f_p_grid.columnconfigure(0, weight=1)
        f_p_grid.columnconfigure(1, weight=1)

        _, self.e_atk = self.create_input_field(f_p_grid, "Attack (Physical/Magic)", COLOR_ATK)
        self.e_atk.master.grid(row=0, column=0, padx=5, sticky="ew")

        _, self.e_amp = self.create_input_field(f_p_grid, "Skill Amp %", COLOR_AMP)
        self.e_amp.master.grid(row=0, column=1, padx=5, sticky="ew")

        _, self.e_crit = self.create_input_field(f_p_grid, "Critical Damage %", COLOR_CRIT)
        self.e_crit.master.grid(row=1, column=0, padx=5, sticky="ew")

        _, self.e_perf = self.create_input_field(f_p_grid, "Penetration", COLOR_DEF)
        self.e_perf.master.grid(row=1, column=1, padx=5, sticky="ew")

        _, self.e_taxa = self.create_input_field(f_p_grid, "Critical Rate %", COLOR_CRIT, default_val="50")
        self.e_taxa.master.grid(row=2, column=0, padx=5, sticky="ew")

        _, self.e_max_taxa = self.create_input_field(f_p_grid, "Max Critical Rate %", COLOR_CRIT, default_val="50")
        self.e_max_taxa.master.grid(row=2, column=1, padx=5, sticky="ew")

        _, self.e_add = self.create_input_field(f_p_grid, "Add Damage", COLOR_ATK)
        self.e_add.master.grid(row=3, column=0, padx=5, sticky="ew")

        _, self.e_inc_fnl = self.create_input_field(f_p_grid, "Final Damage Increase %", COLOR_ATK)
        self.e_inc_fnl.master.grid(row=3, column=1, padx=5, sticky="ew")

        _, self.e_inc_nrm = self.create_input_field(f_p_grid, "Normal Damage Increase %", COLOR_ATK)
        self.e_inc_nrm.master.grid(row=4, column=0, padx=5, sticky="ew")

        _, self.e_cnc_perf = self.create_input_field(f_p_grid, "Cancel Ignore Penetration", COLOR_DEF)
        self.e_cnc_perf.master.grid(row=4, column=1, padx=5, sticky="ew")

        _, self.e_ign_rcrit = self.create_input_field(f_p_grid, "Ignore Res. Crit Damage", COLOR_CRIT)
        self.e_ign_rcrit.master.grid(row=5, column=0, padx=5, sticky="ew")

        _, self.e_ign_ramp = self.create_input_field(f_p_grid, "Ignore Res. Skill Amp", COLOR_AMP)
        self.e_ign_ramp.master.grid(row=5, column=1, padx=5, sticky="ew")

        _, self.e_ign_red = self.create_input_field(f_p_grid, "Ignore Damage Reduction", COLOR_DEF)
        self.e_ign_red.master.grid(row=6, column=0, columnspan=2, padx=5, sticky="ew")

        # MONSTER CARD
        card_m = cctk.CTkFrame(f_cards, fg_color=COLOR_BG_CARD, border_width=1, border_color="#FC8181", corner_radius=10)
        card_m.grid(row=0, column=1, padx=8, pady=5, sticky="nsew")

        cctk.CTkLabel(card_m, text="MONSTER STATS", text_color=COLOR_TITLE_M, font=("Arial", 14, "bold")).pack(pady=10)

        f_m_inner = cctk.CTkFrame(card_m, fg_color="transparent")
        f_m_inner.pack(fill="both", expand=True, padx=15)

        cctk.CTkLabel(f_m_inner, text="Boss Preset:", font=("Arial", 11, "bold"), text_color="#E2E8F0").pack(anchor="w")
        self.combo_boss = cctk.CTkComboBox(
            f_m_inner, values=list(BOSS_PRESETS.keys()),
            command=self.load_boss_preset, fg_color="#121214", button_color="#319795", border_width=1
        )
        self.combo_boss.set("Custom")
        self.combo_boss.pack(fill="x", pady=(2, 15))

        f_m_grid = cctk.CTkFrame(f_m_inner, fg_color="transparent")
        f_m_grid.pack(fill="x")
        f_m_grid.columnconfigure(0, weight=1)
        f_m_grid.columnconfigure(1, weight=1)

        _, self.e_m_def = self.create_input_field(f_m_grid, "Defense", COLOR_DEF)
        self.e_m_def.master.grid(row=0, column=0, padx=5, sticky="ew")

        _, self.e_m_iperf = self.create_input_field(f_m_grid, "Ignore Penetration", COLOR_DEF)
        self.e_m_iperf.master.grid(row=0, column=1, padx=5, sticky="ew")

        _, self.e_m_ramp = self.create_input_field(f_m_grid, "Res. Skill Amp", COLOR_AMP)
        self.e_m_ramp.master.grid(row=1, column=0, padx=5, sticky="ew")

        _, self.e_m_rcrit = self.create_input_field(f_m_grid, "Res. Crit Damage", COLOR_CRIT)
        self.e_m_rcrit.master.grid(row=1, column=1, padx=5, sticky="ew")

        _, self.e_m_red = self.create_input_field(f_m_grid, "Damage Reduction", COLOR_DEF)
        self.e_m_red.master.grid(row=2, column=0, columnspan=2, padx=5, sticky="ew")

        f_bar = cctk.CTkFrame(f_m_inner, fg_color="transparent")
        f_bar.pack(fill="x", pady=15)

        cctk.CTkLabel(f_bar, text="Critical Rate Efficiency:", font=("Arial", 11, "bold"), text_color="#E2E8F0").pack(anchor="w")
        self.bar_taxa = cctk.CTkProgressBar(f_bar, progress_color="#319795", fg_color="#121214")
        self.bar_taxa.set(0)
        self.bar_taxa.pack(fill="x", pady=5)

        self.lbl_taxa_status = cctk.CTkLabel(f_bar, text="Effective Rate: 0% / 0%", font=("Arial", 11, "italic"), text_color="#CBD5E0")
        self.lbl_taxa_status.pack(anchor="w")

        f_bottom = cctk.CTkFrame(self.tab1, fg_color="#1A1A1E", border_width=2, border_color="#319795", corner_radius=10)
        f_bottom.pack(fill="x", padx=10, pady=(10, 0))

        self.lbl_res_base = cctk.CTkLabel(f_bottom, text="Enter stats to view calculation", font=("Arial", 15, "bold"), text_color="#4FD1C5")
        self.lbl_res_base.pack(side="left", padx=20, pady=15, expand=True, fill="x")

        cctk.CTkButton(
            f_bottom, text="Copy", font=("Arial", 11, "bold"),
            fg_color="#D69E2E", hover_color="#B7791F", text_color="#000",
            width=100, command=self.copy_base_result
        ).pack(side="right", padx=15, pady=15)

    # --- TAB 2: MODES & AURA ---
    def setup_tab_bm(self):
        f_custom = cctk.CTkFrame(self.tab_bm, fg_color=COLOR_BG_CARD, corner_radius=10, border_width=1, border_color="#319795")
        f_custom.pack(fill="x", padx=15, pady=15, ipadx=10, ipady=10)

        cctk.CTkLabel(f_custom, text="MODE & AURA BUFF CUSTOMIZATION", font=("Arial", 14, "bold"), text_color="#4FD1C5").pack(pady=(5, 15))

        def create_bm_row(title, color, key):
            f_row = cctk.CTkFrame(f_custom, fg_color="transparent")
            f_row.pack(fill="x", pady=5)

            cctk.CTkLabel(f_row, text=title, font=("Arial", 12, "bold"), text_color=color, width=200, anchor="w").pack(side="left")

            e_atk = cctk.CTkEntry(f_row, width=100, justify="center", fg_color="#121214", border_width=1)
            e_atk.insert(0, str(BM_DEFAULT_VALUES[key]["attack"]))
            e_atk.pack(side="left", padx=5)

            e_amp = cctk.CTkEntry(f_row, width=100, justify="center", fg_color="#121214", border_width=1)
            e_amp.insert(0, str(BM_DEFAULT_VALUES[key]["amp"]))
            e_amp.pack(side="left", padx=5)

            e_crit = cctk.CTkEntry(f_row, width=100, justify="center", fg_color="#121214", border_width=1)
            e_crit.insert(0, str(BM_DEFAULT_VALUES[key]["crit_damage"]))
            e_crit.pack(side="left", padx=5)

            e_taxa = cctk.CTkEntry(f_row, width=100, justify="center", fg_color="#121214", border_width=1)
            e_taxa.insert(0, str(BM_DEFAULT_VALUES[key]["crit_rate"]))
            e_taxa.pack(side="left", padx=5)

            e_perf = cctk.CTkEntry(f_row, width=100, justify="center", fg_color="#121214", border_width=1)
            e_perf.insert(0, str(BM_DEFAULT_VALUES[key]["penetration"]))
            e_perf.pack(side="left", padx=5)

            return e_atk, e_amp, e_crit, e_taxa, e_perf

        f_h = cctk.CTkFrame(f_custom, fg_color="transparent")
        f_h.pack(fill="x")
        cctk.CTkLabel(f_h, text="", width=200).pack(side="left")
        for h in ["+ Attack", "+ Amp %", "+ Crit Dmg %", "+ Crit Rate %", "+ Penetration"]:
            cctk.CTkLabel(f_h, text=h, font=("Arial", 10, "bold"), width=110).pack(side="left")

        self.e_bm_aura_atk, self.e_bm_aura_amp, self.e_bm_aura_crit, self.e_bm_aura_taxa, self.e_bm_aura_perf = create_bm_row("Aura Mode:", "#ED64A6", "Aura")
        self.e_bm_bm2_atk, self.e_bm_bm2_amp, self.e_bm_bm2_crit, self.e_bm_bm2_taxa, self.e_bm_bm2_perf = create_bm_row("Battle Mode 2 (BM2):", "#63B3ED", "BM2")
        self.e_bm_bm3_atk, self.e_bm_bm3_amp, self.e_bm_bm3_crit, self.e_bm_bm3_taxa, self.e_bm_bm3_perf = create_bm_row("Battle Mode 3 (BM3):", "#F6AD55", "BM3")

        f_ativ = cctk.CTkFrame(self.tab_bm, fg_color=COLOR_BG_CARD, corner_radius=10, border_width=1, border_color="#319795")
        f_ativ.pack(fill="x", padx=15, pady=10, ipadx=10, ipady=10)

        cctk.CTkLabel(f_ativ, text="ACTIVATION STATE", font=("Arial", 12, "bold"), text_color="#FFF").pack(anchor="w", pady=(0, 10))

        f_switches = cctk.CTkFrame(f_ativ, fg_color="transparent")
        f_switches.pack(fill="x")

        cctk.CTkSwitch(f_switches, text="Enable Aura Mode", font=("Arial", 12, "bold"), variable=self.var_aura, command=self.on_input_change, progress_color="#ED64A6").pack(side="left", padx=30)
        cctk.CTkSwitch(f_switches, text="Enable BM2", font=("Arial", 12, "bold"), variable=self.var_bm2, command=self.on_bm2_toggle, progress_color="#63B3ED").pack(side="left", padx=30)
        cctk.CTkSwitch(f_switches, text="Enable BM3", font=("Arial", 12, "bold"), variable=self.var_bm3, command=self.on_bm3_toggle, progress_color="#F6AD55").pack(side="left", padx=30)

    def on_bm2_toggle(self):
        if self.var_bm2.get():
            self.var_bm3.set(False)
        self.on_input_change()

    def on_bm3_toggle(self):
        if self.var_bm3.get():
            self.var_bm2.set(False)
        self.on_input_change()

    # --- TAB 3: ITEM COMPARATOR ---
    def setup_tab2(self):
        f_grid = cctk.CTkFrame(self.tab2, fg_color="transparent")
        f_grid.pack(fill="x", padx=10, pady=10)
        f_grid.columnconfigure(0, weight=1)
        f_grid.columnconfigure(1, weight=1)

        # ITEM A
        card_a = cctk.CTkFrame(f_grid, fg_color=COLOR_BG_CARD, border_width=1, border_color=COLOR_DEF, corner_radius=10)
        card_a.grid(row=0, column=0, padx=8, sticky="nsew")
        cctk.CTkLabel(card_a, text="ITEM A STATS", font=("Arial", 12, "bold"), text_color=COLOR_DEF).pack(pady=10)

        f_a_in = cctk.CTkFrame(card_a, fg_color="transparent")
        f_a_in.pack(fill="x", padx=10)
        f_a_in.columnconfigure(0, weight=1)
        f_a_in.columnconfigure(1, weight=1)

        _, self.e_ia_atk = self.create_input_field(f_a_in, "+ Attack", COLOR_ATK)
        self.e_ia_atk.master.grid(row=0, column=0, padx=5, sticky="ew")
        _, self.e_ia_amp = self.create_input_field(f_a_in, "+ Amp %", COLOR_AMP)
        self.e_ia_amp.master.grid(row=0, column=1, padx=5, sticky="ew")
        _, self.e_ia_crit = self.create_input_field(f_a_in, "+ Crit Damage %", COLOR_CRIT)
        self.e_ia_crit.master.grid(row=1, column=0, padx=5, sticky="ew")
        _, self.e_ia_taxa = self.create_input_field(f_a_in, "+ Crit Rate %", COLOR_CRIT)
        self.e_ia_taxa.master.grid(row=1, column=1, padx=5, sticky="ew")
        _, self.e_ia_max_taxa = self.create_input_field(f_a_in, "+ Max Rate %", COLOR_CRIT)
        self.e_ia_max_taxa.master.grid(row=2, column=0, padx=5, sticky="ew")
        _, self.e_ia_perf = self.create_input_field(f_a_in, "+ Penetration", COLOR_DEF)
        self.e_ia_perf.master.grid(row=2, column=1, padx=5, sticky="ew")
        _, self.e_ia_ired = self.create_input_field(f_a_in, "+ Ignore Reduction", COLOR_DEF)
        self.e_ia_ired.master.grid(row=3, column=0, columnspan=2, padx=5, sticky="ew")

        # ITEM B
        card_b = cctk.CTkFrame(f_grid, fg_color=COLOR_BG_CARD, border_width=1, border_color="#ED64A6", corner_radius=10)
        card_b.grid(row=0, column=1, padx=8, sticky="nsew")
        cctk.CTkLabel(card_b, text="ITEM B STATS", font=("Arial", 12, "bold"), text_color="#ED64A6").pack(pady=10)

        f_b_in = cctk.CTkFrame(card_b, fg_color="transparent")
        f_b_in.pack(fill="x", padx=10)
        f_b_in.columnconfigure(0, weight=1)
        f_b_in.columnconfigure(1, weight=1)

        _, self.e_ib_atk = self.create_input_field(f_b_in, "+ Attack", COLOR_ATK)
        self.e_ib_atk.master.grid(row=0, column=0, padx=5, sticky="ew")
        _, self.e_ib_amp = self.create_input_field(f_b_in, "+ Amp %", COLOR_AMP)
        self.e_ib_amp.master.grid(row=0, column=1, padx=5, sticky="ew")
        _, self.e_ib_crit = self.create_input_field(f_b_in, "+ Crit Damage %", COLOR_CRIT)
        self.e_ib_crit.master.grid(row=1, column=0, padx=5, sticky="ew")
        _, self.e_ib_taxa = self.create_input_field(f_b_in, "+ Crit Rate %", COLOR_CRIT)
        self.e_ib_taxa.master.grid(row=1, column=1, padx=5, sticky="ew")
        _, self.e_ib_max_taxa = self.create_input_field(f_b_in, "+ Max Rate %", COLOR_CRIT)
        self.e_ib_max_taxa.master.grid(row=2, column=0, padx=5, sticky="ew")
        _, self.e_ib_perf = self.create_input_field(f_b_in, "+ Penetration", COLOR_DEF)
        self.e_ib_perf.master.grid(row=2, column=1, padx=5, sticky="ew")
        _, self.e_ib_ired = self.create_input_field(f_b_in, "+ Ignore Reduction", COLOR_DEF)
        self.e_ib_ired.master.grid(row=3, column=0, columnspan=2, padx=5, sticky="ew")

        cctk.CTkButton(
            self.tab2, text="COMPARE ITEM DAMAGE", font=("Arial", 13, "bold"),
            fg_color="#D69E2E", hover_color="#B7791F", text_color="#000", command=self.compare_items
        ).pack(fill="x", padx=20, pady=15)

        self.lbl_res_comp = cctk.CTkLabel(
            self.tab2, text="Fill item attributes and click Compare.",
            font=("Arial", 12), fg_color=COLOR_BG_CARD, corner_radius=10, justify="left", padx=20, pady=20
        )
        self.lbl_res_comp.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    # --- TAB 4: BUILD COMPARATOR ---
    def setup_tab3(self):
        f_grid = cctk.CTkFrame(self.tab3, fg_color="transparent")
        f_grid.pack(fill="x", padx=10, pady=10)
        f_grid.columnconfigure(0, weight=1)
        f_grid.columnconfigure(1, weight=1)

        # BUILD 1
        card_b1 = cctk.CTkFrame(f_grid, fg_color=COLOR_BG_CARD, border_width=1, border_color="#4FD1C5", corner_radius=10)
        card_b1.grid(row=0, column=0, padx=8, sticky="nsew")
        cctk.CTkLabel(card_b1, text="BUILD 1", font=("Arial", 12, "bold"), text_color="#4FD1C5").pack(pady=10)

        f_b1_in = cctk.CTkFrame(card_b1, fg_color="transparent")
        f_b1_in.pack(fill="x", padx=10)
        f_b1_in.columnconfigure(0, weight=1)
        f_b1_in.columnconfigure(1, weight=1)

        _, self.e_b1_atk = self.create_input_field(f_b1_in, "Total Attack", COLOR_ATK)
        self.e_b1_atk.master.grid(row=0, column=0, padx=5, sticky="ew")
        _, self.e_b1_amp = self.create_input_field(f_b1_in, "Total Amp %", COLOR_AMP)
        self.e_b1_amp.master.grid(row=0, column=1, padx=5, sticky="ew")
        _, self.e_b1_crit = self.create_input_field(f_b1_in, "Crit Damage %", COLOR_CRIT)
        self.e_b1_crit.master.grid(row=1, column=0, padx=5, sticky="ew")
        _, self.e_b1_taxa = self.create_input_field(f_b1_in, "Crit Rate %", COLOR_CRIT, default_val="50")
        self.e_b1_taxa.master.grid(row=1, column=1, padx=5, sticky="ew")
        _, self.e_b1_max_taxa = self.create_input_field(f_b1_in, "Max Rate %", COLOR_CRIT, default_val="50")
        self.e_b1_max_taxa.master.grid(row=2, column=0, padx=5, sticky="ew")
        _, self.e_b1_perf = self.create_input_field(f_b1_in, "Penetration", COLOR_DEF)
        self.e_b1_perf.master.grid(row=2, column=1, padx=5, sticky="ew")
        _, self.e_b1_add = self.create_input_field(f_b1_in, "Add Damage", COLOR_ATK)
        self.e_b1_add.master.grid(row=3, column=0, padx=5, sticky="ew")
        _, self.e_b1_ired = self.create_input_field(f_b1_in, "Ignore Reduction", COLOR_DEF)
        self.e_b1_ired.master.grid(row=3, column=1, padx=5, sticky="ew")

        # BUILD 2
        card_b2 = cctk.CTkFrame(f_grid, fg_color=COLOR_BG_CARD, border_width=1, border_color="#F6AD55", corner_radius=10)
        card_b2.grid(row=0, column=1, padx=8, sticky="nsew")
        cctk.CTkLabel(card_b2, text="BUILD 2", font=("Arial", 12, "bold"), text_color="#F6AD55").pack(pady=10)

        f_b2_in = cctk.CTkFrame(card_b2, fg_color="transparent")
        f_b2_in.pack(fill="x", padx=10)
        f_b2_in.columnconfigure(0, weight=1)
        f_b2_in.columnconfigure(1, weight=1)

        _, self.e_b2_atk = self.create_input_field(f_b2_in, "Total Attack", COLOR_ATK)
        self.e_b2_atk.master.grid(row=0, column=0, padx=5, sticky="ew")
        _, self.e_b2_amp = self.create_input_field(f_b2_in, "Total Amp %", COLOR_AMP)
        self.e_b2_amp.master.grid(row=0, column=1, padx=5, sticky="ew")
        _, self.e_b2_crit = self.create_input_field(f_b2_in, "Crit Damage %", COLOR_CRIT)
        self.e_b2_crit.master.grid(row=1, column=0, padx=5, sticky="ew")
        _, self.e_b2_taxa = self.create_input_field(f_b2_in, "Crit Rate %", COLOR_CRIT, default_val="50")
        self.e_b2_taxa.master.grid(row=1, column=1, padx=5, sticky="ew")
        _, self.e_b2_max_taxa = self.create_input_field(f_b2_in, "Max Rate %", COLOR_CRIT, default_val="50")
        self.e_b2_max_taxa.master.grid(row=2, column=0, padx=5, sticky="ew")
        _, self.e_b2_perf = self.create_input_field(f_b2_in, "Penetration", COLOR_DEF)
        self.e_b2_perf.master.grid(row=2, column=1, padx=5, sticky="ew")
        _, self.e_b2_add = self.create_input_field(f_b2_in, "Add Damage", COLOR_ATK)
        self.e_b2_add.master.grid(row=3, column=0, padx=5, sticky="ew")
        _, self.e_b2_ired = self.create_input_field(f_b2_in, "Ignore Reduction", COLOR_DEF)
        self.e_b2_ired.master.grid(row=3, column=1, padx=5, sticky="ew")

        cctk.CTkButton(
            self.tab3, text="COMPARE FULL BUILDS", font=("Arial", 13, "bold"),
            fg_color="#9F7AEA", hover_color="#805AD5", text_color="#FFF", command=self.compare_builds
        ).pack(fill="x", padx=20, pady=15)

        self.lbl_res_builds = cctk.CTkLabel(
            self.tab3, text="Configure both builds to compare average damage against target active in Tab 1.",
            font=("Arial", 12), fg_color=COLOR_BG_CARD, corner_radius=10, justify="left", padx=20, pady=20
        )
        self.lbl_res_builds.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    # --- TAB 5: STAT EFFICIENCY ---
    def setup_tab4(self):
        f_main = cctk.CTkFrame(self.tab4, fg_color="transparent")
        f_main.pack(fill="both", expand=True, padx=10, pady=10)

        card_cfg = cctk.CTkFrame(f_main, fg_color=COLOR_BG_CARD, border_width=1, border_color="#48BB78", corner_radius=10, width=320)
        card_cfg.pack(side="left", fill="y", padx=(0, 10), pady=5)

        cctk.CTkLabel(card_cfg, text="CUSTOM INCREMENTS", font=("Arial", 13, "bold"), text_color="#48BB78").pack(pady=(12, 5))
        cctk.CTkLabel(card_cfg, text="Adjust test delta values:", font=("Arial", 10, "italic"), text_color="#A0AEC0").pack(pady=(0, 10))

        f_inputs = cctk.CTkFrame(card_cfg, fg_color="transparent")
        f_inputs.pack(fill="x", padx=12)

        _, self.e_ef_atk = self.create_input_field(f_inputs, "+ Base Attack", COLOR_ATK, "100")
        self.e_ef_atk.master.pack(fill="x")

        _, self.e_ef_amp = self.create_input_field(f_inputs, "+ Skill Amp %", COLOR_AMP, "10")
        self.e_ef_amp.master.pack(fill="x")

        _, self.e_ef_crit = self.create_input_field(f_inputs, "+ Crit Damage %", COLOR_CRIT, "10")
        self.e_ef_crit.master.pack(fill="x")

        _, self.e_ef_taxa = self.create_input_field(f_inputs, "+ Crit Rate %", COLOR_CRIT, "5")
        self.e_ef_taxa.master.pack(fill="x")

        _, self.e_ef_perf = self.create_input_field(f_inputs, "+ Penetration", COLOR_DEF, "50")
        self.e_ef_perf.master.pack(fill="x")

        _, self.e_ef_ired = self.create_input_field(f_inputs, "+ Ignore Reduction", COLOR_DEF, "50")
        self.e_ef_ired.master.pack(fill="x")

        _, self.e_ef_cnc_p = self.create_input_field(f_inputs, "+ Canc. Ign. Perf.", COLOR_DEF, "50")
        self.e_ef_cnc_p.master.pack(fill="x")

        cctk.CTkButton(
            card_cfg, text="ANALYZE NOW", font=("Arial", 12, "bold"),
            fg_color="#48BB78", hover_color="#38A169", text_color="#FFF", command=self.analyze_stat_efficiency
        ).pack(fill="x", padx=12, pady=15)

        card_res = cctk.CTkFrame(f_main, fg_color=COLOR_BG_CARD, border_width=1, border_color="#319795", corner_radius=10)
        card_res.pack(side="right", fill="both", expand=True, pady=5)

        cctk.CTkLabel(card_res, text="MARGINAL GAIN & PENETRATION WEIGHT DIAGNOSTIC", font=("Arial", 13, "bold"), text_color="#4FD1C5").pack(pady=10)

        self.txt_efic = cctk.CTkTextbox(card_res, fg_color="#121214", text_color="#4FD1C5", font=("Courier New", 12, "bold"), corner_radius=8, border_width=1, border_color="#2D3748")
        self.txt_efic.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.txt_efic.insert("1.0", "Fill stats on Tab 1 and adjust parameters on the left to view efficiency.")

    # ==========================================
    # UTILITY METHODS (JSON, PRESETS, CLIPBOARD)
    # ==========================================

    def save_player_preset(self):
        player_data, _ = self.get_ui_data()
        if not player_data:
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(player_data, f, indent=4)
                messagebox.showinfo("Success", "Preset saved successfully!")
            except Exception as err:
                messagebox.showerror("Error", f"Failed to save preset: {err}")

    def load_player_preset(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                mapping = {
                    'attack': self.e_atk, 'amp': self.e_amp, 'crit_damage': self.e_crit,
                    'perf': self.e_perf, 'crit_rate': self.e_taxa, 'max_rate': self.e_max_taxa,
                    'add_damage': self.e_add, 'inc_final': self.e_inc_fnl, 'inc_normal': self.e_inc_nrm,
                    'canc_ign_perf': self.e_cnc_perf, 'ign_res_crit': self.e_ign_rcrit,
                    'ign_res_amp': self.e_ign_ramp, 'ign_reduction': self.e_ign_red
                }

                for key, field in mapping.items():
                    if key in data:
                        field.delete(0, 'end')
                        field.insert(0, str(data[key]))

                self.on_input_change()
                messagebox.showinfo("Success", "Preset loaded successfully!")
            except Exception as err:
                messagebox.showerror("Error", f"Failed to load preset: {err}")

    def reset_player_stats(self):
        fields = [
            self.e_atk, self.e_amp, self.e_crit, self.e_perf, self.e_taxa, self.e_max_taxa,
            self.e_add, self.e_inc_fnl, self.e_inc_nrm, self.e_cnc_perf, self.e_ign_rcrit,
            self.e_ign_ramp, self.e_ign_red
        ]
        for field in fields:
            field.delete(0, 'end')
            field.insert(0, "0")
        self.on_input_change()

    def copy_base_result(self):
        text = self.lbl_res_base.cget("text")
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Result copied to clipboard!")

    def load_boss_preset(self, choice):
        if choice in BOSS_PRESETS:
            data = BOSS_PRESETS[choice]
            self.e_m_def.delete(0, 'end')
            self.e_m_def.insert(0, str(data['defense']))
            self.e_m_iperf.delete(0, 'end')
            self.e_m_iperf.insert(0, str(data['ign_perf']))
            self.e_m_ramp.delete(0, 'end')
            self.e_m_ramp.insert(0, str(data['res_amp']))
            self.e_m_rcrit.delete(0, 'end')
            self.e_m_rcrit.insert(0, str(data['res_crit']))
            self.e_m_red.delete(0, 'end')
            self.e_m_red.insert(0, str(data['reduction']))
            self.on_input_change()

    def get_ui_data(self):
        try:
            player = {
                'attack': float(self.e_atk.get() or 0), 'amp': float(self.e_amp.get() or 0),
                'crit_damage': float(self.e_crit.get() or 0), 'perf': float(self.e_perf.get() or 0),
                'crit_rate': float(self.e_taxa.get() or 0), 'max_rate': float(self.e_max_taxa.get() or 0),
                'add_damage': float(self.e_add.get() or 0), 'inc_final': float(self.e_inc_fnl.get() or 0),
                'inc_normal': float(self.e_inc_nrm.get() or 0), 'canc_ign_perf': float(self.e_cnc_perf.get() or 0),
                'ign_res_crit': float(self.e_ign_rcrit.get() or 0), 'ign_res_amp': float(self.e_ign_ramp.get() or 0),
                'ign_reduction': float(self.e_ign_red.get() or 0)
            }
            monster = {
                'defense': float(self.e_m_def.get() or 0), 'ign_perf': float(self.e_m_iperf.get() or 0),
                'res_amp': float(self.e_m_ramp.get() or 0), 'res_crit': float(self.e_m_rcrit.get() or 0),
                'reduction': float(self.e_m_red.get() or 0)
            }

            if self.var_aura.get():
                player['attack'] += float(self.e_bm_aura_atk.get() or 0)
                player['amp'] += float(self.e_bm_aura_amp.get() or 0)
                player['crit_damage'] += float(self.e_bm_aura_crit.get() or 0)
                player['crit_rate'] += float(self.e_bm_aura_taxa.get() or 0)
                player['perf'] += float(self.e_bm_aura_perf.get() or 0)

            if self.var_bm2.get():
                player['attack'] += float(self.e_bm_bm2_atk.get() or 0)
                player['amp'] += float(self.e_bm_bm2_amp.get() or 0)
                player['crit_damage'] += float(self.e_bm_bm2_crit.get() or 0)
                player['crit_rate'] += float(self.e_bm_bm2_taxa.get() or 0)
                player['perf'] += float(self.e_bm_bm2_perf.get() or 0)

            elif self.var_bm3.get():
                player['attack'] += float(self.e_bm_bm3_atk.get() or 0)
                player['amp'] += float(self.e_bm_bm3_amp.get() or 0)
                player['crit_damage'] += float(self.e_bm_bm3_crit.get() or 0)
                player['crit_rate'] += float(self.e_bm_bm3_taxa.get() or 0)
                player['perf'] += float(self.e_bm_bm3_perf.get() or 0)

            return player, monster
        except ValueError:
            return None, None

    def calculate_base_damage(self):
        player, monster = self.get_ui_data()
        if player and monster:
            normal, crit, avg, eff_rate, wasted_rate = calculate_cabal_damage(player, monster)
            txt = f"NORMAL: {normal}   |   CRITICAL: {crit}\n"
            txt += f"AVERAGE HIT DAMAGE: {avg}  (Effective Critical Rate: {eff_rate}%)"
            self.lbl_res_base.configure(text=txt)

            max_r = player['max_rate'] if player['max_rate'] > 0 else 1.0
            pct_progress = min(1.0, (eff_rate / max_r))
            self.bar_taxa.set(pct_progress)

            if wasted_rate > 0:
                self.lbl_taxa_status.configure(
                    text=f"Effective Rate: {eff_rate}% / {player['max_rate']}% (Wasted Rate: +{wasted_rate}%)",
                    text_color="#FC8181"
                )
            else:
                self.lbl_taxa_status.configure(
                    text=f"Effective Rate: {eff_rate}% / {player['max_rate']}% (Fully Utilized)",
                    text_color="#68D391"
                )

    def compare_items(self):
        p_original, monster = self.get_ui_data()
        if not p_original or not monster:
            return

        try:
            item_a = p_original.copy()
            item_a['attack'] += float(self.e_ia_atk.get() or 0)
            item_a['amp'] += float(self.e_ia_amp.get() or 0)
            item_a['crit_damage'] += float(self.e_ia_crit.get() or 0)
            item_a['crit_rate'] += float(self.e_ia_taxa.get() or 0)
            item_a['max_rate'] += float(self.e_ia_max_taxa.get() or 0)
            item_a['perf'] += float(self.e_ia_perf.get() or 0)
            item_a['ign_reduction'] += float(self.e_ia_ired.get() or 0)

            item_b = p_original.copy()
            item_b['attack'] += float(self.e_ib_atk.get() or 0)
            item_b['amp'] += float(self.e_ib_amp.get() or 0)
            item_b['crit_damage'] += float(self.e_ib_crit.get() or 0)
            item_b['crit_rate'] += float(self.e_ib_taxa.get() or 0)
            item_b['max_rate'] += float(self.e_ib_max_taxa.get() or 0)
            item_b['perf'] += float(self.e_ib_perf.get() or 0)
            item_b['ign_reduction'] += float(self.e_ib_ired.get() or 0)

            norm_a, crit_a, avg_a, rate_a, _ = calculate_cabal_damage(item_a, monster)
            norm_b, crit_b, avg_b, rate_b, _ = calculate_cabal_damage(item_b, monster)

            txt = f"ITEM A -> Normal: {norm_a} | Critical: {crit_a} | AVG DAMAGE: {avg_a} (Rate: {rate_a}%)\n"
            txt += f"ITEM B -> Normal: {norm_b} | Critical: {crit_b} | AVG DAMAGE: {avg_b} (Rate: {rate_b}%)\n"
            txt += "-" * 75 + "\n"

            if avg_a > avg_b:
                diff = ((avg_a - avg_b) / avg_b) * 100
                txt += f"RESULT: ITEM A is superior! Its average damage is {diff:.2f}% HIGHER than Item B."
            elif avg_b > avg_a:
                diff = ((avg_b - avg_a) / avg_a) * 100
                txt += f"RESULT: ITEM B is superior! Its average damage is {diff:.2f}% HIGHER than Item A."
            else:
                txt += "RESULT: Both items produce the exact same damage efficiency."

            self.lbl_res_comp.configure(text=txt)
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for item attributes!")

    def compare_builds(self):
        _, monster = self.get_ui_data()
        if not monster:
            return
        try:
            b1 = {
                'attack': float(self.e_b1_atk.get() or 0), 'amp': float(self.e_b1_amp.get() or 0),
                'crit_damage': float(self.e_b1_crit.get() or 0), 'crit_rate': float(self.e_b1_taxa.get() or 0),
                'max_rate': float(self.e_b1_max_taxa.get() or 0), 'perf': float(self.e_b1_perf.get() or 0),
                'add_damage': float(self.e_b1_add.get() or 0), 'ign_reduction': float(self.e_b1_ired.get() or 0)
            }
            b2 = {
                'attack': float(self.e_b2_atk.get() or 0), 'amp': float(self.e_b2_amp.get() or 0),
                'crit_damage': float(self.e_b2_crit.get() or 0), 'crit_rate': float(self.e_b2_taxa.get() or 0),
                'max_rate': float(self.e_b2_max_taxa.get() or 0), 'perf': float(self.e_b2_perf.get() or 0),
                'add_damage': float(self.e_b2_add.get() or 0), 'ign_reduction': float(self.e_b2_ired.get() or 0)
            }

            n1, c1, avg1, r1, _ = calculate_cabal_damage(b1, monster)
            n2, c2, avg2, r2, _ = calculate_cabal_damage(b2, monster)

            txt = f"BUILD 1 -> Normal: {n1} | Critical: {c1} | AVG DAMAGE: {avg1} (Rate: {r1}%)\n"
            txt += f"BUILD 2 -> Normal: {n2} | Critical: {c2} | AVG DAMAGE: {avg2} (Rate: {r2}%)\n"
            txt += "-" * 75 + "\n"

            if avg1 > avg2:
                diff = ((avg1 - avg2) / avg2) * 100
                txt += f"BUILD 1 wins with {diff:.2f}% higher overall average damage!"
            elif avg2 > avg1:
                diff = ((avg2 - avg1) / avg1) * 100
                txt += f"BUILD 2 wins with {diff:.2f}% higher overall average damage!"
            else:
                txt += "Both builds have equal damage efficiency against this target."

            self.lbl_res_builds.configure(text=txt)
        except ValueError:
            messagebox.showerror("Error", "Please fill all fields with valid numbers!")

    def analyze_stat_efficiency(self):
        player_base, monster = self.get_ui_data()
        if not player_base or not monster:
            return

        _, _, base_avg, _, _ = calculate_cabal_damage(player_base, monster)
        if base_avg <= 0:
            base_avg = 1

        val_atk = float(self.e_ef_atk.get() or 0)
        val_amp = float(self.e_ef_amp.get() or 0)
        val_crit = float(self.e_ef_crit.get() or 0)
        val_taxa = float(self.e_ef_taxa.get() or 0)
        val_perf = float(self.e_ef_perf.get() or 0)
        val_ired = float(self.e_ef_ired.get() or 0)
        val_cncp = float(self.e_ef_cnc_p.get() or 0)

        tests = [
            (f"+{val_atk:.0f} Base Attack", {'attack': val_atk}),
            (f"+{val_amp:.1f}% Skill Amp", {'amp': val_amp}),
            (f"+{val_crit:.1f}% Crit Damage", {'crit_damage': val_crit}),
            (f"+{val_taxa:.1f}% Crit Rate", {'crit_rate': val_taxa}),
            (f"+{val_perf:.0f} Penetration", {'perf': val_perf}),
            (f"+{val_ired:.0f} Ignore Reduction", {'ign_reduction': val_ired}),
            (f"+{val_cncp:.0f} Canc. Ign. Perf.", {'canc_ign_perf': val_cncp})
        ]

        txt = f"CUSTOM MARGINAL GAIN DIAGNOSTIC (Base Average Damage: {base_avg})\n"
        txt += "========================================================================\n\n"

        for label, mod in tests:
            test_player = player_base.copy()
            for k, v in mod.items():
                test_player[k] += v
            _, _, new_avg, _, _ = calculate_cabal_damage(test_player, monster)
            gain_pct = ((new_avg - base_avg) / base_avg) * 100
            txt += f"• {label:<28} -> New Avg Damage: {new_avg:<8} (Gain: +{gain_pct:.2f}%)\n"

        ign_perf_mob = max(0, monster['ign_perf'] - player_base.get('canc_ign_perf', 0))
        used_perf = max(0, player_base['perf'] - ign_perf_mob)
        remaining_def = max(0, monster['defense'] - used_perf)

        txt += "\n" + "=" * 72 + "\n"
        txt += "PENETRATION IMPACT ANALYSIS AGAINST TARGET:\n"
        txt += "========================================================================\n"
        txt += f" • Monster Raw Defense: {monster['defense']:.0f}\n"
        txt += f" • Monster Ignore Penetration: {monster['ign_perf']:.0f} (Your Cancel: {player_base.get('canc_ign_perf', 0):.0f})\n"
        txt += f" • Effective Active Penetration: {used_perf:.0f} out of {player_base['perf']:.0f}\n"
        txt += f" • Target Remaining Defense: {remaining_def:.0f}\n"

        if remaining_def == 0 and monster['defense'] > 0:
            txt += " NOTE: Target defense fully negated! Additional penetration beyond this point has diminishing returns.\n"
        elif used_perf == 0 and player_base['perf'] > 0:
            txt += " WARNING: All penetration is being negated by target's 'Ignore Penetration'. Increase 'Cancel Ignore Penetration'.\n"

        self.txt_efic.delete("1.0", "end")
        self.txt_efic.insert("1.0", txt)


if __name__ == "__main__":
    app = CabalOptimizerApp()
    app.mainloop()