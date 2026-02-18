# Demo Script (3 minutes)

This script walks through the key features of the Epstein RAG system in a live demo.

---

## Setup (before demo)

```bash
docker compose up -d
# Wait for all services to be healthy
docker compose ps
```

Open two browser tabs:
- Tab 1: http://localhost:3000 (Dashboard)
- Tab 2: Claude Desktop (with MCP server configured)

---

## Part 1: Dashboard Overview (30 seconds)

1. Open the **Dashboard** page at http://localhost:3000
2. Point out the key sections:
   - **Stat cards** at the top: Total Queries, Avg Response Time, Indexed Documents
   - **Live Activity chart**: shows real-time query volume
   - **System Health panel**: all components green/healthy
3. Note: "This dashboard gives us full visibility into everything happening in the RAG system."

---

## Part 2: Query via Claude Desktop (45 seconds)

1. Switch to Claude Desktop
2. Type: **"What are the flight logs in the Epstein documents?"**
3. Wait for the response with citations
4. Point out:
   - The response includes specific document sources
   - Page numbers are cited
   - Response time is shown

---

## Part 3: Real-time Dashboard Update (30 seconds)

1. Switch back to the Dashboard
2. Show the **Recent Queries** panel - the query just made should appear
3. Show the **Live Activity chart** - a spike in the graph
4. Click on the query to see full details:
   - Query text
   - Full response
   - Sources with page numbers
   - Response time

Say: "Every query through any MCP client is automatically logged and visible here."

---

## Part 4: Data Import (45 seconds)

1. Navigate to the **Jobs** page
2. Show any active or completed indexing jobs
3. Point out the job details:
   - Source (GitHub URL or local path)
   - Progress bar with percentage
   - Files processed count
   - Current file being processed
   - Estimated time remaining
4. Say: "The system can import entire GitHub repositories of documents. Progress is tracked in real-time."

---

## Part 5: Analytics (30 seconds)

1. Navigate to the **Analytics** page
2. Show the visualizations:
   - **Query Volume Over Time**: line chart showing usage patterns
   - **Popular Queries**: bar chart of most common searches
   - **Response Time Distribution**: histogram showing performance
   - **Document Types**: pie chart of indexed file types
3. Say: "Analytics let you understand how the system is being used and identify popular topics."

---

## Closing (15 seconds)

"This system combines the power of RAG with full observability. AI assistants query documents through MCP, and operators monitor everything through the dashboard - all in real-time."

---

## Troubleshooting

If services are not healthy:

```bash
# Check logs
docker compose logs mcp-server
docker compose logs dashboard-backend

# Restart a specific service
docker compose restart dashboard-backend

# Full restart
docker compose down && docker compose up -d
```
