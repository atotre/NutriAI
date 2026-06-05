"""
build_database.py  ─  ONE-TIME SETUP SCRIPT
Builds food_database.db at the location expected by code/pipeline.py.

Run once before launching the app:
    python data/build_database.py

Source for all nutrient values:
    USDA FoodData Central – SR Legacy / Foundation Foods
    https://fdc.nal.usda.gov/
Low-FODMAP annotations: Monash University FODMAP App (2023)
Glycemic Index values:  The International Tables of Glycemic Index and
                        Glycemic Load (Atkinson et al., Diabetes Care 2008;
                        updated Foster-Powell / Brand-Miller tables)
DASH thresholds:        NHLBI / American Heart Association (2021)
"""

import sqlite3
import os
import itertools
import math

DB_PATH = os.path.join(os.path.dirname(__file__), "food_database.db")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — USDA BASE INGREDIENT PROFILES
# All values per 100 g, ready-to-eat unless noted.
# Keys
#   cal  protein  carb  fat  fib   – macros (g) / kcal
#   iron ca b12 vd zn na k mgm    – micros: mg, mg, µg, µg, mg, mg, mg, mg
#   gi                             – glycemic index (0 = not applicable)
#   fodmap                         – "low" | "high" (Monash University)
#   fodmap_triggers                – specific FODMAP offenders in this item
#   gerd_safe                      – bool (False = contains known GERD triggers)
#   allergens                      – list of canonical tags
#   veg   vegan  pesc              – dietary flags
# ─────────────────────────────────────────────────────────────────────────────

# fmt: off
INGREDIENTS: dict = {

    # ── POULTRY ──────────────────────────────────────────────────────────────
    "chicken_breast": {
        "desc": "Chicken Breast, boneless, skinless, roasted",
        "cal": 165, "pro": 31.0, "carb": 0.0, "fat": 3.6, "fib": 0.0,
        "iron": 1.16, "ca": 15,  "b12": 0.32, "vd": 0.2,  "zn": 1.16,
        "na": 74,  "k": 358, "mgm": 29,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "turkey_breast": {
        "desc": "Turkey Breast, roasted",
        "cal": 157, "pro": 29.9, "carb": 0.0, "fat": 3.5, "fib": 0.0,
        "iron": 1.57, "ca": 28, "b12": 1.50, "vd": 0.0,  "zn": 2.45,
        "na": 63,  "k": 298, "mgm": 28,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "ground_turkey": {
        "desc": "Ground Turkey, cooked",
        "cal": 189, "pro": 27.4, "carb": 0.0, "fat": 8.3, "fib": 0.0,
        "iron": 1.80, "ca": 22, "b12": 1.32, "vd": 0.1,  "zn": 3.26,
        "na": 88,  "k": 310, "mgm": 25,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "chicken_thigh": {
        "desc": "Chicken Thigh, boneless, skinless, roasted",
        "cal": 179, "pro": 24.8, "carb": 0.0, "fat": 8.2, "fib": 0.0,
        "iron": 1.12, "ca": 12, "b12": 0.46, "vd": 0.1,  "zn": 2.40,
        "na": 84,  "k": 283, "mgm": 26,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },

    # ── BEEF / PORK / LAMB ───────────────────────────────────────────────────
    "beef_sirloin": {
        "desc": "Beef Sirloin, lean, broiled",
        "cal": 207, "pro": 27.6, "carb": 0.0, "fat": 10.0, "fib": 0.0,
        "iron": 2.48, "ca": 19, "b12": 2.44, "vd": 0.1,  "zn": 5.88,
        "na": 56,  "k": 338, "mgm": 26,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "ground_beef_lean": {
        "desc": "Ground Beef 90% lean, pan-broiled",
        "cal": 218, "pro": 26.1, "carb": 0.0, "fat": 12.0, "fib": 0.0,
        "iron": 2.60, "ca": 19, "b12": 2.45, "vd": 0.1,  "zn": 5.58,
        "na": 68,  "k": 315, "mgm": 22,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "pork_tenderloin": {
        "desc": "Pork Tenderloin, roasted",
        "cal": 143, "pro": 25.6, "carb": 0.0, "fat": 3.5, "fib": 0.0,
        "iron": 1.21, "ca": 4,  "b12": 0.62, "vd": 0.4,  "zn": 2.31,
        "na": 53,  "k": 451, "mgm": 26,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "lamb_leg": {
        "desc": "Lamb Leg, lean, roasted",
        "cal": 191, "pro": 26.0, "carb": 0.0, "fat": 8.8, "fib": 0.0,
        "iron": 2.22, "ca": 15, "b12": 2.97, "vd": 0.1,  "zn": 4.56,
        "na": 65,  "k": 310, "mgm": 24,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },
    "bison_ground": {
        "desc": "Ground Bison, cooked",
        "cal": 215, "pro": 24.5, "carb": 0.0, "fat": 12.3, "fib": 0.0,
        "iron": 3.46, "ca": 14, "b12": 2.86, "vd": 0.1,  "zn": 4.78,
        "na": 70,  "k": 338, "mgm": 24,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": False, "vegan": False, "pesc": False,
    },

    # ── SEAFOOD ──────────────────────────────────────────────────────────────
    "salmon_atlantic": {
        "desc": "Atlantic Salmon, cooked",
        "cal": 208, "pro": 20.4, "carb": 0.0, "fat": 13.4, "fib": 0.0,
        "iron": 0.34, "ca": 9,  "b12": 3.18, "vd": 9.6,  "zn": 0.36,
        "na": 59,  "k": 384, "mgm": 29,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "salmon_sockeye": {
        "desc": "Sockeye Salmon, cooked",
        "cal": 168, "pro": 25.7, "carb": 0.0, "fat": 6.7, "fib": 0.0,
        "iron": 0.63, "ca": 8,  "b12": 4.9,  "vd": 11.2, "zn": 0.55,
        "na": 50,  "k": 391, "mgm": 31,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "tuna_yellowfin": {
        "desc": "Tuna, yellowfin, cooked",
        "cal": 139, "pro": 30.1, "carb": 0.0, "fat": 1.2, "fib": 0.0,
        "iron": 0.93, "ca": 16, "b12": 2.10, "vd": 4.0,  "zn": 0.52,
        "na": 47,  "k": 569, "mgm": 50,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "tuna_canned_water": {
        "desc": "Tuna, light, canned in water",
        "cal": 116, "pro": 25.5, "carb": 0.0, "fat": 1.0, "fib": 0.0,
        "iron": 1.18, "ca": 11, "b12": 2.52, "vd": 3.7,  "zn": 0.72,
        "na": 337, "k": 267, "mgm": 31,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "cod_pacific": {
        "desc": "Pacific Cod, cooked",
        "cal": 105, "pro": 22.8, "carb": 0.0, "fat": 0.86,"fib": 0.0,
        "iron": 0.58, "ca": 22, "b12": 1.19, "vd": 0.9,  "zn": 0.52,
        "na": 73,  "k": 439, "mgm": 32,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "tilapia": {
        "desc": "Tilapia, cooked",
        "cal": 128, "pro": 26.2, "carb": 0.0, "fat": 2.7, "fib": 0.0,
        "iron": 0.56, "ca": 10, "b12": 1.86, "vd": 0.4,  "zn": 0.36,
        "na": 56,  "k": 302, "mgm": 27,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "halibut": {
        "desc": "Halibut, cooked",
        "cal": 140, "pro": 27.2, "carb": 0.0, "fat": 2.9, "fib": 0.0,
        "iron": 0.18, "ca": 60, "b12": 1.24, "vd": 4.9,  "zn": 0.53,
        "na": 69,  "k": 576, "mgm": 107, "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "mackerel": {
        "desc": "Atlantic Mackerel, cooked",
        "cal": 239, "pro": 21.9, "carb": 0.0, "fat": 16.3,"fib": 0.0,
        "iron": 1.63, "ca": 10, "b12": 12.6, "vd": 4.6,  "zn": 0.90,
        "na": 83,  "k": 314, "mgm": 73,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "sardines_water": {
        "desc": "Sardines, canned in water",
        "cal": 127, "pro": 22.0, "carb": 0.0, "fat": 5.2, "fib": 0.0,
        "iron": 2.98, "ca": 241,"b12": 8.94, "vd": 1.9,  "zn": 1.12,
        "na": 307, "k": 397, "mgm": 39,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["fish"], "veg": False, "vegan": False, "pesc": True,
    },
    "shrimp": {
        "desc": "Shrimp, steamed",
        "cal": 99,  "pro": 24.0, "carb": 0.0, "fat": 0.3, "fib": 0.0,
        "iron": 3.09, "ca": 70, "b12": 1.40, "vd": 0.0,  "zn": 1.57,
        "na": 224, "k": 259, "mgm": 37,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["shellfish"], "veg": False, "vegan": False, "pesc": True,
    },
    "scallops": {
        "desc": "Sea Scallops, cooked",
        "cal": 111, "pro": 20.5, "carb": 5.4, "fat": 0.9, "fib": 0.0,
        "iron": 0.61, "ca": 10, "b12": 1.80, "vd": 0.0,  "zn": 1.17,
        "na": 267, "k": 476, "mgm": 46,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["shellfish"], "veg": False, "vegan": False, "pesc": True,
    },
    "mussels": {
        "desc": "Mussels, cooked",
        "cal": 172, "pro": 23.8, "carb": 7.4, "fat": 4.5, "fib": 0.0,
        "iron": 6.72, "ca": 33, "b12": 20.4, "vd": 0.3,  "zn": 2.67,
        "na": 369, "k": 268, "mgm": 37,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["shellfish"], "veg": False, "vegan": False, "pesc": True,
    },

    # ── EGGS ─────────────────────────────────────────────────────────────────
    "egg_whole": {
        "desc": "Egg, whole, hard-boiled",
        "cal": 155, "pro": 12.6, "carb": 1.1, "fat": 11.2,"fib": 0.0,
        "iron": 1.83, "ca": 50, "b12": 0.89, "vd": 2.0,  "zn": 1.10,
        "na": 124, "k": 126, "mgm": 10,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["eggs"], "veg": True, "vegan": False, "pesc": True,
    },
    "egg_white": {
        "desc": "Egg white, cooked",
        "cal": 52,  "pro": 10.9, "carb": 0.7, "fat": 0.2, "fib": 0.0,
        "iron": 0.08, "ca": 7,  "b12": 0.09, "vd": 0.0,  "zn": 0.03,
        "na": 166, "k": 163, "mgm": 11,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["eggs"], "veg": True, "vegan": False, "pesc": True,
    },

    # ── SOY / PLANT PROTEINS ─────────────────────────────────────────────────
    "tofu_firm": {
        "desc": "Tofu, firm, raw",
        "cal": 76,  "pro": 8.1,  "carb": 1.9, "fat": 4.8, "fib": 0.3,
        "iron": 2.66, "ca": 350,"b12": 0.0,  "vd": 0.0,  "zn": 0.80,
        "na": 7,   "k": 121, "mgm": 30,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["soy"], "veg": True, "vegan": True, "pesc": True,
    },
    "tempeh": {
        "desc": "Tempeh, cooked",
        "cal": 193, "pro": 19.0, "carb": 9.4, "fat": 11.0,"fib": 0.0,
        "iron": 2.29, "ca": 96, "b12": 0.0,  "vd": 0.0,  "zn": 1.72,
        "na": 14,  "k": 401, "mgm": 81,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["soy"], "veg": True, "vegan": True, "pesc": True,
    },
    "edamame": {
        "desc": "Edamame, shelled, cooked",
        "cal": 121, "pro": 11.9, "carb": 8.9, "fat": 5.2, "fib": 5.2,
        "iron": 2.27, "ca": 63, "b12": 0.0,  "vd": 0.0,  "zn": 1.37,
        "na": 6,   "k": 436, "mgm": 64,  "gi": 18,
        "fodmap": "high", "fodmap_triggers": ["soy", "GOS"],
        "gerd_safe": True, "allergens": ["soy"], "veg": True, "vegan": True, "pesc": True,
    },
    "seitan": {
        "desc": "Seitan (wheat gluten), cooked",
        "cal": 370, "pro": 75.0, "carb": 14.0,"fat": 1.9, "fib": 0.6,
        "iron": 5.20, "ca": 142,"b12": 0.0,  "vd": 0.0,  "zn": 2.74,
        "na": 400, "k": 104, "mgm": 24,  "gi": 30,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },

    # ── LEGUMES ──────────────────────────────────────────────────────────────
    "lentils": {
        "desc": "Lentils, cooked",
        "cal": 116, "pro": 9.0,  "carb": 20.1,"fat": 0.4, "fib": 7.9,
        "iron": 3.33, "ca": 19, "b12": 0.0,  "vd": 0.0,  "zn": 1.27,
        "na": 2,   "k": 369, "mgm": 36,  "gi": 32,
        "fodmap": "low",  "fodmap_triggers": [],   # ½ cup low FODMAP
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "chickpeas": {
        "desc": "Chickpeas (garbanzo beans), cooked",
        "cal": 164, "pro": 8.9,  "carb": 27.4,"fat": 2.6, "fib": 7.6,
        "iron": 2.89, "ca": 49, "b12": 0.0,  "vd": 0.0,  "zn": 1.53,
        "na": 7,   "k": 291, "mgm": 48,  "gi": 28,
        "fodmap": "high", "fodmap_triggers": ["GOS"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "black_beans": {
        "desc": "Black beans, cooked",
        "cal": 132, "pro": 8.9,  "carb": 23.7,"fat": 0.5, "fib": 8.7,
        "iron": 2.10, "ca": 27, "b12": 0.0,  "vd": 0.0,  "zn": 1.17,
        "na": 1,   "k": 355, "mgm": 70,  "gi": 30,
        "fodmap": "high", "fodmap_triggers": ["GOS"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "kidney_beans": {
        "desc": "Kidney beans, cooked",
        "cal": 127, "pro": 8.7,  "carb": 22.8,"fat": 0.5, "fib": 6.4,
        "iron": 2.59, "ca": 28, "b12": 0.0,  "vd": 0.0,  "zn": 1.07,
        "na": 2,   "k": 403, "mgm": 45,  "gi": 24,
        "fodmap": "high", "fodmap_triggers": ["GOS"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "navy_beans": {
        "desc": "Navy beans, cooked",
        "cal": 140, "pro": 8.2,  "carb": 25.6,"fat": 0.6, "fib": 10.5,
        "iron": 2.36, "ca": 69, "b12": 0.0,  "vd": 0.0,  "zn": 1.03,
        "na": 0,   "k": 389, "mgm": 53,  "gi": 31,
        "fodmap": "high", "fodmap_triggers": ["GOS"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "split_peas": {
        "desc": "Split Peas, cooked",
        "cal": 118, "pro": 8.3,  "carb": 21.1,"fat": 0.4, "fib": 8.3,
        "iron": 1.29, "ca": 14, "b12": 0.0,  "vd": 0.0,  "zn": 1.00,
        "na": 2,   "k": 362, "mgm": 36,  "gi": 25,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "pinto_beans": {
        "desc": "Pinto beans, cooked",
        "cal": 143, "pro": 9.0,  "carb": 26.9,"fat": 0.7, "fib": 9.0,
        "iron": 2.24, "ca": 46, "b12": 0.0,  "vd": 0.0,  "zn": 1.08,
        "na": 1,   "k": 436, "mgm": 50,  "gi": 39,
        "fodmap": "high", "fodmap_triggers": ["GOS"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },

    # ── DAIRY ────────────────────────────────────────────────────────────────
    "greek_yogurt_whole": {
        "desc": "Greek Yogurt, plain, whole milk",
        "cal": 97,  "pro": 9.0,  "carb": 3.6, "fat": 5.0, "fib": 0.0,
        "iron": 0.07, "ca": 100,"b12": 0.75, "vd": 0.0,  "zn": 0.52,
        "na": 36,  "k": 141, "mgm": 11,  "gi": 11,
        "fodmap": "high", "fodmap_triggers": ["lactose"],
        "gerd_safe": True, "allergens": ["dairy"], "veg": True, "vegan": False, "pesc": True,
    },
    "cottage_cheese_2pct": {
        "desc": "Cottage Cheese, 2% milkfat",
        "cal": 90,  "pro": 11.1, "carb": 3.4, "fat": 2.5, "fib": 0.0,
        "iron": 0.07, "ca": 83, "b12": 0.43, "vd": 0.0,  "zn": 0.47,
        "na": 308, "k": 104, "mgm": 8,   "gi": 10,
        "fodmap": "high", "fodmap_triggers": ["lactose"],
        "gerd_safe": True, "allergens": ["dairy"], "veg": True, "vegan": False, "pesc": True,
    },
    "feta_cheese": {
        "desc": "Feta Cheese",
        "cal": 264, "pro": 14.2, "carb": 4.1, "fat": 21.3,"fib": 0.0,
        "iron": 0.65, "ca": 493,"b12": 1.69, "vd": 0.0,  "zn": 2.88,
        "na": 1116,"k": 62,  "mgm": 19,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],    # aged/hard cheese low FODMAP
        "gerd_safe": True, "allergens": ["dairy"], "veg": True, "vegan": False, "pesc": True,
    },
    "parmesan": {
        "desc": "Parmesan Cheese, grated",
        "cal": 431, "pro": 38.5, "carb": 4.1, "fat": 28.6,"fib": 0.0,
        "iron": 0.82, "ca": 1109,"b12": 1.20,"vd": 0.0,  "zn": 2.75,
        "na": 1529,"k": 92,  "mgm": 44,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["dairy"], "veg": True, "vegan": False, "pesc": True,
    },
    "mozzarella_skim": {
        "desc": "Mozzarella, part-skim",
        "cal": 254, "pro": 24.3, "carb": 2.8, "fat": 15.9,"fib": 0.0,
        "iron": 0.44, "ca": 516,"b12": 0.65, "vd": 0.0,  "zn": 2.92,
        "na": 486, "k": 76,  "mgm": 20,  "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["dairy"], "veg": True, "vegan": False, "pesc": True,
    },

    # ── GRAINS ───────────────────────────────────────────────────────────────
    "brown_rice": {
        "desc": "Brown Rice, medium grain, cooked",
        "cal": 112, "pro": 2.4,  "carb": 23.5,"fat": 0.9, "fib": 1.8,
        "iron": 0.53, "ca": 3,  "b12": 0.0,  "vd": 0.0,  "zn": 0.71,
        "na": 5,   "k": 79,  "mgm": 44,  "gi": 50,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "white_rice": {
        "desc": "White Rice, long-grain, cooked",
        "cal": 130, "pro": 2.7,  "carb": 28.2,"fat": 0.3, "fib": 0.4,
        "iron": 1.49, "ca": 10, "b12": 0.0,  "vd": 0.0,  "zn": 0.49,
        "na": 1,   "k": 35,  "mgm": 12,  "gi": 72,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "quinoa": {
        "desc": "Quinoa, cooked",
        "cal": 120, "pro": 4.4,  "carb": 21.3,"fat": 1.9, "fib": 2.8,
        "iron": 1.49, "ca": 17, "b12": 0.0,  "vd": 0.0,  "zn": 1.09,
        "na": 7,   "k": 172, "mgm": 64,  "gi": 53,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "oatmeal_rolled": {
        "desc": "Oatmeal, rolled oats, cooked with water",
        "cal": 71,  "pro": 2.5,  "carb": 12.5,"fat": 1.5, "fib": 1.7,
        "iron": 0.84, "ca": 11, "b12": 0.0,  "vd": 0.0,  "zn": 0.72,
        "na": 49,  "k": 61,  "mgm": 18,  "gi": 55,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["gluten"],  # cross-contamination risk
        "veg": True, "vegan": True, "pesc": True,
    },
    "oatmeal_steel_cut": {
        "desc": "Steel-cut Oats, cooked",
        "cal": 68,  "pro": 2.4,  "carb": 11.9,"fat": 1.4, "fib": 2.0,
        "iron": 0.82, "ca": 10, "b12": 0.0,  "vd": 0.0,  "zn": 0.70,
        "na": 43,  "k": 57,  "mgm": 17,  "gi": 42,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["gluten"],
        "veg": True, "vegan": True, "pesc": True,
    },
    "sweet_potato": {
        "desc": "Sweet Potato, baked with skin",
        "cal": 90,  "pro": 2.0,  "carb": 20.7,"fat": 0.1, "fib": 3.3,
        "iron": 0.69, "ca": 38, "b12": 0.0,  "vd": 0.0,  "zn": 0.32,
        "na": 36,  "k": 475, "mgm": 27,  "gi": 61,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "potato_baked": {
        "desc": "Potato, baked, flesh and skin",
        "cal": 93,  "pro": 2.5,  "carb": 21.1,"fat": 0.1, "fib": 2.2,
        "iron": 0.52, "ca": 12, "b12": 0.0,  "vd": 0.0,  "zn": 0.35,
        "na": 10,  "k": 535, "mgm": 28,  "gi": 85,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "pasta_whole_wheat": {
        "desc": "Whole Wheat Pasta, cooked",
        "cal": 124, "pro": 5.3,  "carb": 24.8,"fat": 1.0, "fib": 4.5,
        "iron": 1.39, "ca": 21, "b12": 0.0,  "vd": 0.0,  "zn": 1.23,
        "na": 3,   "k": 89,  "mgm": 45,  "gi": 42,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },
    "pasta_white": {
        "desc": "White Pasta, enriched, cooked",
        "cal": 158, "pro": 5.8,  "carb": 30.9,"fat": 0.9, "fib": 1.8,
        "iron": 0.68, "ca": 5,  "b12": 0.0,  "vd": 0.0,  "zn": 0.52,
        "na": 2,   "k": 45,  "mgm": 18,  "gi": 61,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },
    "barley": {
        "desc": "Barley, cooked",
        "cal": 123, "pro": 2.3,  "carb": 28.2,"fat": 0.4, "fib": 3.8,
        "iron": 1.33, "ca": 11, "b12": 0.0,  "vd": 0.0,  "zn": 0.82,
        "na": 3,   "k": 93,  "mgm": 22,  "gi": 28,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },
    "bulgur": {
        "desc": "Bulgur, cooked",
        "cal": 83,  "pro": 3.1,  "carb": 18.6,"fat": 0.2, "fib": 4.5,
        "iron": 1.03, "ca": 10, "b12": 0.0,  "vd": 0.0,  "zn": 0.57,
        "na": 5,   "k": 68,  "mgm": 32,  "gi": 46,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },
    "millet": {
        "desc": "Millet, cooked",
        "cal": 119, "pro": 3.5,  "carb": 23.7,"fat": 1.0, "fib": 1.3,
        "iron": 0.63, "ca": 2,  "b12": 0.0,  "vd": 0.0,  "zn": 0.62,
        "na": 2,   "k": 62,  "mgm": 26,  "gi": 71,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "buckwheat": {
        "desc": "Buckwheat, groats, cooked",
        "cal": 92,  "pro": 3.4,  "carb": 20.0,"fat": 0.6, "fib": 2.7,
        "iron": 0.75, "ca": 7,  "b12": 0.0,  "vd": 0.0,  "zn": 0.58,
        "na": 4,   "k": 88,  "mgm": 42,  "gi": 45,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "corn_tortilla": {
        "desc": "Corn Tortilla, prepared",
        "cal": 218, "pro": 5.7,  "carb": 46.0,"fat": 2.7, "fib": 6.7,
        "iron": 3.07, "ca": 96, "b12": 0.0,  "vd": 0.0,  "zn": 1.16,
        "na": 47,  "k": 195, "mgm": 58,  "gi": 52,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "polenta": {
        "desc": "Polenta, cooked",
        "cal": 71,  "pro": 1.7,  "carb": 15.0,"fat": 0.5, "fib": 1.0,
        "iron": 0.25, "ca": 4,  "b12": 0.0,  "vd": 0.0,  "zn": 0.28,
        "na": 239, "k": 37,  "mgm": 12,  "gi": 68,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "farro": {
        "desc": "Farro, cooked",
        "cal": 130, "pro": 5.1,  "carb": 26.0,"fat": 0.5, "fib": 3.5,
        "iron": 1.42, "ca": 19, "b12": 0.0,  "vd": 0.0,  "zn": 1.40,
        "na": 3,   "k": 98,  "mgm": 48,  "gi": 40,
        "fodmap": "high", "fodmap_triggers": ["fructans", "wheat"],
        "gerd_safe": True, "allergens": ["gluten"], "veg": True, "vegan": True, "pesc": True,
    },
    "amaranth": {
        "desc": "Amaranth grain, cooked",
        "cal": 102, "pro": 3.8,  "carb": 18.7,"fat": 1.6, "fib": 2.1,
        "iron": 2.10, "ca": 47, "b12": 0.0,  "vd": 0.0,  "zn": 0.86,
        "na": 6,   "k": 135, "mgm": 65,  "gi": 35,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "teff": {
        "desc": "Teff grain, cooked",
        "cal": 101, "pro": 3.9,  "carb": 19.9,"fat": 0.7, "fib": 2.8,
        "iron": 2.44, "ca": 87, "b12": 0.0,  "vd": 0.0,  "zn": 0.87,
        "na": 9,   "k": 122, "mgm": 33,  "gi": 57,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "wild_rice": {
        "desc": "Wild Rice, cooked",
        "cal": 101, "pro": 4.0,  "carb": 21.3,"fat": 0.3, "fib": 1.8,
        "iron": 0.60, "ca": 3,  "b12": 0.0,  "vd": 0.0,  "zn": 2.20,
        "na": 3,   "k": 101, "mgm": 32,  "gi": 45,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "plantain_cooked": {
        "desc": "Plantain, cooked",
        "cal": 116, "pro": 0.8,  "carb": 31.2,"fat": 0.2, "fib": 1.8,
        "iron": 0.49, "ca": 2,  "b12": 0.0,  "vd": 0.0,  "zn": 0.10,
        "na": 3,   "k": 465, "mgm": 32,  "gi": 65,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },

    # ── VEGETABLES ───────────────────────────────────────────────────────────
    "spinach_cooked": {
        "desc": "Spinach, cooked",
        "cal": 23,  "pro": 3.0,  "carb": 3.8, "fat": 0.4, "fib": 2.4,
        "iron": 3.57, "ca": 136,"b12": 0.0,  "vd": 0.0,  "zn": 0.81,
        "na": 70,  "k": 466, "mgm": 87,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "kale_cooked": {
        "desc": "Kale, cooked",
        "cal": 33,  "pro": 2.9,  "carb": 6.9, "fat": 0.5, "fib": 2.0,
        "iron": 1.17, "ca": 112,"b12": 0.0,  "vd": 0.0,  "zn": 0.34,
        "na": 23,  "k": 228, "mgm": 18,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "broccoli_cooked": {
        "desc": "Broccoli, cooked",
        "cal": 35,  "pro": 2.4,  "carb": 7.2, "fat": 0.4, "fib": 3.3,
        "iron": 0.67, "ca": 40, "b12": 0.0,  "vd": 0.0,  "zn": 0.45,
        "na": 33,  "k": 293, "mgm": 21,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "cauliflower_cooked": {
        "desc": "Cauliflower, cooked",
        "cal": 23,  "pro": 1.9,  "carb": 4.6, "fat": 0.5, "fib": 2.3,
        "iron": 0.32, "ca": 16, "b12": 0.0,  "vd": 0.0,  "zn": 0.21,
        "na": 15,  "k": 142, "mgm": 10,  "gi": 15,
        "fodmap": "high", "fodmap_triggers": ["mannitol"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "zucchini_cooked": {
        "desc": "Zucchini, cooked",
        "cal": 17,  "pro": 1.2,  "carb": 3.6, "fat": 0.2, "fib": 1.2,
        "iron": 0.41, "ca": 15, "b12": 0.0,  "vd": 0.0,  "zn": 0.31,
        "na": 0,   "k": 264, "mgm": 18,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "bell_pepper_red": {
        "desc": "Red Bell Pepper, raw",
        "cal": 31,  "pro": 1.0,  "carb": 7.2, "fat": 0.3, "fib": 2.1,
        "iron": 0.43, "ca": 7,  "b12": 0.0,  "vd": 0.0,  "zn": 0.25,
        "na": 4,   "k": 211, "mgm": 12,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "carrots_cooked": {
        "desc": "Carrots, cooked",
        "cal": 35,  "pro": 0.8,  "carb": 8.2, "fat": 0.2, "fib": 2.9,
        "iron": 0.34, "ca": 30, "b12": 0.0,  "vd": 0.0,  "zn": 0.22,
        "na": 58,  "k": 235, "mgm": 10,  "gi": 39,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "asparagus_cooked": {
        "desc": "Asparagus, cooked",
        "cal": 22,  "pro": 2.4,  "carb": 4.1, "fat": 0.2, "fib": 1.8,
        "iron": 2.14, "ca": 23, "b12": 0.0,  "vd": 0.0,  "zn": 0.48,
        "na": 14,  "k": 202, "mgm": 14,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "green_beans_cooked": {
        "desc": "Green Beans, cooked",
        "cal": 31,  "pro": 1.8,  "carb": 7.1, "fat": 0.2, "fib": 3.4,
        "iron": 1.04, "ca": 37, "b12": 0.0,  "vd": 0.0,  "zn": 0.24,
        "na": 1,   "k": 152, "mgm": 18,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "mushrooms_cooked": {
        "desc": "White Mushrooms, cooked",
        "cal": 18,  "pro": 2.2,  "carb": 3.3, "fat": 0.3, "fib": 1.6,
        "iron": 0.59, "ca": 3,  "b12": 0.0,  "vd": 0.2,  "zn": 0.49,
        "na": 9,   "k": 326, "mgm": 12,  "gi": 15,
        "fodmap": "high", "fodmap_triggers": ["mannitol"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "brussels_sprouts": {
        "desc": "Brussels Sprouts, cooked",
        "cal": 36,  "pro": 2.6,  "carb": 7.1, "fat": 0.5, "fib": 3.8,
        "iron": 1.50, "ca": 30, "b12": 0.0,  "vd": 0.0,  "zn": 0.40,
        "na": 25,  "k": 317, "mgm": 20,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "peas_cooked": {
        "desc": "Green Peas, cooked",
        "cal": 84,  "pro": 5.4,  "carb": 15.6,"fat": 0.2, "fib": 5.5,
        "iron": 1.54, "ca": 22, "b12": 0.0,  "vd": 0.0,  "zn": 1.19,
        "na": 3,   "k": 244, "mgm": 33,  "gi": 51,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "eggplant_cooked": {
        "desc": "Eggplant, cooked",
        "cal": 25,  "pro": 0.8,  "carb": 6.6, "fat": 0.2, "fib": 2.5,
        "iron": 0.23, "ca": 7,  "b12": 0.0,  "vd": 0.0,  "zn": 0.12,
        "na": 1,   "k": 123, "mgm": 11,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "bok_choy_cooked": {
        "desc": "Bok Choy, cooked",
        "cal": 12,  "pro": 1.6,  "carb": 2.0, "fat": 0.2, "fib": 1.0,
        "iron": 0.80, "ca": 93, "b12": 0.0,  "vd": 0.0,  "zn": 0.13,
        "na": 58,  "k": 252, "mgm": 19,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "beets_cooked": {
        "desc": "Beets, cooked",
        "cal": 44,  "pro": 1.7,  "carb": 10.0,"fat": 0.2, "fib": 2.8,
        "iron": 0.79, "ca": 13, "b12": 0.0,  "vd": 0.0,  "zn": 0.35,
        "na": 77,  "k": 305, "mgm": 23,  "gi": 65,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "swiss_chard_cooked": {
        "desc": "Swiss Chard, cooked",
        "cal": 20,  "pro": 1.9,  "carb": 4.1, "fat": 0.1, "fib": 1.6,
        "iron": 2.26, "ca": 51, "b12": 0.0,  "vd": 0.0,  "zn": 0.29,
        "na": 179, "k": 549, "mgm": 87,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "collard_greens": {
        "desc": "Collard Greens, cooked",
        "cal": 32,  "pro": 2.7,  "carb": 6.3, "fat": 0.6, "fib": 4.0,
        "iron": 0.87, "ca": 210,"b12": 0.0,  "vd": 0.0,  "zn": 0.31,
        "na": 15,  "k": 213, "mgm": 19,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "butternut_squash": {
        "desc": "Butternut Squash, cooked",
        "cal": 45,  "pro": 1.0,  "carb": 11.7,"fat": 0.1, "fib": 2.8,
        "iron": 0.66, "ca": 42, "b12": 0.0,  "vd": 0.0,  "zn": 0.21,
        "na": 4,   "k": 352, "mgm": 27,  "gi": 51,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "cucumber_raw": {
        "desc": "Cucumber, raw",
        "cal": 15,  "pro": 0.7,  "carb": 3.6, "fat": 0.1, "fib": 0.5,
        "iron": 0.28, "ca": 16, "b12": 0.0,  "vd": 0.0,  "zn": 0.20,
        "na": 2,   "k": 147, "mgm": 13,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "arugula_raw": {
        "desc": "Arugula, raw",
        "cal": 25,  "pro": 2.6,  "carb": 3.7, "fat": 0.7, "fib": 1.6,
        "iron": 1.46, "ca": 160,"b12": 0.0,  "vd": 0.0,  "zn": 0.47,
        "na": 27,  "k": 369, "mgm": 47,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },

    # ── FRUITS ───────────────────────────────────────────────────────────────
    "avocado": {
        "desc": "Avocado, raw",
        "cal": 160, "pro": 2.0,  "carb": 8.5, "fat": 14.7,"fib": 6.7,
        "iron": 0.55, "ca": 12, "b12": 0.0,  "vd": 0.0,  "zn": 0.64,
        "na": 7,   "k": 485, "mgm": 29,  "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],  # ¼ avocado low FODMAP
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "blueberries": {
        "desc": "Blueberries, raw",
        "cal": 57,  "pro": 0.7,  "carb": 14.5,"fat": 0.3, "fib": 2.4,
        "iron": 0.28, "ca": 6,  "b12": 0.0,  "vd": 0.0,  "zn": 0.16,
        "na": 1,   "k": 77,  "mgm": 6,   "gi": 53,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "strawberries": {
        "desc": "Strawberries, raw",
        "cal": 32,  "pro": 0.7,  "carb": 7.7, "fat": 0.3, "fib": 2.0,
        "iron": 0.41, "ca": 16, "b12": 0.0,  "vd": 0.0,  "zn": 0.14,
        "na": 1,   "k": 153, "mgm": 13,  "gi": 40,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "banana": {
        "desc": "Banana, raw",
        "cal": 89,  "pro": 1.1,  "carb": 22.8,"fat": 0.3, "fib": 2.6,
        "iron": 0.26, "ca": 5,  "b12": 0.0,  "vd": 0.0,  "zn": 0.15,
        "na": 1,   "k": 358, "mgm": 27,  "gi": 51,
        "fodmap": "low",  "fodmap_triggers": [],   # ripe but not over-ripe
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "kiwi": {
        "desc": "Kiwifruit, raw",
        "cal": 61,  "pro": 1.1,  "carb": 14.7,"fat": 0.5, "fib": 3.0,
        "iron": 0.31, "ca": 34, "b12": 0.0,  "vd": 0.0,  "zn": 0.14,
        "na": 3,   "k": 312, "mgm": 17,  "gi": 47,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "pomegranate_seeds": {
        "desc": "Pomegranate Arils, raw",
        "cal": 83,  "pro": 1.7,  "carb": 18.7,"fat": 1.2, "fib": 4.0,
        "iron": 0.30, "ca": 10, "b12": 0.0,  "vd": 0.0,  "zn": 0.35,
        "na": 3,   "k": 236, "mgm": 12,  "gi": 35,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "orange": {
        "desc": "Orange, raw",
        "cal": 47,  "pro": 0.9,  "carb": 11.8,"fat": 0.1, "fib": 2.4,
        "iron": 0.10, "ca": 40, "b12": 0.0,  "vd": 0.0,  "zn": 0.07,
        "na": 0,   "k": 181, "mgm": 10,  "gi": 43,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": False,  # citrus = GERD trigger
        "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "mango": {
        "desc": "Mango, raw",
        "cal": 60,  "pro": 0.8,  "carb": 15.0,"fat": 0.4, "fib": 1.6,
        "iron": 0.16, "ca": 11, "b12": 0.0,  "vd": 0.0,  "zn": 0.09,
        "na": 1,   "k": 168, "mgm": 10,  "gi": 60,
        "fodmap": "high", "fodmap_triggers": ["excess fructose"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "apple": {
        "desc": "Apple, raw, with skin",
        "cal": 52,  "pro": 0.3,  "carb": 13.8,"fat": 0.2, "fib": 2.4,
        "iron": 0.12, "ca": 6,  "b12": 0.0,  "vd": 0.0,  "zn": 0.04,
        "na": 1,   "k": 107, "mgm": 5,   "gi": 36,
        "fodmap": "high", "fodmap_triggers": ["sorbitol", "excess fructose"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "pear": {
        "desc": "Pear, raw",
        "cal": 57,  "pro": 0.4,  "carb": 15.2,"fat": 0.1, "fib": 3.1,
        "iron": 0.18, "ca": 9,  "b12": 0.0,  "vd": 0.0,  "zn": 0.10,
        "na": 1,   "k": 116, "mgm": 7,   "gi": 38,
        "fodmap": "high", "fodmap_triggers": ["sorbitol", "excess fructose"],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },

    # ── SEEDS / OILS (used as toppings/fats) ─────────────────────────────────
    "chia_seeds": {
        "desc": "Chia Seeds",
        "cal": 486, "pro": 16.5, "carb": 42.1,"fat": 30.7,"fib": 34.4,
        "iron": 7.72, "ca": 631,"b12": 0.0,  "vd": 0.0,  "zn": 4.58,
        "na": 16,  "k": 407, "mgm": 335, "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "flaxseeds_ground": {
        "desc": "Flaxseeds, ground",
        "cal": 534, "pro": 18.3, "carb": 28.9,"fat": 42.2,"fib": 27.3,
        "iron": 5.73, "ca": 255,"b12": 0.0,  "vd": 0.0,  "zn": 4.34,
        "na": 30,  "k": 813, "mgm": 392, "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "hemp_seeds": {
        "desc": "Hemp Seeds, hulled",
        "cal": 553, "pro": 31.6, "carb": 8.7, "fat": 48.8,"fib": 4.0,
        "iron": 7.95, "ca": 70, "b12": 0.0,  "vd": 0.0,  "zn": 9.90,
        "na": 5,   "k": 1200,"mgm": 700, "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "pumpkin_seeds": {
        "desc": "Pumpkin Seeds, raw",
        "cal": 559, "pro": 30.2, "carb": 10.7,"fat": 49.1,"fib": 6.0,
        "iron": 8.82, "ca": 46, "b12": 0.0,  "vd": 0.0,  "zn": 7.81,
        "na": 7,   "k": 809, "mgm": 592, "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "sunflower_seeds": {
        "desc": "Sunflower Seeds, dry roasted",
        "cal": 582, "pro": 19.3, "carb": 24.1,"fat": 51.5,"fib": 11.5,
        "iron": 3.80, "ca": 70, "b12": 0.0,  "vd": 0.0,  "zn": 5.29,
        "na": 3,   "k": 689, "mgm": 129, "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "walnuts": {
        "desc": "Walnuts, raw",
        "cal": 654, "pro": 15.2, "carb": 13.7,"fat": 65.2,"fib": 6.7,
        "iron": 2.91, "ca": 98, "b12": 0.0,  "vd": 0.0,  "zn": 3.09,
        "na": 2,   "k": 441, "mgm": 158, "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["tree_nuts"], "veg": True, "vegan": True, "pesc": True,
    },
    "almonds": {
        "desc": "Almonds, raw",
        "cal": 579, "pro": 21.2, "carb": 21.7,"fat": 49.9,"fib": 12.5,
        "iron": 3.71, "ca": 264,"b12": 0.0,  "vd": 0.0,  "zn": 3.12,
        "na": 1,   "k": 733, "mgm": 270, "gi": 15,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": ["tree_nuts"], "veg": True, "vegan": True, "pesc": True,
    },
    "cashews": {
        "desc": "Cashews, dry roasted",
        "cal": 574, "pro": 15.3, "carb": 32.7,"fat": 46.4,"fib": 3.3,
        "iron": 6.68, "ca": 45, "b12": 0.0,  "vd": 0.0,  "zn": 5.78,
        "na": 16,  "k": 565, "mgm": 273, "gi": 22,
        "fodmap": "high", "fodmap_triggers": ["fructans"],
        "gerd_safe": True, "allergens": ["tree_nuts"], "veg": True, "vegan": True, "pesc": True,
    },
    "tahini": {
        "desc": "Tahini (sesame paste)",
        "cal": 595, "pro": 17.0, "carb": 21.2,"fat": 53.8,"fib": 9.3,
        "iron": 8.95, "ca": 426,"b12": 0.0,  "vd": 0.0,  "zn": 4.62,
        "na": 115, "k": 414, "mgm": 95,  "gi": 1,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "olive_oil": {
        "desc": "Olive Oil, extra virgin",
        "cal": 884, "pro": 0.0,  "carb": 0.0, "fat": 100.0,"fib": 0.0,
        "iron": 0.56, "ca": 1,  "b12": 0.0,  "vd": 0.0,  "zn": 0.0,
        "na": 2,   "k": 1,   "mgm": 0,   "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
    "coconut_oil": {
        "desc": "Coconut Oil",
        "cal": 862, "pro": 0.0,  "carb": 0.0, "fat": 100.0,"fib": 0.0,
        "iron": 0.01, "ca": 0,  "b12": 0.0,  "vd": 0.0,  "zn": 0.0,
        "na": 0,   "k": 0,   "mgm": 0,   "gi": 0,
        "fodmap": "low",  "fodmap_triggers": [],
        "gerd_safe": True, "allergens": [], "veg": True, "vegan": True, "pesc": True,
    },
}
# fmt: on


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — USDA NUTRIENT RETENTION FACTORS (cooking method modifiers)
# Source: USDA ARS "Nutrient Retention Factors, Release 6"
# Applied per-nutrient; values represent fraction of original nutrient retained.
# ─────────────────────────────────────────────────────────────────────────────

# (moisture_factor, iron_r, ca_r, b12_r, vd_r, zn_r, na_r, k_r, mg_r)
RETENTION_FACTORS: dict[str, tuple] = {
    # method         moisture  iron   ca    b12   vd    zn    na    k     mg
    "Roasted":      (0.75,     0.95, 1.00, 0.80, 0.95, 0.95, 0.95, 0.90, 0.90),
    "Grilled":      (0.78,     0.93, 1.00, 0.78, 0.93, 0.93, 0.93, 0.88, 0.88),
    "Baked":        (0.80,     0.97, 1.00, 0.85, 0.97, 0.97, 0.97, 0.92, 0.92),
    "Steamed":      (0.92,     0.92, 0.95, 0.90, 0.90, 0.92, 0.85, 0.88, 0.92),
    "Stir-Fried":   (0.83,     0.95, 0.97, 0.82, 0.93, 0.95, 0.94, 0.90, 0.90),
    "Pan-Seared":   (0.82,     0.94, 1.00, 0.80, 0.92, 0.94, 0.94, 0.90, 0.90),
    "Boiled":       (0.88,     0.88, 0.90, 0.85, 0.85, 0.88, 0.80, 0.85, 0.88),
    "Braised":      (0.82,     0.93, 0.98, 0.82, 0.90, 0.93, 0.90, 0.88, 0.90),
    "Poached":      (0.90,     0.90, 0.92, 0.88, 0.88, 0.90, 0.82, 0.87, 0.90),
    "Air-Fried":    (0.77,     0.95, 1.00, 0.82, 0.94, 0.95, 0.94, 0.91, 0.91),
    "Raw":          (1.00,     1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00),
}


def _apply_retention(base: dict, method: str, serving_g: float) -> dict:
    """
    Compute per-serving (serving_g grams) nutritional values for base ingredient
    after applying USDA retention factors for the given cooking method.
    """
    mf, iron_r, ca_r, b12_r, vd_r, zn_r, na_r, k_r, mg_r = RETENTION_FACTORS[method]
    s = serving_g / 100.0   # scale from per-100g to per-serving

    # Moisture concentration factor: as water evaporates, nutrients concentrate
    # in remaining mass. Macros scale inversely with moisture.
    c = 1.0 / mf  # concentration multiplier

    cal  = round(base["cal"]  * s * c, 1)
    pro  = round(base["pro"]  * s * c, 1)
    fat  = round(base["fat"]  * s * c, 1)
    carb = round(base["carb"] * s * c, 1)
    fib  = round(base["fib"]  * s * c, 1)

    iron = round(base["iron"] * s * c * iron_r, 2)
    ca   = round(base["ca"]   * s * c * ca_r,   1)
    b12  = round(base["b12"]  * s * c * b12_r,  2)
    vd   = round(base["vd"]   * s * c * vd_r,   2)
    zn   = round(base["zn"]   * s * c * zn_r,   2)
    na   = round(base["na"]   * s * c * na_r,   1)
    k    = round(base["k"]    * s * c * k_r,    1)
    mgm  = round(base["mgm"]  * s * c * mg_r,   1)

    return dict(cal=cal, pro=pro, carb=carb, fat=fat, fib=fib,
                iron=iron, ca=ca, b12=b12, vd=vd, zn=zn,
                na=na, k=k, mgm=mgm)


def _sum_components(component_list: list[tuple]) -> dict:
    """
    Sum nutritional contributions from multiple meal components.
    component_list: [(ingredient_key, method, serving_g), ...]
    """
    totals = dict(cal=0.0, pro=0.0, carb=0.0, fat=0.0, fib=0.0,
                  iron=0.0, ca=0.0, b12=0.0, vd=0.0, zn=0.0,
                  na=0.0, k=0.0, mgm=0.0)
    for ing_key, method, serving_g in component_list:
        if ing_key not in INGREDIENTS:
            continue
        contrib = _apply_retention(INGREDIENTS[ing_key], method, serving_g)
        for key in totals:
            totals[key] += contrib[key]
    return {k: round(v, 2) for k, v in totals.items()}


def _weighted_gi(component_list: list[tuple]) -> int:
    """
    Carb-weighted average GI across meal components.
    Returns 0 if no carb-containing components.
    """
    total_carbs = 0.0
    gi_x_carb   = 0.0
    for ing_key, method, serving_g in component_list:
        if ing_key not in INGREDIENTS:
            continue
        ing = INGREDIENTS[ing_key]
        mf = RETENTION_FACTORS[method][0]
        carb_g = ing["carb"] * serving_g / 100 / mf
        gi     = ing.get("gi", 0)
        gi_x_carb   += gi * carb_g
        total_carbs += carb_g
    return int(gi_x_carb / total_carbs) if total_carbs > 0 else 0


def _clinical_flags(component_list: list[tuple]) -> dict:
    """Merge clinical flags across all components (most restrictive wins)."""
    flags = dict(
        fodmap="low", is_low_fodmap=1,
        gerd_safe=True, is_gerd_safe=1,
        allergens=set(),
        veg=True, vegan=True, pesc=True,
        fodmap_triggers=[],
    )
    for ing_key, _, _ in component_list:
        if ing_key not in INGREDIENTS:
            continue
        ing = INGREDIENTS[ing_key]
        if ing.get("fodmap") == "high":
            flags["fodmap"] = "high"
            flags["is_low_fodmap"] = 0
            flags["fodmap_triggers"] = list(set(
                flags["fodmap_triggers"] + ing.get("fodmap_triggers", [])
            ))
        if not ing.get("gerd_safe", True):
            flags["gerd_safe"] = False
            flags["is_gerd_safe"] = 0
        flags["allergens"].update(ing.get("allergens", []))
        if not ing.get("veg", True):
            flags["veg"] = False
        if not ing.get("vegan", True):
            flags["vegan"] = False
        if not ing.get("pesc", True):
            flags["pesc"] = False

    flags["allergens"] = list(flags["allergens"])
    return flags


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — MEAL BLUEPRINTS
# Each blueprint defines (primary, grain, vegetable, fat_key, servings_g,
#                         name_template, meal_type, cuisines)
# Components: list of (ingredient_key, method, serving_g)
# ─────────────────────────────────────────────────────────────────────────────

BREAKFAST_PROTEINS = [
    "egg_whole", "tofu_firm", "egg_white", "tempeh", "greek_yogurt_whole",
    "cottage_cheese_2pct", "salmon_atlantic", "sardines_water", "lentils",
    "chickpeas", "black_beans", "edamame", "hemp_seeds", "chia_seeds",
    "tuna_canned_water", "mackerel", "turkey_breast", "chicken_breast",
    "tilapia", "split_peas",
]

BREAKFAST_GRAINS = [
    "oatmeal_rolled", "oatmeal_steel_cut", "quinoa", "brown_rice", "buckwheat",
    "amaranth", "teff", "millet", "wild_rice", "corn_tortilla",
    "polenta", "sweet_potato", "plantain_cooked",
]

BREAKFAST_TOPPINGS = [
    "blueberries", "strawberries", "banana", "kiwi", "pomegranate_seeds",
    "avocado", "spinach_cooked", "chia_seeds", "flaxseeds_ground", "pumpkin_seeds",
    "sunflower_seeds", "almonds", "walnuts",
]

BREAKFAST_CUISINES = [
    "American", "Japanese", "Indian", "Mediterranean", "Mexican",
    "Middle Eastern", "Korean", "Ethiopian",
]

LUNCH_PROTEINS = [
    "chicken_breast", "turkey_breast", "salmon_atlantic", "tuna_canned_water",
    "cod_pacific", "tilapia", "halibut", "shrimp", "scallops", "tofu_firm",
    "tempeh", "lentils", "chickpeas", "black_beans", "kidney_beans",
    "edamame", "sardines_water", "mackerel", "mussels", "beef_sirloin",
    "ground_turkey", "pork_tenderloin", "split_peas", "navy_beans", "pinto_beans",
]

LUNCH_GRAINS = [
    "brown_rice", "quinoa", "wild_rice", "buckwheat", "farro", "millet",
    "barley", "bulgur", "teff", "amaranth", "sweet_potato", "potato_baked",
    "corn_tortilla", "pasta_whole_wheat",
]

LUNCH_VEGETABLES = [
    "spinach_cooked", "kale_cooked", "broccoli_cooked", "zucchini_cooked",
    "bell_pepper_red", "carrots_cooked", "asparagus_cooked", "green_beans_cooked",
    "brussels_sprouts", "peas_cooked", "bok_choy_cooked", "beets_cooked",
    "swiss_chard_cooked", "butternut_squash", "arugula_raw",
]

LUNCH_CUISINES = [
    "American", "Italian", "Indian", "Mediterranean", "Asian",
    "Mexican", "Middle Eastern", "Japanese", "Thai",
]

DINNER_PROTEINS = [
    "salmon_atlantic", "salmon_sockeye", "cod_pacific", "halibut",
    "mackerel", "tilapia", "shrimp", "scallops", "mussels",
    "chicken_breast", "chicken_thigh", "turkey_breast", "beef_sirloin",
    "ground_beef_lean", "pork_tenderloin", "lamb_leg", "bison_ground",
    "tofu_firm", "tempeh", "lentils", "chickpeas", "black_beans",
    "navy_beans", "pinto_beans", "split_peas",
]

DINNER_BASES = [
    "brown_rice", "quinoa", "wild_rice", "sweet_potato", "potato_baked",
    "butternut_squash", "pasta_whole_wheat", "polenta", "millet",
    "amaranth", "teff", "buckwheat", "corn_tortilla", "plantain_cooked",
]

DINNER_VEGS = [
    "spinach_cooked", "kale_cooked", "broccoli_cooked", "asparagus_cooked",
    "green_beans_cooked", "brussels_sprouts", "zucchini_cooked",
    "collard_greens", "swiss_chard_cooked", "bok_choy_cooked",
    "eggplant_cooked", "cauliflower_cooked",
]

DINNER_CUISINES = [
    "American", "Italian", "Indian", "Mediterranean", "French",
    "Mexican", "Middle Eastern", "Japanese", "Thai", "Korean",
]

BREAKFAST_METHODS  = ["Baked", "Steamed", "Raw", "Boiled", "Stir-Fried"]
PROTEIN_METHODS    = ["Grilled", "Baked", "Pan-Seared", "Steamed", "Roasted",
                      "Stir-Fried", "Boiled", "Braised", "Poached", "Air-Fried"]
VEG_METHODS        = ["Steamed", "Roasted", "Stir-Fried", "Boiled", "Raw",
                      "Baked", "Braised"]
GRAIN_METHODS      = ["Boiled", "Steamed"]

# Cooking method selection is deterministic via index arithmetic (no random).
def _pick(lst: list, idx: int) -> str:
    return lst[idx % len(lst)]


def _generate_breakfast_records() -> list[dict]:
    records = []
    idx = 0
    for cuisine in BREAKFAST_CUISINES:
        for grain_key in BREAKFAST_GRAINS:
            for prot_key in BREAKFAST_PROTEINS:
                for top_key in BREAKFAST_TOPPINGS:
                    g_method = _pick(GRAIN_METHODS,   idx)
                    p_method = _pick(BREAKFAST_METHODS, idx)
                    t_method = "Raw"

                    grain_g = 120.0
                    prot_g  = 80.0
                    top_g   = 40.0

                    components = [
                        (grain_key, g_method, grain_g),
                        (prot_key,  p_method, prot_g),
                        (top_key,   t_method, top_g),
                    ]
                    nuts = _sum_components(components)
                    clin = _clinical_flags(components)
                    gi   = _weighted_gi(components)

                    grain_desc = INGREDIENTS[grain_key]["desc"].split(",")[0]
                    prot_desc  = INGREDIENTS[prot_key]["desc"].split(",")[0]
                    top_desc   = INGREDIENTS[top_key]["desc"].split(",")[0]
                    name = f"{cuisine} {grain_desc} with {prot_desc} and {top_desc}"

                    records.append(_build_row(name, "Breakfast", nuts, clin, gi))
                    idx += 1
    return records


def _generate_lunch_records() -> list[dict]:
    records = []
    idx = 0
    for cuisine in LUNCH_CUISINES:
        for prot_key in LUNCH_PROTEINS:
            for grain_key in LUNCH_GRAINS:
                for veg_key in LUNCH_VEGETABLES:
                    p_method = _pick(PROTEIN_METHODS, idx)
                    g_method = _pick(GRAIN_METHODS,   idx)
                    v_method = _pick(VEG_METHODS,      idx)
                    fat_key  = "olive_oil" if idx % 3 != 0 else "coconut_oil"

                    prot_g  = 140.0
                    grain_g = 130.0
                    veg_g   = 90.0
                    fat_g   = 8.0

                    components = [
                        (prot_key,  p_method, prot_g),
                        (grain_key, g_method, grain_g),
                        (veg_key,   v_method, veg_g),
                        (fat_key,   "Raw",    fat_g),
                    ]
                    nuts = _sum_components(components)
                    clin = _clinical_flags(components)
                    gi   = _weighted_gi(components)

                    prot_desc  = INGREDIENTS[prot_key]["desc"].split(",")[0]
                    grain_desc = INGREDIENTS[grain_key]["desc"].split(",")[0]
                    veg_desc   = INGREDIENTS[veg_key]["desc"].split(",")[0]
                    name = f"{cuisine} {p_method} {prot_desc} with {grain_desc} and {veg_desc}"

                    records.append(_build_row(name, "Lunch", nuts, clin, gi))
                    idx += 1
    return records


def _generate_dinner_records() -> list[dict]:
    records = []
    idx = 0
    for cuisine in DINNER_CUISINES:
        for prot_key in DINNER_PROTEINS:
            for base_key in DINNER_BASES:
                for veg_key in DINNER_VEGS:
                    p_method = _pick(PROTEIN_METHODS, idx)
                    b_method = _pick(GRAIN_METHODS,   idx)
                    v_method = _pick(VEG_METHODS,      idx)
                    fat_key  = "olive_oil" if idx % 3 != 0 else "coconut_oil"

                    prot_g  = 160.0
                    base_g  = 140.0
                    veg_g   = 100.0
                    fat_g   = 10.0

                    components = [
                        (prot_key,  p_method, prot_g),
                        (base_key,  b_method, base_g),
                        (veg_key,   v_method, veg_g),
                        (fat_key,   "Raw",    fat_g),
                    ]
                    nuts = _sum_components(components)
                    clin = _clinical_flags(components)
                    gi   = _weighted_gi(components)

                    prot_desc  = INGREDIENTS[prot_key]["desc"].split(",")[0]
                    base_desc  = INGREDIENTS[base_key]["desc"].split(",")[0]
                    veg_desc   = INGREDIENTS[veg_key]["desc"].split(",")[0]
                    name = f"{cuisine} {p_method} {prot_desc} over {base_desc} with {veg_desc}"

                    records.append(_build_row(name, "Dinner", nuts, clin, gi))
                    idx += 1
    return records


def _allergen_flags(allergens: list[str]) -> dict:
    tags = ["gluten", "dairy", "eggs", "soy", "tree_nuts", "shellfish", "fish", "peanuts"]
    return {f"contains_{t}": int(t in allergens) for t in tags}


def _build_row(name: str, meal_type: str, nuts: dict,
               clin: dict, gi: int) -> dict:
    row = {
        "name":          name,
        "meal_type":     meal_type,
        "calories":      nuts["cal"],
        "protein":       nuts["pro"],
        "carbs":         nuts["carb"],
        "fat":           nuts["fat"],
        "fiber":         nuts["fib"],
        "iron":          nuts["iron"],
        "calcium":       nuts["ca"],
        "vitamin_b12":   nuts["b12"],
        "vitamin_d":     nuts["vd"],
        "zinc":          nuts["zn"],
        "sodium":        nuts["na"],
        "potassium":     nuts["k"],
        "magnesium":     nuts["mgm"],
        "glycemic_index":gi,
        "is_low_fodmap": clin["is_low_fodmap"],
        "fodmap_triggers": ",".join(clin["fodmap_triggers"]),
        "is_gerd_safe":  clin["is_gerd_safe"],
        "is_vegetarian": int(clin["veg"]),
        "is_vegan":      int(clin["vegan"]),
        "is_pescatarian":int(clin["pesc"]),
        "is_diabetic_friendly": int(gi <= 55 or gi == 0),
        "is_dash_compliant":    int(nuts["na"] <= 600),
    }
    row.update(_allergen_flags(clin["allergens"]))
    return row


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — BUILD & SEED DATABASE
# ─────────────────────────────────────────────────────────────────────────────

CREATE_MEALS_SQL = """
CREATE TABLE IF NOT EXISTS meals (
    meal_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name                 TEXT    NOT NULL UNIQUE,
    meal_type            TEXT    NOT NULL,
    calories             REAL,
    protein              REAL,
    carbs                REAL,
    fat                  REAL,
    fiber                REAL,
    iron                 REAL,
    calcium              REAL,
    vitamin_b12          REAL,
    vitamin_d            REAL,
    zinc                 REAL,
    sodium               REAL,
    potassium            REAL,
    magnesium            REAL,
    glycemic_index       INTEGER,
    is_low_fodmap        INTEGER,
    fodmap_triggers      TEXT,
    is_gerd_safe         INTEGER,
    is_vegetarian        INTEGER,
    is_vegan             INTEGER,
    is_pescatarian       INTEGER,
    is_diabetic_friendly INTEGER,
    is_dash_compliant    INTEGER,
    contains_gluten      INTEGER DEFAULT 0,
    contains_dairy       INTEGER DEFAULT 0,
    contains_eggs        INTEGER DEFAULT 0,
    contains_soy         INTEGER DEFAULT 0,
    contains_tree_nuts   INTEGER DEFAULT 0,
    contains_shellfish   INTEGER DEFAULT 0,
    contains_fish        INTEGER DEFAULT 0,
    contains_peanuts     INTEGER DEFAULT 0
);
"""

CREATE_INGREDIENTS_SQL = """
CREATE TABLE IF NOT EXISTS ingredients (
    ing_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    description    TEXT,
    category       TEXT,
    calories       REAL,
    protein        REAL,
    carbs          REAL,
    fat            REAL,
    fiber          REAL,
    iron           REAL,
    calcium        REAL,
    vitamin_b12    REAL,
    vitamin_d      REAL,
    zinc           REAL,
    sodium         REAL,
    potassium      REAL,
    magnesium      REAL,
    glycemic_index INTEGER,
    is_low_fodmap  INTEGER,
    fodmap_triggers TEXT,
    is_gerd_safe   INTEGER
);
"""


def _seed_ingredients(conn: sqlite3.Connection) -> None:
    """Store the USDA base ingredient profiles for reference."""
    rows = []
    for key, ing in INGREDIENTS.items():
        rows.append((
            key, ing["desc"], "",
            ing["cal"], ing["pro"], ing["carb"], ing["fat"], ing["fib"],
            ing["iron"], ing["ca"], ing["b12"], ing["vd"], ing["zn"],
            ing["na"], ing["k"], ing["mgm"], ing["gi"],
            1 if ing["fodmap"] == "low" else 0,
            ",".join(ing.get("fodmap_triggers", [])),
            1 if ing.get("gerd_safe", True) else 0,
        ))
    conn.executemany(
        "INSERT OR IGNORE INTO ingredients VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def _deduplicate_sql(conn: sqlite3.Connection) -> int:
    """Remove duplicate meal names, keeping the row with the lowest meal_id."""
    cur = conn.execute("""
        DELETE FROM meals
        WHERE meal_id NOT IN (
            SELECT MIN(meal_id)
            FROM meals
            GROUP BY name
        )
    """)
    conn.commit()
    return cur.rowcount


def build_database(force_rebuild: bool = False) -> None:
    if os.path.exists(DB_PATH) and not force_rebuild:
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0]
        conn.close()
        if count >= 10_000:
            print(f"[build_database] Existing DB has {count:,} rows — skipping rebuild.")
            return
        print("[build_database] Existing DB is underpopulated — rebuilding.")
        os.remove(DB_PATH)

    print("[build_database] Generating meal records from USDA ingredient profiles…")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_MEALS_SQL)
    conn.execute(CREATE_INGREDIENTS_SQL)
    conn.commit()

    _seed_ingredients(conn)

    print("  >> Generating breakfast records...")
    breakfasts = _generate_breakfast_records()
    print(f"     {len(breakfasts):,} breakfast records")

    print("  >> Generating lunch records...")
    lunches = _generate_lunch_records()
    print(f"     {len(lunches):,} lunch records")

    print("  >> Generating dinner records...")
    dinners = _generate_dinner_records()
    print(f"     {len(dinners):,} dinner records")

    all_records = breakfasts + lunches + dinners
    print(f"  >> Total before deduplication: {len(all_records):,}")

    # Batch insert
    cols = [
        "name", "meal_type", "calories", "protein", "carbs", "fat", "fiber",
        "iron", "calcium", "vitamin_b12", "vitamin_d", "zinc", "sodium",
        "potassium", "magnesium", "glycemic_index", "is_low_fodmap",
        "fodmap_triggers", "is_gerd_safe", "is_vegetarian", "is_vegan",
        "is_pescatarian", "is_diabetic_friendly", "is_dash_compliant",
        "contains_gluten", "contains_dairy", "contains_eggs", "contains_soy",
        "contains_tree_nuts", "contains_shellfish", "contains_fish", "contains_peanuts",
    ]
    placeholders = ",".join(["?"] * len(cols))
    col_str = ",".join(cols)

    batch = [tuple(r[c] for c in cols) for r in all_records]
    conn.executemany(
        f"INSERT OR IGNORE INTO meals ({col_str}) VALUES ({placeholders})",
        batch,
    )
    conn.commit()

    removed = _deduplicate_sql(conn)
    if removed:
        print(f"  → SQL deduplication removed {removed:,} duplicates.")

    # Build indexes for fast filtering
    conn.execute("CREATE INDEX IF NOT EXISTS idx_meal_type ON meals(meal_type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_is_low_fodmap ON meals(is_low_fodmap);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gi ON meals(glycemic_index);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sodium ON meals(sodium);")
    conn.commit()

    final_count = conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0]
    conn.close()

    print(f"\n[build_database] DONE: {final_count:,} distinct meal records written to:")
    print(f"    {DB_PATH}")
    assert final_count >= 10_000, (
        f"FATAL: Only {final_count} records generated — minimum is 10,000. "
        "Add more blueprint combinations."
    )


if __name__ == "__main__":
    build_database(force_rebuild=True)
