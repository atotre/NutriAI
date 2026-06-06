# Core AI Prompts: NutriAI Implementation Log

This document tracks the foundational engineering prompts utilized during the design, development, and deployment of the NutriAI platform.

---

### 1. Database Ingestion & Relational Architecture
* **Prompt used:** 
  > "Design a Python script using SQLite3 to build a nutrition database that stores meal indices, macro/micronutrient counts, ingredient logs, allergen tags, and clinical condition metadata for 15,500 recipe profiles."
* **Implementation & Modification:** I utilized the resulting SQL schemas to construct `food_database.db`, manually expanding the string parsing logic to include complex multi-variable tags for specialized diets like Hindu Vegetarianism.

---

### 2. High-Throughput Vectorized Filtration Engine
* **Prompt used:** 
  > "Write a vectorized Pandas filter in Python that accepts multi-variable user profiles (allergies, medical conditions) and applies advanced Boolean masking to completely eliminate unsafe meal options without using naive nested for loops."
* **Implementation & Modification:** This output became the core optimization layer inside `filters.py`, which I customized to separate absolute clinical exclusions (allergies) from threshold ceilings (sodium limits for hypertension).

---

### 3. Streamlit Interface & Session Memory Design
* **Prompt used:** 
  > "Create a modular Streamlit UI containing a profile submission sidebar form, multi-select components for clinical states, and a clean layout using tabs for the meal plan calendar and analytics dashboard."
* **Implementation & Modification:** I mapped this structural layout directly into `app.py` and modified the form submission layer to write active selections into `st.session_state` to keep metrics synchronized across re-runs.

---

### 4. Menu Fatigue Optimization Algorithm
* **Prompt used:** 
  > "Develop a recommendation heuristic matrix routine that satisfies precise caloric targets across 21 distinct meal slots while introducing randomization to prevent repetitive meal assignments across consecutive days."
* **Implementation & Modification:** This logic was integrated into `pipeline.py` and `recommender.py`, where I restricted the target parameters to enforce hard caloric boundaries over a 7-day schedule.