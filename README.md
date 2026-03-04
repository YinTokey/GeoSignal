# GeoSignal

GeoSignal is a multi-agent Telegram bot that uses MCP to schedule recurring jobs to monitor breaking geopolitical/financial news.

## Agent Architecture & Workflow

Below is the execution graph and agent orchestration flow for GeoSignal:

```mermaid
graph TD
    %% Define Styles
    classDef startEnd fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#333;
    classDef mainAgent fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px,color:#000;
    classDef secondaryAgent fill:#fff3e0,stroke:#ff9800,stroke-width:2px,color:#000;
    classDef finalAgent fill:#e8f5e9,stroke:#4caf50,stroke-width:2px,color:#000;
    classDef logStop fill:#ffebee,stroke:#f44336,stroke-width:2px,color:#000;
    classDef toolNode fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px,stroke-dasharray: 4 4,color:#000;

    %% Nodes
    START((Start)):::startEnd
    Orchestrator[Orchestrator]:::mainAgent
    
    SchedulerAgent[Scheduler Agent]:::secondaryAgent
    GeneralQueryAgent[General Query Agent]:::secondaryAgent
    NewsAgent[News Agent]:::mainAgent
    
    LogAndStop[Log And Stop]:::logStop
    MarketAgent[Market Agent]:::secondaryAgent
    WebSearchAgent[Web Search Agent]:::secondaryAgent
    
    SynthesisAgent[Synthesis Agent]:::finalAgent
    END((End)):::startEnd

    %% Edges
    START --> Orchestrator
    
    Orchestrator -- "Intent: Schedule" --> SchedulerAgent
    Orchestrator -- "Intent: General Query" --> GeneralQueryAgent
    Orchestrator -- "Intent: News" --> NewsAgent
    
    SchedulerAgent --> END
    GeneralQueryAgent --> END
    
    NewsAgent -- "Duplicate/Low Severity" --> LogAndStop
    NewsAgent -- "High Severity" --> MarketAgent & WebSearchAgent
    
    LogAndStop --> END
    
    MarketAgent --> SynthesisAgent
    WebSearchAgent --> SynthesisAgent
    
    SynthesisAgent --> END
    
    LogAndStop --> END
    
    MarketAgent --> SynthesisAgent
    WebSearchAgent --> SynthesisAgent
    
    SynthesisAgent --> END
```

### Agents Description:

- **Orchestrator**: The entry point. Extracts user intent (`schedule`, `general_query`, or `news`) and routes the request.
- **News Agent**: Fetches and analyzes current breaking events. Checks for duplicates and evaluates the event severity.
- **Scheduler Agent**: Manages and configures CRON job alerts for users based on their requests.
- **General Query Agent**: Uses standard tools (like web search / market snapshots) to quickly answer direct questions.
- **Market Agent**: Looks into the financial market snapshot to measure the impact of breaking events.
- **Web Search Agent**: Identifies matching historical precedents and recovery timelines for market events.
- **Synthesis Agent**: Combines outputs from the News, Market, and Web Search agents into a cohesive Telegram alert and logs the event.

## Deployment on Render

To deploy GeoSignal on Render as a **Web Service**:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `OPENAI_API_KEY`: Your OpenAI key.
  - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token. 
    - *How to get*: Message [@BotFather](https://t.me/BotFather) on Telegram and use the `/newbot` command.
  - `TAVILY_API_KEY`: Your Tavily API key.
  - `MONGO_URI`: Your MongoDB connection string (e.g., MongoDB Atlas).
    - *Critical Note*: Render Web Services do not have static IP addresses. In your MongoDB Atlas dashboard, go to **Network Access** and add IP `0.0.0.0/0` (Allow Access From Anywhere) so your Render backend can connect successfully.

## Demo

[<img src="https://img.youtube.com/vi/cCp0VLTduVE/hqdefault.jpg"
/>](https://youtu.be/cCp0VLTduVE)