# FoodRescue AI — AI Food Waste Forecasting & Redistribution Agent

> **Predict Surplus. Prevent Waste. Share More.**  
> A full-stack, responsive, sustainability-focused web application built with Python Flask, Scikit-Learn RandomForest, SQLite/PostgreSQL-ready schema, and Bootstrap 5 with Chart.js.

---

## 🌿 1. Project Overview

FoodRescue AI connects commercial kitchens (restaurants & canteens) with food rescue organizations (NGOs, charities, shelters) and delivery volunteers to minimize food waste.

The application features:
- **Machine Learning Demand Forecasting**: RandomForestRegressor trained on chronological sales records, weekday patterns, and environmental factors to predict food demand and recommend batch prep sizes.
- **Surplus Food Marketplace**: Card-based donation platform inspired by **Food Connect** and **Plateful** with dietary tags, time-to-expiration meters, and 1-click reservations.
- **Smart NGO Matching**: Transparent rule-based algorithmic ranking considering urgency, proximity distance, quantity, and NGO serving capacity.
- **Deterministic Food Safety Validation**: Aligned with **FSSAI Food Donation Safety Regulations**. Automatic expiration blocking and mandatory temperature declarations.
- **Courier Route Tracking**: Stop-by-stop route dispatch interface inspired by **Surplus by Sharing Excess** with strict state machine validation.
- **AI Sustainability Assistant**: Real-time analytical advisor providing root-cause surplus diagnostics and next-day preparation recommendations.

---

## 🎨 2. Visual Design System

The visual design is inspired by the provided reference interfaces (**FoodBridge**, **PlateForward**, **Food Connect**, **No Waste**, and **Completed Route**):

| Color Name | Hex Code | Purpose |
|---|---|---|
| **Primary Forest Green** | `#176B45` | Primary buttons, active sidebar links, key badges |
| **Dark Green** | `#103D2B` | Sidebar navigation, hero gradient backdrop |
| **Fresh Green** | `#24A66A` | Metric card sub-labels, accents, success tags |
| **Lime Accent** | `#C8F169` | Hero call-to-actions, highlight badges, active step dots |
| **Soft Mint Background** | `#F1F8F3` | Page body background |
| **Clean White** | `#FFFFFF` | Rounded cards, navbar, table containers |
| **Main Text** | `#20332A` | Primary typography |
| **Secondary Text** | `#718078` | Subtitles, metadata, form labels |
| **Warning Amber** | `#E9A23B` | Pending status pills, leftover alerts |
| **Error Crimson** | `#D9534F` | Rejection badges, safety block notices |

---

## 👥 3. User Roles & Demo Credentials

The platform provides 4 distinct roles with server-side authorization:

| Role | Email | Password | Primary Capabilities |
|---|---|---|---|
| **Restaurant / Canteen** | `chef@greengarden.com` | `Chef@123` | Log inventory & sales, run AI forecasts, publish surplus, approve requests |
| **Additional Kitchen** | `manager@centralcanteen.edu` | `Chef@123` | Institutional canteen food records, bakery surplus |
| **NGO Organization** | `contact@cityrelief.org` | `Ngo@123` | Browse marketplace, smart matches, claim portions, confirm receipts |
| **Community Shelter** | `trust@hopeshelter.org` | `Ngo@123` | Shelter capacity claims, donation history |
| **Delivery Volunteer** | `alex@volunteer.com` | `Volunteer@123` | Browse dispatches, accept routes, update stops (pickup -> transit -> delivery) |
| **System Administrator** | `admin@foodrescue.ai` | `Admin@123` | Verify organizations, moderate listings, resolve complaints, platform analytics |

---

## 🚀 4. Quick Setup & Execution

### Prerequisites
- Python 3.10+ installed

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Seed Demo Database & Train ML Models
```powershell
python seed_demo.py
```
*This populates 35 days of historical food records for 6 signature items, trains RandomForest models persisted via Joblib, and seeds active surplus listings and deliveries.*

### Step 3: Run the Web Server
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 5. Automated Testing

Run the test suite covering authentication, permissions, forecasting, safety checks, donation reservation, and the delivery state machine:

```powershell
python -m pytest -v
```
*(All 13 test suites pass with 100% green status)*

---

## 🔄 6. End-to-End Workflow Demonstration

1. **Sign In**: Log in as `chef@greengarden.com` (`Chef@123`).
2. **AI Forecast**: Navigate to **AI Demand Forecast**; select *Vegetable Biryani* to see the predicted demand, recommended batch size (with safety buffer), MAE/RMSE metrics, and factor attribution.
3. **Surplus Listing**: Go to **Surplus Food** and inspect published batches or add a new one with the mandatory FSSAI safety checkbox.
4. **NGO Claim**: Log in on another tab or window as `contact@cityrelief.org` (`Ngo@123`). Browse the **Available Food Marketplace** and claim 20 portions via *Volunteer Delivery*.
5. **Kitchen Approval**: Return to the restaurant portal under **Donation Requests** and click **Approve**.
6. **Volunteer Pickup**: Log in as `alex@volunteer.com` (`Volunteer@123`). Go to **Available Assignments**, accept the dispatch, and step through milestones: `Confirm Picked Up` ➔ `Start Transit` ➔ `Confirm Drop-off`.
7. **NGO Receipt**: Switch to the NGO's **Pickup & Delivery** tab and click **Confirm Safe Receipt**.
8. **Admin Oversight**: Log in as `admin@foodrescue.ai` (`Admin@123`) to review system-wide redistributed tonnage, review pending applications under **Org Verification**, and inspect **System Audit Logs**.

---

## 🛡️ 7. Food Safety & AI Ethics
- **Deterministic Rules**: Food safety is strictly validated through explicit FSSAI storage duration checks and temperature constraints. AI is **never** used to certify food as safe.
- **Zero Future Leakage**: ML forecasting uses purely pre-service historical sales, day-of-week lags, and environmental variables. Future sales or leftover quantities are never used as training inputs.
- **Fallback Engine**: If historical records for a dish are below 5 shifts, the model automatically fails over to a same-weekday baseline.
