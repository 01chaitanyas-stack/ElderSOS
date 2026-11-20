# ElderSOS: Emergency Assistance & Smart Diet Planner for Senior Citizens

> **Academic Project Submission**  
> **Domain**: Healthcare Informatics & Assistive Technologies for Geriatric Care  
> **Tech Stack**: Python Flask, SQLite, Vanilla JavaScript, Responsive CSS3, PWA (Progressive Web App)

---

## 1. Executive Summary & Purpose

**ElderSOS** is an accessible, fail-safe web platform specifically designed for elderly individuals living alone or requiring semi-assisted care. The platform prioritizes high reliability, minimal cognitive load, and transparent communication across two core pillars:

1. **SOS Emergency Alert System (Highest Priority)**: A one-touch emergency trigger with a 5-second false-alarm countdown, GPS geolocation attachment, pluggable multi-channel dispatch (Telegram Bot, SMS, Console simulation), honest per-contact delivery auditing, and instant fallback dialing (`tel:112` and primary caregiver).
2. **Personalized Indian Diet Planner**: A rule-based nutrition engine with 44 curated regional Indian meals across four daily meal slots. Strictly eliminates user-specific food allergens and disliked items, supports Vegetarian, Vegan, and Non-Vegetarian diets, prioritizes soft textures for dental ease, and enforces transparent medical disclaimers.

---

## 2. System Architecture

```mermaid
graph TD
    User([👵 Senior Citizen / Caregiver]) -->|Interacts with UI| WebApp[ElderSOS PWA Frontend]
    WebApp -->|5-Sec Countdown / GPS| SOSCtrl[SOS Controller / JS Engine]
    SOSCtrl -->|POST /api/sos| Backend[Flask Application Layer]
    Backend -->|Auth & Session| FlaskLogin[Flask-Login & CSRF Protection]
    Backend -->|ORM Queries| SQLite[(SQLite Database)]
    
    Backend -->|Dispatch Alert| AlertService[Alert Dispatch Service]
    AlertService -->|Pluggable Interface| ProviderRouter{ALERT_MODE?}
    
    ProviderRouter -->|Mode: test| ConsoleProv[Console Provider (Dev/Testing)]
    ProviderRouter -->|Mode: live / telegram| TGProv[Telegram Bot API Provider]
    ProviderRouter -->|Mode: live / twilio| TwilioProv[Twilio SMS Provider]
    
    TGProv -->|HTTPS Telegram API| FamilyPhone[📱 Caregiver Telegram App]
    ConsoleProv -->|Standard Output| AuditLog[(alert_deliveries Table)]
    
    Backend -->|Rule Evaluation| DietEngine[Diet Rule Engine]
    DietEngine -->|Filter Allergens & Preferences| MealsDataset[(meals.json - 44 Indian Meals)]
    DietEngine -->|Generate 4 Meals| DietView[Daily Nutrition Menu]
```

---

## 3. Key Features

### 3.1 Priority 1: Emergency SOS Workflow
- **Senior-First UX**: Massive 240px circular emergency button with gentle pulse and high-contrast text.
- **5-Second Countdown Safeguard**: Tapping begins an audible 5-second countdown with a prominent Cancel button to abort accidental triggers without stress.
- **Geolocation with Graceful Fallback**: Requests GPS position with high accuracy. If denied or timed out, alerts proceed immediately with `"location unavailable"`.
- **Honest Delivery Guarantee**:
  - The server **NEVER** displays "Sent" unless the external provider returns positive confirmation.
  - Per-contact status (Sent ✅ / Failed ❌) and exact error descriptions (e.g., bot blocked, chat not found) are saved in `alert_deliveries` and displayed in real time.
- **Fail-Safe Offline Direct Calling**: If network connectivity fails, the app immediately highlights one-tap cellular telephone links:
  - 🚨 **Call 112** (National Emergency Police / Ambulance across India)
  - 📞 **Call Primary Caregiver** (Direct phone link to family member)
- **Test vs. Live Modes**:
  - In `ALERT_MODE=test`, alerts are routed to the Console provider and clearly badged as `TEST` throughout the UI and audit logs.
  - In `ALERT_MODE=live`, unconfigured credentials produce honest warnings explaining the missing keys rather than false confirmations.

### 3.2 Priority 2: Rule-Based Diet Planner
- **44 Curated Indian Meals**: Authentic regional items across Breakfast, Lunch, Evening Snacks, and Dinner.
- **Strict Allergen Exclusions**: Automatically excludes meals containing declared allergens (Dairy, Gluten, Peanuts, Mustard, Eggs, Fish, Soy, Sesame) through tagged properties and ingredient keyword parsing.
- **Dietary Classifications**: Strict separation between Vegetarian, Vegan, and Non-Vegetarian preferences.
- **Senior Dental Texture Handling**: Tags meals with soft textures (🦷 Easy to chew) for older adults with chewing or denture difficulties.
- **Nutritional Guidance & Medical Disclaimers**: Displays estimated daily calories, protein, carbs, fat, and fiber. Features prominent notices advising seniors with chronic conditions (e.g. Type 2 Diabetes, Hypertension) to consult their treating physician.
- **One-Click Regenerate**: Seniors or caregivers can regenerate daily plans on demand while preserving safety constraints.

### 3.3 Priority 3: Accessibility & Design Standards
- **High Contrast (WCAG AA Compliant)**: 12:1 text-to-background contrast using deep slate navy (`#0f2942`) on crisp white/soft gray cards (`#ffffff`, `#f4f7f9`).
- **Senior Typography**: Base body text is **18px or larger** (`1.125rem`), with line height 1.6 for enhanced reading comfort.
- **Large Touch Targets**: Minimum interactive element height of 48px to 58px with rounded feedback corners.
- **Keyboard Navigation & ARIA**: Visible 3px focus rings, ARIA dialog landmarks, live regions for countdown timers, and skip-to-content links.
- **PWA & Offline Readiness**: Service worker (`sw.js`) and Web Manifest (`manifest.json`) allow installation to home screens with offline fallback pages.

---

## 4. Folder Structure

```
eldersos/
├─ app.py                                # Application factory, PWA routes, DB setup
├─ config.py                             # Configuration, environment variable loading
├─ requirements.txt                      # Project dependencies
├─ .env.example                          # Environment variable template
├─ .env                                  # Local configuration file
├─ models.py                             # SQLAlchemy models (User, Contact, Alert, Diet, etc.)
├─ routes/
│  ├─ auth.py                            # Registration, login, logout, password hashing
│  ├─ sos.py                             # SOS trigger, dashboard, alert history, POST /api/sos
│  ├─ diet.py                            # Diet plan viewer, generator, plan history
│  ├─ contacts.py                        # Emergency contacts CRUD & primary contact selector
│  └─ profile.py                         # Dietary restrictions, health notes & reminders
├─ services/
│  ├─ alerts.py                          # Alert dispatcher, audit logger, message builder
│  ├─ diet_engine.py                     # Rule-based filtering & menu generation engine
│  └─ providers/
│     ├─ base.py                         # Abstract BaseAlertProvider & ProviderResult
│     ├─ console.py                      # Safe test/dev alert provider
│     ├─ telegram.py                     # Telegram Bot API integration
│     └─ twilio.py                       # Twilio SMS API integration
├─ data/
│  └─ meals.json                         # Curated Indian meals dataset (44 items)
├─ templates/
│  ├─ base.html                          # Layout, healthcare disclaimer, navigation, PWA
│  ├─ dashboard.html                     # Giant SOS button, diet shortcut, hydration, contacts
│  ├─ sos.html                           # Dedicated SOS page, countdown overlay, failsafes
│  ├─ history.html                       # Audit log of past alerts and provider receipts
│  ├─ diet.html                          # 4-meal daily menu with nutrition & portion details
│  ├─ diet_history.html                  # Archive of historical daily meal plans
│  ├─ contacts.html                      # Contact list, primary toggle, Telegram guide
│  ├─ profile.html                       # Dietary exclusions, allergens, doctor's notes
│  ├─ login.html                         # Senior-friendly sign-in form
│  └─ register.html                      # Senior citizen account registration
├─ static/
│  ├─ css/style.css                      # Senior-friendly Healthcare Design System
│  ├─ js/app.js                          # Service Worker registration, network monitor
│  ├─ js/sos.js                          # 5s countdown, geolocation, AJAX dispatch, audio beep
│  ├─ js/reminders.js                    # Hydration tracker with localStorage persistence
│  ├─ manifest.json                      # PWA web manifest
│  ├─ sw.js                              # PWA service worker with offline caching
│  └─ icons/                             # 192x192 and 512x512 app icons
├─ tests/
│  ├─ test_auth.py                       # Registration, login, session, password hashing
│  ├─ test_contacts.py                   # Contacts CRUD, validation, primary toggle
│  ├─ test_sos.py                        # SOS test mode, live mode, Telegram mocks, history
│  ├─ test_diet.py                       # Diet filtering, allergen exclusion, daily plans
│  └─ test_profile_and_dashboard.py      # Profile management, hydration, dashboard rendering
└─ scripts/
   └─ verify_eldersos.py                 # Automated end-to-end verification script
```

---

## 5. Installation & Setup

### Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Git (optional)

### Step 1: Clone or Navigate to Directory
```powershell
cd d:\Project\eldersos
```

### Step 2: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Default `.env` settings are ready for testing out of the box (`ALERT_MODE=test`).

### Step 5: Launch the Application
```powershell
python app.py
```
Open your browser to: **`http://127.0.0.1:5000`**

---

## 6. Telegram Bot Integration Guide (Real-Time Live Channel)

To send real alerts to family members' Telegram apps:

1. **Create the Telegram Bot**:
   - Open Telegram and search for `@BotFather`.
   - Send `/newbot` and follow the prompts to choose a bot name and username (e.g. `MyElderSOSBot`).
   - Copy the generated HTTP API Bot Token (e.g., `7182930412:AAHjK...`).
2. **Retrieve the Caregiver's Chat ID**:
   - Have the family member open Telegram and search for `@userinfobot`.
   - Tap **Start**. The bot will immediately reply with their numeric **Id** (e.g., `583920194`).
   - The family member must also send `/start` to your newly created bot so Telegram allows it to message them.
3. **Configure `.env`**:
   ```ini
   ALERT_MODE=live
   ALERT_PROVIDER=telegram
   TELEGRAM_BOT_TOKEN=7182930412:AAHjK...your_bot_token_here
   ```
4. **Update Contact in ElderSOS**:
   - Go to **Emergency Contacts** in ElderSOS.
   - Enter the family member's numeric Chat ID into the *Telegram Chat ID* field.
   - Now, triggering an SOS alert will dispatch an immediate notification with GPS location links straight to their phone!

---

## 7. Optional Twilio SMS Setup

To send SMS alerts via Twilio:
1. Sign up at [twilio.com](https://www.twilio.com/) and obtain an Account SID, Auth Token, and Virtual Phone Number.
2. In `.env`:
   ```ini
   ALERT_MODE=live
   ALERT_PROVIDER=twilio
   TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890
   ```

---

## 8. Web App Limitations & Practical Realities

In an academic and engineering context, web applications operate inside the browser sandbox:
1. **Silent Background SMS**: Browsers cannot silently send SMS from a user's cellular SIM card without user interaction. **ElderSOS Solution**: We dispatch alerts securely from the server via the Telegram Bot API and Twilio SMS, while offering direct `tel:` links for instantaneous manual dialing.
2. **Automatic Phone Calling**: Browser security policies prohibit automated, silent phone call placement without user approval. **ElderSOS Solution**: We provide prominent, oversized `tel:112` and `tel:[contact]` direct dial buttons.
3. **Background Location Polling**: Modern mobile OSs suspend background GPS in web applications. **ElderSOS Solution**: High-accuracy geolocation is acquired on-demand the instant the SOS countdown completes, with a 3.5s timeout fallback so alerts are never stalled.

---

## 9. Running Automated Tests

Run the full automated pytest suite (14 tests covering authentication, contacts, SOS providers, diet engine, and profile management):

```powershell
$env:PYTHONPATH = "d:\Project\eldersos"
pytest d:\Project\eldersos\tests -v
```

Run the end-to-end system verification script:
```powershell
$env:PYTHONIOENCODING = "utf-8"
python d:\Project\scripts\verify_eldersos.py
```

---

## 10. Medical & Legal Notice

> **Permanent Safety Notice**: ElderSOS is an emergency assistance and dietary planning companion. It is **NOT** a replacement for statutory emergency services (Dial **112** in India) or clinical medical diagnoses. Always dial 112 in life-threatening scenarios.
