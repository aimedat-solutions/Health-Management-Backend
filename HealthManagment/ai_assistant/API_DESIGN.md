# AI Assistant — REST API Design Document

> **Author:** Principal Backend Engineer  
> **Version:** 1.0  
> **Status:** Draft  

---

## Table of Contents

1. [Business Requirements](#1-business-requirements)
2. [Design Principles](#2-design-principles)
3. [API Versioning](#3-api-versioning)
4. [Authentication & Authorisation](#4-authentication--authorisation)
5. [Common Conventions](#5-common-conventions)
6. [Endpoint Catalogue](#6-endpoint-catalogue)
7. [Sequence Diagrams](#7-sequence-diagrams)
8. [API Flow Diagrams](#8-api-flow-diagrams)
9. [Rate Limiting](#9-rate-limiting)
10. [Error Response Reference](#10-error-response-reference)
11. [Appendix — Decision Log](#11-appendix--decision-log)

---

## 1. Business Requirements

### 1.1 Problem Statement

Patients need 24/7 access to preliminary health guidance. Doctors are overburdened with routine queries. The system must allow patients to converse with an AI assistant that can triage symptoms, answer common questions, and escalate to a human doctor when necessary.

### 1.2 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR1 | Patient can start a new AI-assisted conversation | P0 |
| FR2 | Patient can send text messages and receive AI responses | P0 |
| FR3 | Patient can view their conversation history | P0 |
| FR4 | Patient can rate/flag individual AI responses | P1 |
| FR5 | Patient can close/resolve a conversation | P1 |
| FR6 | Doctor can view conversations assigned to them | P1 |
| FR7 | Doctor can post notes and change review status | P1 |
| FR8 | Admin can manage available AI models and agents | P2 |
| FR9 | System can auto-escalate based on triage severity | P2 |
| FR10 | Patient can attach images or files to messages | P2 |

### 1.3 Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR1 | AI response time must be <5s for 95% of requests |
| NFR2 | API must support 1000 concurrent patients |
| NFR3 | All patient health data is encrypted at rest and in transit |
| NFR4 | Audit log must capture every AI decision and doctor intervention |

---

## 2. Design Principles

Every endpoint in this document follows these principles:

1. **Resource-oriented URLs** — URLs represent nouns (conversations, messages), not actions.
2. **Stateless** — No server-side session state; every request carries full context via JWT.
3. **Consistency over convenience** — Error shapes, pagination metadata, and field naming are uniform across all endpoints.
4. **Chat is special** — The "send message" endpoint is the only synchronous write that returns two resources (user message + AI response) because the chat UX demands it.
5. **Versioning via URL prefix** — `/api/v1/` because header-based versioning is invisible in documentation, harder to test, and doesn't cache differently.
6. **Async where it matters** — AI response generation is synchronous for simplicity in v1; if latency becomes problematic, the endpoint returns immediately with a `202 Accepted` and the client polls via WebSocket.

---

## 3. API Versioning

**Scheme:** URL path prefix

```
https://api.healthmanagment.com/api/v1/conversations
```

**Rationale:** URL-based versioning is explicit, cacheable, and easy to test with curl. Header-based versioning hides the version from logs and requires middleware to extract.

**Deprecation policy:** Each major version is supported for 18 months after the next version ships. A `Sunset` header is added 6 months before removal.

---

## 4. Authentication & Authorisation

### 4.1 Authentication

| Mechanism | Detail |
|---|---|
| **Scheme** | Bearer JWT (access + refresh token pair) |
| **Token lifetime** | Access: 15 days, Refresh: 365 days (configurable via `settings.py`) |
| **Header** | `Authorization: Bearer <access_token>` |
| **Token content** | `user_id`, `role` (patient / doctor / admin), `exp`, `iat` |

Every endpoint except token obtain/refresh requires a valid JWT.

### 4.2 Authorisation Matrix

| Endpoint | Patient | Doctor | Admin |
|---|---|---|---|
| `GET /conversations` | Own only | Assigned only | All |
| `POST /conversations` | Yes | No | No |
| `GET /conversations/:id` | Own only | Assigned only | All |
| `PATCH /conversations/:id` | Own only (status/title) | Yes (status/notes) | All |
| `DELETE /conversations/:id` | No | No | Yes (soft-delete) |
| `GET /conversations/:id/messages` | Own conversation | Assigned conversation | All |
| `POST /conversations/:id/messages` | Own conversation | No | No |
| `POST /messages/:id/feedback` | Own message only | No | No |
| `GET /conversations/:id/reviews` | Own conversation | Assigned | All |
| `POST /conversations/:id/reviews` | No | Yes | Yes |
| `PATCH /reviews/:id` | No | Assigned review | All |

**Enforcement pattern:** Permission classes at the view level + object-level checks at the repository layer. Never trust the client to self-limit.

---

## 5. Common Conventions

### 5.1 Base URL

```
/api/v1/
```

### 5.2 Date/Time Format

ISO 8601 with timezone: `2026-06-26T14:30:00+05:30`

### 5.3 Pagination

| Type | Where | Parameter | Default | Max |
|---|---|---|---|---|
| **Cursor-based** | Messages (chat) | `cursor`, `limit` | 50 | 200 |
| **Page-based** | Lists (conversations, reviews, feedback) | `page`, `page_size` | 20 | 100 |

**Rationale for cursor pagination on messages:** New messages arrive constantly. Cursor pagination prevents duplicate or missed records when new rows are inserted between page requests — a common problem with `OFFSET` in chat contexts.

### 5.4 Standard Response Envelope

**Success (200/201):**
```json
{
    "data": { ... },
    "meta": {
        "request_id": "req_abc123"
    }
}
```

**Paginated success:**
```json
{
    "data": [ ... ],
    "meta": {
        "request_id": "req_abc123",
        "pagination": {
            "next_cursor": "eyJpZCI6MTUwfQ==",
            "prev_cursor": null,
            "has_more": true,
            "total": 342
        }
    }
}
```

### 5.5 Error Envelope

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable summary",
        "details": [
            {
                "field": "content",
                "code": "required",
                "message": "This field is required."
            }
        ],
        "request_id": "req_abc123"
    }
}
```

### 5.6 Status Code Usage

| Code | When |
|---|---|
| `200 OK` | Successful read or update |
| `201 Created` | Resource created |
| `202 Accepted` | Async operation accepted (future v2) |
| `204 No Content` | Successful delete |
| `400 Bad Request` | Validation failure |
| `401 Unauthorized` | Missing/invalid JWT |
| `403 Forbidden` | Valid JWT but insufficient role |
| `404 Not Found` | Resource doesn't exist |
| `409 Conflict` | Duplicate resource (e.g. duplicate feedback) |
| `429 Too Many Requests` | Rate limit hit |
| `500 Internal Server Error` | Unhandled server error |

### 5.7 Field Naming

`snake_case` for request and response bodies. Rationale: matches Python/Django conventions, avoids serialisation overhead of mapping camelCase.

---

## 6. Endpoint Catalogue

### 6.1 Conversation Endpoints

#### `GET /api/v1/conversations` — List conversations

**Why this endpoint exists:** The patient's home screen shows their active conversations. The doctor's dashboard shows assigned conversations awaiting review. This is the primary entry point.

**Authentication required:** Yes

**Permissions:**
- Patient: returns only `patient == request.user`
- Doctor: returns only `doctor == request.user`
- Admin: returns all

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `status` | string | — | Filter by status: `active`, `paused`, `resolved`, `escalated_to_doctor`, `archived` |
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | Items per page |
| `ordering` | string | `-updated_at` | Sort field: `updated_at`, `started_at`, `-updated_at`, `-started_at` |

**Response `200 OK`:**
```json
{
    "data": [
        {
            "id": 42,
            "title": "Persistent headache for 3 days",
            "status": "active",
            "message_count": 12,
            "total_tokens": 4523,
            "summary": "",
            "patient": {
                "id": 7,
                "name": "Ravi Sharma",
                "phone": "+919876543210"
            },
            "doctor": null,
            "model": {
                "id": 1,
                "name": "GPT-4o"
            },
            "last_message_preview": "You should stay hydrated and rest...",
            "started_at": "2026-06-25T10:30:00+05:30",
            "updated_at": "2026-06-26T08:15:00+05:30"
        }
    ],
    "meta": {
        "request_id": "req_abc123",
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 5,
            "total_pages": 1
        }
    }
}
```

**Errors:** `401`, `403`

---

#### `POST /api/v1/conversations` — Create conversation

**Why this endpoint exists:** A patient must create a conversation container before sending messages. This captures the initial context (title, optional metadata) and assigns the default AI model.

**Authentication required:** Yes

**Permissions:** Patient only

**Request body:**
```json
{
    "title": "Persistent headache for 3 days",
    "metadata": {
        "department": "general",
        "language": "hi"
    }
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `title` | Required. Max 255 chars. |
| `metadata` | Optional. Must be a JSON object. Max depth: 5. |

**Response `201 Created`:**
```json
{
    "data": {
        "id": 42,
        "title": "Persistent headache for 3 days",
        "status": "active",
        "message_count": 0,
        "total_tokens": 0,
        "summary": "",
        "patient": {
            "id": 7,
            "name": "Ravi Sharma",
            "phone": "+919876543210"
        },
        "doctor": null,
        "model": {
            "id": 1,
            "name": "GPT-4o"
        },
        "started_at": "2026-06-26T08:20:00+05:30",
        "updated_at": "2026-06-26T08:20:00+05:30"
    },
    "meta": {
        "request_id": "req_abc124"
    }
}
```

**Errors:** `400`, `401`, `403`

---

#### `GET /api/v1/conversations/{id}` — Retrieve conversation

**Why this endpoint exists:** Needed to load the conversation header when re-entering a chat, or when a doctor reviews a specific conversation.

**Authentication required:** Yes

**Permissions:** Patient (own), Doctor (assigned), Admin (all)

**Path parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | integer | Conversation ID |

**Response `200 OK`:**
Same shape as the single object in the list response but includes full metadata and summary.

**Errors:** `401`, `403`, `404`

---

#### `PATCH /api/v1/conversations/{id}` — Update conversation

**Why this endpoint exists:** Patient changes the title or marks as resolved. Doctor updates status (e.g. `escalated_to_doctor` → `resolved`). Admin may add notes to metadata.

**Authentication required:** Yes

**Permissions:** Patient (own, limited fields), Doctor (assigned), Admin (all)

**Request body (patient):**
```json
{
    "title": "Updated: Headache + fever",
    "status": "resolved"
}
```

**Request body (doctor/admin):**
```json
{
    "status": "resolved",
    "metadata": {
        "doctor_notes": "Patient advised to visit clinic if symptoms persist"
    }
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `title` | Optional. Max 255 chars. |
| `status` | Must be a valid `ConversationStatus` enum value. Patient can only set: `paused`, `resolved`. Doctor can set: `resolved`, `archived`. Admin: any. |
| `metadata` | Optional. Merged shallowly with existing metadata (not replaced). |

**Response `200 OK`:** Returns full conversation object.

**Errors:** `400`, `401`, `403`, `404`

---

#### `DELETE /api/v1/conversations/{id}` — Delete conversation

**Why this endpoint exists:** GDPR right to erasure and admin cleanup. Not exposed to patients — they can only archive.

**Authentication required:** Yes

**Permissions:** Admin only

**Behaviour:** Performs a soft-delete (sets status to `archived`). Hard deletion is a separate admin-only management command.

**Response `204 No Content`**

**Errors:** `401`, `403`, `404`

---

### 6.2 Message Endpoints

#### `GET /api/v1/conversations/{conversation_id}/messages` — List messages

**Why this endpoint exists:** Loads the entire chat transcript when a patient or doctor opens a conversation.

**Authentication required:** Yes

**Permissions:** Patient (own conversation), Doctor (assigned), Admin (all)

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cursor` | string | — | Opaque cursor from previous response |
| `limit` | integer | 50 | Messages per page (max 200) |
| `direction` | string | `backward` | `backward` (newest first, typical) or `forward` (oldest first) |

**Why cursor direction defaults to `backward`:** Opening a chat should show the most recent messages first — that is what the user just sent/received. They scroll up to see older context.

**Cursor format:** Base64-encoded JSON `{"id": <last_message_id>, "created_at": "<timestamp>"}`. Opaque to clients.

**Response `200 OK`:**
```json
{
    "data": [
        {
            "id": 156,
            "role": "user",
            "content_type": "text",
            "content": "I have a bad headache that won't go away",
            "content_data": {},
            "tokens": 12,
            "created_at": "2026-06-26T08:25:00+05:30",
            "feedback": null
        },
        {
            "id": 157,
            "role": "assistant",
            "content_type": "text",
            "content": "I understand you're experiencing a persistent headache. Let me ask a few questions to help assess your situation...",
            "content_data": {},
            "tokens": 142,
            "created_at": "2026-06-26T08:25:03+05:30",
            "feedback": {
                "rating": null,
                "category": null
            }
        }
    ],
    "meta": {
        "request_id": "req_abc125",
        "pagination": {
            "next_cursor": "eyJpZCI6MTU3LCJjcmVhdGVkX2F0IjoiMjAyNi0wNi0yNlQwODoyNTowMyswNTozMCJ9",
            "has_more": true
        }
    }
}
```

**Design decision — `feedback` nested in message:** Chat UIs display feedback inline next to each AI message. Including a `feedback` summary avoids N+1 queries on the frontend. The full feedback object is available via the feedback endpoints.

**Errors:** `401`, `403`, `404`

---

#### `POST /api/v1/conversations/{conversation_id}/messages` — Send message

**Why this endpoint exists:** This is the core interaction — patient sends a message, the system stores it, invokes the AI pipeline (RAG retrieval → LLM call → agent execution), and returns both the user message and AI response in a single round-trip.

**Why not split into "send message" + "poll for response"?** For v1, synchronous delivery simplifies the client enormously. The AI stack is designed for sub-5s responses. If latency becomes a problem, we switch to `202 Accepted` + WebSocket push (v2).

**Authentication required:** Yes

**Permissions:** Patient (own conversation, conversation must be `active` or `paused`)

**Request body:**
```json
{
    "content": "I have a bad headache that won't go away. It started 3 days ago.",
    "content_type": "text",
    "content_data": {}
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `content` | Required. Max 100 000 chars. Must not be blank. |
| `content_type` | Optional. Default: `text`. Valid values: `text`, `image_url`. File uploads use a separate future endpoint. |
| `content_data` | Optional. JSON object. Required keys depend on `content_type`: for `image_url` requires `{"url": "..."}`. |

**Business rule:** If `conversation.status == "paused"`, the message is saved but the AI does NOT respond. The conversation remains paused until the patient or doctor resumes it.

**Response `201 Created`:**
```json
{
    "data": {
        "user_message": {
            "id": 156,
            "role": "user",
            "content_type": "text",
            "content": "I have a bad headache that won't go away...",
            "content_data": {},
            "tokens": 15,
            "created_at": "2026-06-26T08:25:00+05:30"
        },
        "ai_message": {
            "id": 157,
            "role": "assistant",
            "content_type": "text",
            "content": "I understand you're experiencing a persistent headache...",
            "content_data": {},
            "tokens": 142,
            "created_at": "2026-06-26T08:25:03+05:30"
        },
        "triage": {
            "urgency": "non_urgent",
            "recommendation": "Monitor symptoms for 24 hours. Seek care if fever develops."
        },
        "conversation_status": "active"
    },
    "meta": {
        "request_id": "req_abc126"
    }
}
```

**Design decision — returning `triage` at the top level:** The frontend needs to know immediately if the AI flagged something urgent. Nesting it inside `ai_message` makes it harder to extract. It is a first-class output of the message-send operation.

**Errors:** `400`, `401`, `403`, `404`, `429`

---

#### `GET /api/v1/messages/{id}` — Retrieve single message

**Why this endpoint exists:** Used for deep-linking to a specific message (e.g. from a notification or feedback screen).

**Authentication required:** Yes

**Permissions:** Patient (own conversation's message), Doctor (assigned conversation's message), Admin (all)

**Response `200 OK`:** Same shape as message objects in the list endpoint.

**Errors:** `401`, `403`, `404`

---

### 6.3 Feedback Endpoints

#### `POST /api/v1/messages/{message_id}/feedback` — Create or update feedback

**Why this endpoint exists:** AI quality depends on patient ratings. This endpoint lets patients rate individual AI responses, which feeds into model evaluation and fine-tuning.

**Why single endpoint for create + update:** The `unique_together` constraint on `(message, patient)` means one feedback per patient per message. Using `POST` with upsert semantics is simpler than requiring the client to `GET` first to check existence.

**Authentication required:** Yes

**Permissions:** Patient (own message only)

**Request body:**
```json
{
    "rating": 4,
    "category": "helpful",
    "comment": "The advice was clear and practical"
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `rating` | Required. Integer 1–5. |
| `category` | Optional. Valid values: `helpful`, `inaccurate`, `confusing`, `incomplete`, `harmful`, `off_topic`, `other`. |
| `comment` | Optional. Max 2000 chars. |

**Response `200 OK`** (200, not 201, because upsert may update existing):
```json
{
    "data": {
        "id": 12,
        "message_id": 157,
        "rating": 4,
        "category": "helpful",
        "comment": "The advice was clear and practical",
        "created_at": "2026-06-26T09:00:00+05:30"
    },
    "meta": {
        "request_id": "req_abc127"
    }
}
```

**Errors:** `400`, `401`, `403`, `404`, `409`

---

#### `GET /api/v1/messages/{message_id}/feedback` — Get feedback

**Why this endpoint exists:** Allows the frontend to pre-fill the feedback UI if the patient already rated this message.

**Authentication required:** Yes

**Permissions:** Patient (own), Doctor (assigned conversation), Admin (all)

**Response `200 OK`:** Same shape as above. Returns `null` in the `data` field if no feedback exists, rather than `404`.

**Errors:** `401`, `403`, `404`

---

### 6.4 Doctor Review Endpoints

#### `GET /api/v1/conversations/{conversation_id}/reviews` — List reviews

**Why this endpoint exists:** Shows review history for a conversation. A conversation can be reviewed multiple times by different doctors (e.g. transferred cases).

**Authentication required:** Yes

**Permissions:** Patient (own), Doctor (assigned), Admin (all)

**Response `200 OK`:**
```json
{
    "data": [
        {
            "id": 5,
            "doctor": {
                "id": 12,
                "name": "Dr. Priya Patel"
            },
            "status": "approved",
            "notes": "Patient advised to take paracetamol and rest. Follow up in 3 days.",
            "reviewed_at": "2026-06-26T10:00:00+05:30",
            "created_at": "2026-06-26T09:30:00+05:30"
        }
    ],
    "meta": {
        "request_id": "req_abc128",
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total": 1,
            "total_pages": 1
        }
    }
}
```

**Errors:** `401`, `403`, `404`

---

#### `POST /api/v1/conversations/{conversation_id}/reviews` — Create review

**Why this endpoint exists:** Doctor initiates a review of a conversation. This could be triggered:
1. Manually — doctor opens a conversation and decides to review it
2. Automatically — system escalates based on triage severity

**Authentication required:** Yes

**Permissions:** Doctor, Admin

**Request body:**
```json
{
    "status": "in_review",
    "notes": "Patient reports persistent headache for 3 days with no fever. Will review chat history."
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `status` | Optional. Default: `requested`. Valid: `requested`, `in_review`. |
| `notes` | Optional. Max 10 000 chars. |

**Response `201 Created`**

**Errors:** `400`, `401`, `403`, `404`, `409` (if doctor already has a review for this conversation)

---

#### `PATCH /api/v1/reviews/{id}` — Update review

**Why this endpoint exists:** Doctor progresses the review workflow: `in_review` → `approved` / `rejected` / `needs_revision`.

**Authentication required:** Yes

**Permissions:** Doctor (own review only), Admin (any)

**Request body:**
```json
{
    "status": "approved",
    "notes": "Reviewed. Condition is non-urgent. Paracetamol + rest recommended."
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `status` | Required. Must follow state machine: `requested` → `in_review` → `approved|rejected|needs_revision`. |
| `notes` | Optional. Max 10 000 chars. |

**State machine:**
```
requested ──→ in_review ──→ approved
                            ├── rejected
                            └── needs_revision
```

**Response `200 OK`**

**Errors:** `400`, `401`, `403`, `404`, `422` (invalid state transition)

---

### 6.5 AI Model & Agent Endpoints (Admin)

#### `GET /api/v1/models` — List AI models

**Why this endpoint exists:** Admin UI needs to see available models, and the system uses this when assigning a model to a new conversation.

**Authentication required:** Yes

**Permissions:** All authenticated users (read-only)

**Response `200 OK`:**
```json
{
    "data": [
        {
            "id": 1,
            "name": "GPT-4o",
            "provider": "openai",
            "model_id": "gpt-4o-2026-05-01",
            "is_active": true,
            "max_tokens": 8192,
            "temperature": 0.7,
            "cost_per_input_token": "0.00000250",
            "cost_per_output_token": "0.00001000"
        }
    ],
    "meta": {
        "request_id": "req_abc129"
    }
}
```

**Errors:** `401`

---

#### `GET /api/v1/agents` — List AI agents

**Why this endpoint exists:** Similar to models — visibility into which agents are configured and active.

**Authentication required:** Yes

**Permissions:** All authenticated users (read-only)

**Response `200 OK`:**
```json
{
    "data": [
        {
            "id": 1,
            "name": "Triage Agent v1",
            "agent_type": "triage",
            "is_active": true,
            "timeout_seconds": 60
        }
    ]
}
```

**Errors:** `401`

---

## 7. Sequence Diagrams

### 7.1 Patient Sends Message (Happy Path)

```
Patient          Frontend            API              AI Pipeline         DB
   │                │                 │                   │                │
   │  Type message  │                 │                   │                │
   │───────────────>│                 │                   │                │
   │                │  POST /messages │                   │                │
   │                │────────────────>│                   │                │
   │                │                 │──┐                │                │
   │                │                 │  │ Validate       │                │
   │                │                 │<─┘                │                │
   │                │                 │──┐                │                │
   │                │                 │  │ Save user msg  │───────────────>│
   │                │                 │<─┘                │                │
   │                │                 │──┐                │                │
   │                │                 │  │ Invoke AI      │                │
   │                │                 │──────────────────>│                │
   │                │                 │                   │──┐             │
   │                │                 │                   │  │ RAG retr.   │
   │                │                 │                   │<─┘             │
   │                │                 │                   │──┐             │
   │                │                 │                   │  │ LLM call    │
   │                │                 │                   │<─┘             │
   │                │                 │                   │──┐             │
   │                │                 │                   │  │ Triage      │
   │                │                 │                   │<─┘             │
   │                │                 │                   │                │
   │                │                 │  AI response      │                │
   │                │                 │<──────────────────│                │
   │                │                 │──┐                │                │
   │                │                 │  │ Save AI msg    │───────────────>│
   │                │                 │<─┘                │                │
   │                │    201 + data   │                   │                │
   │                │<────────────────│                   │                │
   │  Show AI reply │                 │                   │                │
   │<───────────────│                 │                   │                │
   │                │                 │                   │                │
   │  Rate reply    │                 │                   │                │
   │───────────────>│  POST /feedback │                   │                │
   │                │────────────────>│                   │                │
   │                │                 │  Save feedback    │───────────────>│
   │                │    200          │                   │                │
   │                │<────────────────│                   │                │
```

### 7.2 Doctor Reviews Conversation

```
Doctor           Frontend            API                  DB
   │                │                 │                    │
   │  Open dashboard│                 │                    │
   │───────────────>│  GET /convs     │                    │
   │                │────────────────>│   Query assigned   │
   │                │                 │───────────────────>│
   │                │  List + meta    │                    │
   │                │<────────────────│                    │
   │<───────────────│                 │                    │
   │                │                 │                    │
   │  Select conv   │                 │                    │
   │───────────────>│  GET /msgs      │                    │
   │                │────────────────>│   Query messages   │
   │                │                 │───────────────────>│
   │                │  Messages +     │                    │
   │                │  feedback       │                    │
   │                │<────────────────│                    │
   │<───────────────│                 │                    │
   │                │                 │                    │
   │  Write review  │                 │                    │
   │───────────────>│  POST /reviews  │                    │
   │                │────────────────>│   Create review    │
   │                │                 │───────────────────>│
   │                │  201            │                    │
   │                │<────────────────│                    │
   │<───────────────│                 │                    │
```

---

## 8. API Flow Diagrams

### 8.1 Request Lifecycle

```
                        ┌──────────────┐
                        │  Client App  │
                        └──────┬───────┘
                               │ HTTP Request
                               ▼
                        ┌──────────────┐
                        │  Nginx / LB  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  Django App  │
                        │  (Gunicorn)  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  Middleware   │
                        │  - CORS      │
                        │  - Auth JWT  │
                        │  - Audit     │
                        │  - Rate Lim  │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  URL Router  │
                        │  /api/v1/*   │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  Permission  │
                        │  Check (DRF) │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   Service    │
                        │   Layer      │
                        │  (Business   │
                        │   Logic)     │
                        └──────┬───────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │   Repo  │ │   LLM  │ │   RAG  │
              │  Layer  │ │ Client │ │  Store  │
              └────┬────┘ └─────────┘ └─────────┘
                   │
                   ▼
              ┌─────────┐
              │Postgres │
              └─────────┘
```

### 8.2 AI Pipeline Flow

```
                    ┌─────────────────────┐
                    │  SendMessageService │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 1. Validate message │
                    │ 2. Save user msg    │
                    │ 3. Check status     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 4. Build context    │
                    │    - Last N messages│
                    │    - Patient info   │
                    │    - RAG context    │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 5. Select agent     │
                    │    - Triage agent   │
                    │    - Main agent     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 6. Execute LLM call │
                    │    - Retry logic    │
                    │    - Token tracking │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 7. Parse response   │
                    │    - Extract triage │
                    │    - Format content │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ 8. Save AI message  │
                    │ 9. Update counters  │
                    │10. Check escalation │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Return response    │
                    └─────────────────────┘
```

### 8.3 Feedback & Improvement Loop

```
Patient Feedback ──> Store in DB ──> Periodic eval
                                          │
                                          ▼
                                    Drift detection
                                          │
                              ┌───────────┴───────────┐
                              │                       │
                              ▼                       ▼
                        Fine-tune model       Adjust prompts
                        / switch model       / agent config
```

---

## 9. Rate Limiting

### 9.1 Limits

| Scope | Limit | Period | Burst |
|---|---|---|---|
| Message send (per patient) | 30 | 1 minute | 5 |
| Feedback creation (per patient) | 60 | 1 minute | 10 |
| Read endpoints (per user) | 200 | 1 minute | 20 |
| Conversation create (per patient) | 10 | 1 hour | — |

### 9.2 Headers

Every response includes:

```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 28
X-RateLimit-Reset: 1689876543
Retry-After: 4
```

### 9.3 Implementation

Token bucket algorithm per user ID, stored in Redis. The message send endpoint is the most sensitive — a single patient sending 30 messages/minute is a plausible burst during detailed symptom gathering. The 5-burst allowance handles that without false positives.

---

## 10. Error Response Reference

### 10.1 Validation Error (`400`)

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "2 validation errors",
        "details": [
            {
                "field": "content",
                "code": "required",
                "message": "This field is required."
            },
            {
                "field": "content_type",
                "code": "invalid_choice",
                "message": "\"video\" is not a valid content type."
            }
        ],
        "request_id": "req_abc130"
    }
}
```

### 10.2 Not Found (`404`)

```json
{
    "error": {
        "code": "NOT_FOUND",
        "message": "Conversation with id 999 not found.",
        "details": [],
        "request_id": "req_abc131"
    }
}
```

### 10.3 Conflict (`409`)

```json
{
    "error": {
        "code": "DUPLICATE_REVIEW",
        "message": "You have already submitted a review for this conversation.",
        "details": [
            {
                "field": "doctor",
                "code": "unique_together",
                "message": "A review by this doctor already exists for this conversation."
            }
        ],
        "request_id": "req_abc132"
    }
}
```

### 10.4 Rate Limited (`429`)

```json
{
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many messages. Please wait before sending another message.",
        "details": [],
        "request_id": "req_abc133"
    }
}
```

### 10.5 AI Service Error (`502`)

```json
{
    "error": {
        "code": "AI_SERVICE_ERROR",
        "message": "The AI service is temporarily unavailable. Your message has been saved and will be processed shortly.",
        "details": [],
        "request_id": "req_abc134"
    }
}
```

**Rationale for `502` instead of `500`:** When the LLM call fails, the user's message is already persisted. Returning `502 Bad Gateway` signals that the upstream AI provider is the problem, not our application logic. The client can retry with the same conversation and the system will recognise the last user message has no AI response yet.

---

## 11. Appendix — Decision Log

| Decision | Rationale |
|---|---|
| **Cursor pagination for messages** | Chat data grows from the bottom. OFFSET pagination causes duplicate/skipped records when new messages arrive between page requests. |
| **Page-based pagination for lists** | Conversations, reviews, and feedback are relatively stable. Page-based is simpler to implement and understand. |
| **`snake_case` not `camelCase`** | Matches Python/Django conventions. Avoids serialisation mapping. |
| **Single `POST /messages` for send+respond** | Simplifies frontend state machine. The AI pipeline is fast enough (<5s) for synchronous response in v1. |
| **Feedback upsert via `POST`** | One feedback per patient per message. Using POST with idempotency key avoids a separate GET-then-PUT dance. |
| **`feedback` nested in message list** | Eliminates N+1 queries when rendering a chat UI with feedback indicators. |
| **Triage returned at top level** | Urgency assessment is consumed by the UI immediately (e.g. red banner for urgent cases). Nesting it would force two lookups. |
| **No batch endpoints in v1** | Premature optimisation. Add `POST /batch/messages` only when network profiling proves it necessary. |
| **`502` for AI errors** | Distinguishes upstream provider failure from application bugs. Lets operations alert on provider health separately. |
| **`PATCH` for updates (not `PUT`)** | Partial updates are the dominant use case. Full replacement semantics of `PUT` add risk of accidental data loss. |
| **Doctor review state machine** | Enforces a predictable workflow. Prevents skipping from `requested` directly to `approved` without review. |
| **No WebSocket in v1** | Synchronous REST is simpler, cacheable, and works with every tool. WebSockets for streaming AI responses can be added in v2. |

---

*End of API Design Document*
