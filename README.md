# ✈️ Trip Pilot AI — Multi-Agent Travel Planner

**Live demo:** https://multi-agent-travel-planning-system.streamlit.app/

A multi-agent travel planner built with **LangGraph**, **Groq (GPT-OSS-20B)**, **Tavily Search**, **AviationStack** and **Streamlit**. It is designed so that **every fact in the plan can be traced to a source**:

- flights come only from the flight API
- places come only from a knowledge base with citations
- distances are checked
- the budget is calculated in code instead of being guessed by the LLM

---

## 💡 Why this project is different

Most LLM travel planners invent things: flight numbers, hotel prices, attractions in the wrong city, visa rules for domestic trips. Trip Pilot AI splits the work:

| The LLM does | Code does |
|---|---|
| Understands the request and pulls out the trip details | Fetches flights, hotels and places from real sources |
| Chooses activities **from a verified list** | Checks every choice, calculates the budget and writes the final answer with sources |

If a fact can't be verified, the app either leaves it out or tells you to check it. It never presents it as true.

---

## 🚀 Features

- **Asks before planning.** If the starting city, number of days, travellers or budget is missing, it asks. Reply "assume" and it plans with defaults, listing every assumption at the top.
- **Any destination.** Uses a hand-written knowledge base where one exists (Goa is included). For anywhere else, it builds one automatically from web search and map lookups.
- **Real flight data only.** The flight table shows exactly what AviationStack returned, or *"Live flight data unavailable"*. The LLM never writes a flight number.
- **Budget calculated in code.** Line items with group total and per-person cost. It picks the most comfortable style (budget, mid-range or luxury) that fits your budget, and the total is re-checked against the items.
- **Verifier agent.** Before you see the plan it:
  - removes places that aren't in the knowledge base
  - removes places that are too far from your base (no "day trip to Diu" from Goa)
  - removes invented flight numbers
  - removes passport/visa text on domestic trips
  - flags long drives, too many hotel changes and places without a source
- **Domestic vs international detection.** Visa guidance appears only for international trips, and only as a pointer to official sites.
- **Citations.** Every place and hotel has a numbered source link.
- **Mock mode.** `TRAVEL_MOCK=1` runs the whole app offline with fake data: no API keys, no quota.
- **Tested.** 29 offline tests, an 8-case evaluation set, and GitHub Actions CI on every push.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    U[User message] --> R[Router agent<br/>chat or travel? extract trip details]
    R -->|greeting or question| C[Chat agent]
    R -->|details missing| Q[Clarify agent<br/>asks for days, people, budget]
    R -->|ready to plan| K[Knowledge agent<br/>local KB or auto-build]
    K --> F[Flight agent<br/>AviationStack]
    F --> P[Planner agent · LLM<br/>picks places from the KB only]
    P --> H[Hotel agent<br/>Tavily search]
    H --> V[Verifier agent · code<br/>removes unverified items, calculates budget]
    V --> O[Final agent · code<br/>writes the response with sources]
```

| Agent | Uses LLM? | Job |
|---|---|---|
| Router | ✅ | Decides chat vs travel; extracts origin, destination, countries, days, travellers, budget, dates |
| Chat | ✅ | Replies to greetings and general questions |
| Clarify | ❌ | Asks for missing trip details |
| Knowledge | ❌ | Loads the destination's knowledge base, or builds one |
| Flight | ❌ | Calls AviationStack for every destination airport |
| Planner | ✅ | Chooses daily activities and the base area, using place IDs from the knowledge base only |
| Hotel | ❌ | Searches hotels near the chosen base area |
| Verifier | ❌ | Checks the plan against tool data; calculates the budget |
| Final | ❌ | Writes the response: assumptions, flights, day-by-day plan, hotels, budget, checks, sources |

---

## 🔍 How each fact is checked

| Fact | Where it comes from | How it's checked |
|---|---|---|
| Flights | AviationStack response | The table is built in code; notes mentioning any other flight number are removed |
| Places | Knowledge base | Must exist in the KB. Auto-built KBs: the place must be named in its cited search result and lie within 80 km of the destination |
| Distances | KB area-distance table, or map coordinates | Over 80 km from base: removed. Over 30 km: flagged as a long drive |
| Budget | KB price ranges, or LLM estimates clearly labelled as estimates | Added up in code and re-checked |
| Entry requirements | Origin and destination countries | Domestic: passport/visa text removed. International: a pointer to official sites only |

---

## 📚 Knowledge base

- **Hand-written:** [`knowledge/goa.json`](knowledge/goa.json) has airports, railway stations, areas, distances between areas, places with sources, and price ranges.
- **Automatic:** any other destination gets a knowledge base built from Tavily search results plus OpenStreetMap lookups. It's cached in `knowledge/cache/`.
- **Add your own:** copy the shape of `goa.json` to give a destination hand-checked data.

> The prices in `goa.json` are indicative placeholders. Replace them with researched figures before relying on the budget.

---

## 📂 Project structure

```text
├── frontend.py                  # Streamlit chat UI
├── main.py                      # LangGraph graph + command-line app
├── planning.py                  # Budget, verifier and response writer (no LLM)
├── providers.py                 # All external calls, plus offline mock versions
├── schemas.py                   # Structured LLM outputs (Pydantic)
├── tools/
│   └── flight_tool.py           # AviationStack client
├── knowledge/
│   ├── __init__.py              # Knowledge-base lookup and distances
│   ├── builder.py               # Builds a knowledge base for any destination
│   └── goa.json                 # Hand-written example
├── tests/                       # Offline tests (mock mode)
├── eval/run_eval.py             # Evaluation set (mock, or --live)
├── .github/workflows/ci.yml     # Runs tests on every push
├── .streamlit/secrets.toml.example
├── requirements.txt
└── requirements-dev.txt
```

---

## 📦 Tech stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Backend |
| LangGraph | Agent workflow |
| LangChain + Groq (GPT-OSS-20B) | LLM inference and structured output |
| Pydantic | Structured LLM output schemas |
| Tavily Search | Hotel and attraction search |
| AviationStack | Live flight data |
| OpenStreetMap Nominatim | Map lookups for distance checks |
| Streamlit | Web UI |
| MySQL / TiDB Cloud + PyMySQL | Saved conversation history for the command-line app |
| pytest + GitHub Actions | Tests and CI |

---

## ⚙️ Getting started

### 1. Clone and install

```bash
git clone https://github.com/BVISHNU78/Trip-Pilot-AI-Multi-Agent-Travel-Planning-System.git
cd Trip-Pilot-AI-Multi-Agent-Travel-Planning-System

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2. Add your API keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API=your_tavily_api_key
AVIATIONSTACK_API=your_aviationstack_api_key

# Only needed for the command-line app (python main.py)
DATABASE_url=mysql+pymysql://username:password@host:port/database
```

| API | Used for | Get a key |
|---|---|---|
| Groq | Understanding requests, planning, chat | https://console.groq.com |
| Tavily | Hotel and attraction search | https://tavily.com |
| AviationStack | Live flights | https://aviationstack.com |

### 3. Run it

```bash
streamlit run frontend.py      # Web app → http://localhost:8501
python main.py                 # Command-line app (history saved to MySQL)
```

### Try it without any API keys

```bash
# Windows PowerShell
$env:TRAVEL_MOCK="1"; streamlit run frontend.py

# macOS / Linux
TRAVEL_MOCK=1 streamlit run frontend.py
```

Mock mode uses fake flights, places and hotels, and shows a **MOCK MODE** banner on every response.

---

## 💬 Example conversation

```text
You:  trip kochi to goa
Bot:  Happy to plan Goa! Before I do, could you tell me:
      - how many days
      - how many people are travelling
      - your total budget (₹)
      Or reply "assume" and I'll plan with defaults.

You:  4 days, 2 people, budget 40000
Bot:  # 4-day trip: Kochi → Goa
      Assumptions · Getting there (live flights + rail) · Day-by-day plan
      Where to stay · Budget (calculated in code) · Checks · Sources
```

More to try:

```text
plan 5 days from delhi to paris for 2 people, budget 3 lakh
plan 3 days from mumbai to hampi for 2 people under 30000
plan 3 days from kochi to goa for 1 person, budget 25000, include a day trip to diu
```

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt

python -m pytest tests -q          # 29 offline tests
python eval/run_eval.py            # evaluation set, offline
python eval/run_eval.py --live     # same cases against the real APIs
```

The test suite always runs in mock mode, so it never uses API quota. CI runs both on every push.

| Evaluation case | Expected |
|---|---|
| "trip kochi to goa" | Asks for days/budget (or states assumptions); no passport text |
| Any domestic trip | No visa/passport requirements |
| Flight table | Only flights returned by the API |
| Budget | Total equals the sum of its items |
| Nearby trips | No impossible suggestions (e.g. Diu from Goa) |
| "hi" | Friendly reply, no trip plan |

---

## ☁️ Deployment (free tier)

Deployed on **Streamlit Community Cloud**:

1. Connect this repository and set **Main file path** to `frontend.py` (Python 3.12).
2. Under **Settings → Secrets**, add your keys. See [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example):
   ```toml
   GROQ_API_KEY = "..."
   TAVILY_API = "..."
   AVIATIONSTACK_API = "..."
   ```
3. Optional: add `TRAVEL_MOCK = "1"` to demo the app without using API quota.

| Component | Service | Tier |
|---|---|---|
| Hosting | Streamlit Community Cloud | Free |
| LLM | Groq Cloud (GPT-OSS-20B) | Free tier |
| Database (command-line app) | TiDB Cloud (AWS) | Free tier |
| Flight data | AviationStack | Free developer tier |
| Search | Tavily | Free developer tier |
| Maps | OpenStreetMap Nominatim | Free (1 request/second) |

No secrets are stored in the repository: `.env` and `secrets.toml` are git-ignored.

---

## 💾 Memory

- **Web app:** each browser session has its own conversation memory, so follow-up answers ("4 days, 2 people") connect to the earlier request. It resets when the app restarts.
- **Command-line app:** conversation history is saved to MySQL/TiDB with LangGraph's `PyMySQLSaver` and survives restarts.

---

## ⚠️ Known limitations

- **No fares or dates.** AviationStack's free tier shows flights operating today, not fares or schedules for your dates.
- **Placeholder Goa prices.** Replace them in `goa.json`.
- **Auto-built places aren't hand-checked.** They're checked against their source and their location, and budgets for those destinations are labelled LLM estimates.
- **The first plan for a new city is slower** (about 10–15 seconds) because of the map-lookup rate limit. After that it's cached.
- **Free-tier limits** depend on each provider's policy.

---

## 🖼️ Screenshots

<img width="1920" height="1032" alt="Screenshot 2026-05-30 225141" src="https://github.com/user-attachments/assets/9ef7f7a3-7b34-48ae-800d-54095b5a23b9" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225329" src="https://github.com/user-attachments/assets/78403823-1f89-4f4c-8369-04c7f4c6143d" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225319" src="https://github.com/user-attachments/assets/df8b9370-ac2f-4e24-b2a1-daaf063a7001" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225339" src="https://github.com/user-attachments/assets/1f4dd002-c92c-428c-83f9-23d4a77e3af9" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225335" src="https://github.com/user-attachments/assets/b76053bc-413b-40e0-aea9-9b59f5ce32de" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225129" src="https://github.com/user-attachments/assets/b05b1a63-d526-4953-b63a-94830ffa1f34" />

---

## 🔮 Future enhancements

- Real fares and availability (e.g. Amadeus or Skyscanner APIs)
- More hand-written destination knowledge bases
- Weather forecasts for the travel dates
- Map view of the day-by-day plan
- PDF itinerary export
- User accounts with saved trips

---

## 🤝 Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Run `python -m pytest tests -q` before committing
4. Open a pull request

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
