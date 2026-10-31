# ResolveHelm Architecture & Security Specification

## 1. System Overview

ResolveHelm is an automated customer support operations platform designed to safely triage, evaluate, and respond to e-commerce customer emails using knowledge-grounded AI models backed by deterministic business logic.

```mermaid
flowchart TD
    Customer([Customer Email]) -->|SMTP| Gmail[Gmail Inbox]
    Gmail -->|OAuth 2.0 API| Poller[Background Poller Process]
    
    subgraph Core Pipeline
        Poller --> Guards[Pre-Processing Guards]
        Guards -->|Skip Self/Auto| DB1[(PostgreSQL / Supabase)]
        Guards --> Claim[Atomic Event Claim]
        Claim --> Decider[Decision Engine]
        
        subgraph Decider Logic
            Decider --> SafetyCheck{Mandatory Escalation?}
            SafetyCheck -->|Yes: Safety/Legal/Refund/Injection| Escalate[Escalate Action]
            SafetyCheck -->|No| RulesCheck{Deterministic Rule Match?}
            RulesCheck -->|Yes: Size/Valve/Hardware/Parts| RuleAction[Deterministic Decision]
            RulesCheck -->|No| PydanticAI[Pydantic AI Agent]
            PydanticAI --> KB[(Knowledge Base Policy Tables)]
        end
    end
    
    RuleAction --> Outbound[Outbound Sending Safeguard]
    Escalate --> Outbound
    PydanticAI --> Outbound
    
    Outbound -->|DRY_RUN / AUTO_SEND| GmailSend[Gmail Threaded Send]
    Outbound --> DB2[(Tickets, Messages & Events DB)]
    
    subgraph Admin Interface
        Dashboard[React 18 Dashboard] -->|HTTP Basic Auth| API[FastAPI Admin Backend]
        API --> DB2
        API --> ManualPoll[Trigger Manual Poll]
    end
```

## 2. Core Security Invariants

1. **Principle of Deterministic Rule Supremacy:**
   The AI model only proposes replies; pure Python business rules evaluate and finalize decisions. If a customer request touches financial refunds, legal disputes, safety hazards, attachments, or prompt injection patterns, mandatory escalation immediately overrides any model response.

2. **Outbound Send Idempotency & Protection:**
   The application defaults to `DRY_RUN=true` and `AUTO_SEND_ENABLED=false`. Sending actions are recorded durably with event state tracking to prevent duplicate emails across retries or application restarts.

3. **Loopback Server Binding:**
   The administrative dashboard and API bind strictly to `127.0.0.1:8080` in production containers. Public traffic cannot access the administrative dashboard directly; authorized operators access the dashboard via an SSH tunnel (`ssh -L 8080:localhost:8080`).

4. **Human Thread Ownership Protection:**
   Once a thread is escalated to `needs-human`, subsequent customer follow-ups are protected from automated interference. Human agents retain complete control of escalated conversations.
