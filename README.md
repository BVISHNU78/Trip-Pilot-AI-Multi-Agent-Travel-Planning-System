# ✈️ AI Travel Planner
LIVE NOW....
https://multi-agent-travel-planning-system.streamlit.app/
An AI-powered travel planning assistant built with **LangGraph**, **Groq LLM**, **Tavily Search**, **AviationStack API**, and **Streamlit**.

The application helps users plan trips by automatically gathering flight information, finding hotel recommendations, generating personalized itineraries, and presenting everything through an interactive web interface.

---
The system also supports **persistent conversation memory using MySQL Checkpointing**, allowing users to continue travel planning sessions without losing context.

---


## 🚀 Features

### 🛫 Flight Search
- Retrieves flight information using the AviationStack API
- Displays airline details
- Shows departure and arrival airports
- Provides flight status updates

### 🏨 Hotel Recommendations
- Uses Tavily Search to discover hotels
- Finds accommodation options based on travel destination
- Provides summarized hotel information

### 🤖 AI Itinerary Generation
- Creates personalized travel itineraries
- Generates destination-specific travel plans
- Combines flight and hotel information into a complete itinerary

### 🔄 Multi-Agent Workflow
Built with LangGraph using specialized agents:

- Flight Agent
- Hotel Agent
- Itinerary Agent
- Final Response Agent

### 🌐 Interactive Streamlit UI
- Chat-based travel planner
- Dynamic destination galleries
- Responsive travel dashboard
- Beautiful travel-themed interface

### 💾 Persistent Memory
- MySQL-based checkpointing
- Stores conversation state
- Supports multi-turn interactions
- ## 🗄️ Database & Memory

The application uses **MySQL** together with **LangGraph Checkpointing** to persist conversation state.

### Benefits

- Stores user sessions
- Maintains conversation history
- Enables long-running travel planning workflows
- Supports context-aware follow-up questions


---

## 🏗️ Architecture

```text
User Query
    │
    ▼
Flight Agent
    │
    ▼
Hotel Agent
    │
    ▼
Itinerary Agent
    │
    ▼
Final Agent
    │
    ▼
Response
```

### LangGraph Workflow

```text
START
  │
  ▼
flight_agent
  │
  ▼
hotel_agent
  │
  ▼
itinerary_agent
  │
  ▼
final_agent
  │
  ▼
 END
```

---

## 📂 Project Structure

```text
AI-Travel-Planner/
│
├── frontend.py
├── main.py
│
├── tools/
│   ├── flight_tool.py
│   └── tavily_tool.py
│
├── .env
├── requirements.txt
└── README.md
```

---
## 📦 Tech Stack

| Technology | Purpose |
|------------|----------|
| Python | Backend Development |
| LangGraph | Agent Orchestration |
| Groq | LLM Inference |
| Streamlit | Frontend UI |
| Tavily Search | Hotel & Travel Search |
| AviationStack API | Flight Data |
| MySQL | Persistent Storage |
| PyMySQL | Database Connectivity |
| LangChain | LLM Integration |
| dotenv | Environment Management |

<img width="1920" height="1032" alt="Screenshot 2026-05-30 225141" src="https://github.com/user-attachments/assets/9ef7f7a3-7b34-48ae-800d-54095b5a23b9" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225329" src="https://github.com/user-attachments/assets/78403823-1f89-4f4c-8369-04c7f4c6143d" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225319" src="https://github.com/user-attachments/assets/df8b9370-ac2f-4e24-b2a1-daaf063a7001" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225339" src="https://github.com/user-attachments/assets/1f4dd002-c92c-428c-83f9-23d4a77e3af9" />
<img width="1920" height="1032" alt="Screenshot 2026-05-30 225335" src="https://github.com/user-attachments/assets/b76053bc-413b-40e0-aea9-9b59f5ce32de" />


## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ai-travel-planner.git

cd ai-travel-planner
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate virtual environment:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key

TAVILY_API=your_tavily_api_key

AVIATIONSTACK_API=your_aviationstack_api_key

DATABASE_url=mysql+pymysql://username:password@localhost/travel_db
```

---

## 🛠 Required APIs

### Groq API

Used for:
- Itinerary generation
- Travel planning
- Final response generation

Get your API key:
https://console.groq.com

---

### Tavily API

Used for:
- Hotel recommendations
- Travel information retrieval

Get your API key:
https://tavily.com

---

### AviationStack API

Used for:
- Flight information
- Airline details
- Flight status

Get your API key:
https://aviationstack.com

---

## 🗄️ MySQL Setup

Create a database:

```sql
CREATE DATABASE travel_db;
```

Update your `.env` file:

```env
DATABASE_url=mysql+pymysql://root:password@localhost/travel_db
```

---

## ▶️ Running the Application

### Run Backend

```bash
python main.py
```

Example:

```text
Enter travel request:
Plan a 5-day trip to Tokyo
```

---

### Run Frontend

```bash
streamlit run frontend.py
```

Open in browser:

```text
http://localhost:8501
```

---

## 💬 Example Queries

```text
Plan a 7-day trip to Japan
```

```text
Luxury honeymoon trip to Bali
```

```text
Family vacation in Dubai for 5 days
```

```text
Budget-friendly Thailand itinerary
```

```text
Paris travel plan with hotel recommendations
```

---

## 🧠 Agents Overview

### Flight Agent
Responsible for:
- Flight search
- Airline information retrieval

### Hotel Agent
Responsible for:
- Hotel discovery
- Accommodation recommendations

### Itinerary Agent
Responsible for:
- Travel itinerary generation
- Personalized trip planning

### Final Agent
Responsible for:
- Combining all gathered information
- Producing the final response

---

## 💾 Persistent Memory

The project uses:

```python
PyMySQLSaver
```

Benefits:

- Conversation persistence
- Session continuity
- Multi-turn travel planning

---

## 🖼️ User Interface Features

- Dynamic hero banners
- Destination image galleries
- Interactive chat interface
- AI-powered travel planning experience

---

## 📦 Tech Stack

| Technology | Purpose |
|------------|----------|
| Python | Backend Development |
| LangGraph | Agent Workflow |
| Groq | Large Language Model |
| Tavily | Search Engine |
| AviationStack | Flight Data |
| Streamlit | Frontend UI |
| MySQL | Persistence Layer |
| PyMySQL | Database Connectivity |

---

## 🔮 Future Enhancements

- Flight booking integration
- Hotel booking integration
- Weather forecasts
- Google Maps integration
- Budget optimization
- Multi-city itinerary planning
- PDF itinerary export
- User authentication

---

## 🤝 Contributing

Contributions are welcome.

```bash
Fork the repository

Create a feature branch

Commit your changes

Push your branch

Open a Pull Request
```

---

<img width="1920" height="1032" alt="Screenshot 2026-05-30 225129" src="https://github.com/user-attachments/assets/b05b1a63-d526-4953-b63a-94830ffa1f34" />

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
