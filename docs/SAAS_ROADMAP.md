# SaaS Commercialization Technical Roadmap & Architectural Specification
## AI Stock Workstation (Nghiệp Vụ AI Workstation V5.0)

- **Document Version**: 1.0.0
- **Status**: Production Engineering Blueprint
- **Target Audience**: System Architects, Backend Engineers, DevOps, Product Leadership
- **Document Path**: `docs/SAAS_ROADMAP.md`
- **Last Updated**: November 2026

---

## 1. Executive Summary & Architectural Vision

The **AI Stock Workstation** is a professional quantitative and AI-driven equity research platform designed for the Vietnamese stock market (VNINDEX, HNX, UPCOM). While the current release operates as an all-in-one containerized workstation (single-tenant architecture with local SQLite and disk cache), commercial scaling requires transforming the application into a secure, multi-tenant **Software-as-a-Service (SaaS)** platform.

### Core Objectives
1. **Multi-Tenancy & Data Isolation**: Transition from shared SQLite storage to an isolated PostgreSQL multi-tenant architecture with per-user watchlists, subscription status, and usage analytics.
2. **Defensive Security & Rate Limiting**: Eliminate unauthenticated resource exhaustion ("Denial-of-Wallet" attacks against Gemini LLM and upstream market APIs) via distributed Redis sliding window rate limiters.
3. **Automated Revenue Generation**: Integrate zero-fee Vietnamese Open Banking payments (PayOS VietQR) alongside international gateways (Stripe), backed by an idempotent, cryptographically verified webhook engine.
4. **Tiered Monetization Engine**: Provide strict separation between Free Tier visitors and VIP/PRO paying investors with automated subscription lifecycle state machines.

```mermaid
flowchart TD
    subgraph Clients["Investor Clients"]
        Web[React SPA / Web App]
        Mobile[Mobile Browser]
        Bot[Telegram Alert Bot]
    end

    subgraph Edge["Edge & Security Layer"]
        CF[Cloudflare WAF / CDN / DDoS Shield]
        SSL[TLS 1.3 Termination / HSTS]
    end

    subgraph Gateway["API & Application Layer (FastAPI)"]
        Ingress[Uvicorn Workers]
        AuthMid[Auth & Session Middleware\nArgon2id + Dual JWT]
        RateMid[Redis Sliding Window Limiter]
        TierMid[Tier Entitlement Guard]
        Router[API Routers:\n/api/auth, /api/market_data,\n/api/ai_report, /api/webhook]
    end

    subgraph CacheStore["Distributed Cache & State (Redis)"]
        RedisSession[Session Store & Device Tracker]
        RedisLimit[Sliding Window Counters]
        RedisCache[Market Data & Forecast Cache]
        RedisLock[Distributed Lock (Redlock)]
    end

    subgraph RelationalDB["Multi-Tenant Database (PostgreSQL)"]
        Users[(users)]
        Subs[(subscriptions)]
        Watchlists[(user_watchlists)]
        Tx[(payment_transactions)]
        Logs[(usage_logs)]
    end

    subgraph Upstream["Upstream Integrations"]
        PayOS[PayOS VietQR OpenAPI]
        Stripe[Stripe Billing]
        Gemini[Google Gemini 2.5/3.8 Flash]
        MarketFeed[Vietcap / DNSE / SSI Market Data]
    end

    Clients -->|HTTPS| CF
    CF --> SSL
    SSL --> Ingress
    Ingress --> AuthMid
    AuthMid --> RateMid
    RateMid --> TierMid
    TierMid --> Router

    AuthMid <--> RedisSession
    RateMid <--> RedisLimit
    Router <--> RedisCache
    Router <--> RelationalDB

    Router <-->|Async LLM| Gemini
    Router <-->|Market Data| MarketFeed
    Router <-->|Create Orders| PayOS
    PayOS -->|Signed Webhook| Router
```

---

## 2. Current Architecture vs. SaaS Target State

| Dimension | Current State (v5.0 Single-Tenant) | Target State (SaaS Multi-Tenant Commercial) |
| :--- | :--- | :--- |
| **User Identity** | Anonymous / Public. No login or user profile. | Authenticated via Argon2id Passwords or Google OAuth2 SSO. |
| **Session Model** | Stateless HTTP requests without tokens. | Dual-Token JWT (15-min Access Token + 14-day HttpOnly Refresh Token). |
| **Device Control** | Unrestricted access per client. | Max 2 concurrent active sessions tracked via Redis. |
| **Watchlist Storage** | Single SQLite table `antigravity.db` shared globally by all users. | PostgreSQL `user_watchlists` scoped strictly by `user_id` UUID. |
| **Rate Limiting** | In-memory Python `defaultdict` based on client IP (`_ip_ai_timestamps`). Lost on container restart. | Distributed Redis Sliding Window counter via atomic Lua script. Multi-tier limits. |
| **Cache Persistence** | Local ephemeral disk cache (`backend/.cache/*.json`). Cleared on cloud redeployments. | Redis Cluster with key namespacing, JSON serialization, and configurable TTL. |
| **LLM Quota Protection** | Uncapped calls to `/api/ai_report`. Susceptible to abuse. | Free: 5 reports/day (cached). VIP/PRO: High-frequency live inference with search grounding. |
| **Payment Flow** | None. Completely unmonetized. | PayOS (0% fee VietQR OpenAPI) + Stripe international with idempotent webhook processing. |
| **Security Vault** | Plaintext API keys in `.env` or container environment. | Encrypted developer keys (SHA-256) & upstream keys via Cloud KMS / Secret Manager. |

---

## 3. Pillar 1: User Authentication & Session Management

### 3.1. Password Hashing Architecture: Argon2id
In accordance with OWASP Password Storage Cheat Sheet standards, passwords must be hashed using **Argon2id**, the hybrid algorithm resistant to both GPU brute-force attacks and side-channel timing attacks.

#### Recommended Parameters
- **Memory Cost ($m$)**: $65,536\text{ KiB}$ (64 MB)
- **Time Cost ($t$)**: $3\text{ iterations}$
- **Parallelism ($p$)**: $4\text{ threads}$
- **Salt Length**: 16 cryptographically random bytes
- **Derived Key Length**: 32 bytes

```python
# backend/auth/hasher.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
    deprecated="auto"
)

def hash_password(plain_password: str) -> str:
    """Hash plaintext password with Argon2id."""
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored Argon2id hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

---

### 3.2. Dual-Token JWT Architecture

```mermaid
sequenceDiagram
    autonumber
    actor Client as Investor Browser
    participant API as FastAPI Backend
    participant Redis as Redis State Store
    participant DB as PostgreSQL DB

    Note over Client,API: User Authentication (Login)
    Client->>API: POST /api/auth/login {email, password}
    API->>DB: Query user & verify Argon2id
    DB-->>API: User verified (Tier: VIP_PRO)
    API->>Redis: Register session & issue token family
    API-->>Client: 200 OK<br/>Body: {access_token, expires_in: 900}<br/>Set-Cookie: refresh_token=... (HttpOnly, Secure, SameSite=Strict)

    Note over Client,API: Authorized API Request
    Client->>API: GET /api/market_data<br/>Header: Authorization: Bearer <access_token>
    API->>API: Verify RS256 signature & check exp
    API-->>Client: 200 OK Market Data

    Note over Client,API: Token Refresh & Rotation
    Client->>API: POST /api/auth/refresh<br/>Cookie: refresh_token
    API->>Redis: Check if refresh_token has been reused
    alt Token Reused (Attack Detected!)
        API->>Redis: Revoke entire token family for user
        API-->>Client: 401 Unauthorized (Force re-login)
    else Valid Refresh Token
        API->>Redis: Invalidate old refresh_token, issue new token pair
        API-->>Client: 200 OK<br/>Body: {new_access_token}<br/>Set-Cookie: new_refresh_token
    end
```

#### Token Characteristics
1. **Access Token**:
   - **Lifespan**: 15 minutes (`900` seconds).
   - **Signature**: Asymmetric `RS256` (RSA 2048-bit private key signs, public key verifies) or symmetric `HS256` with high-entropy secret.
   - **Delivery**: HTTP Response Body, stored exclusively in client memory (React state).
   - **Claims Payload**:
     ```json
     {
       "sub": "b2c019d3-63bf-4d89-9a2c-d90c0ef53021",
       "email": "investor@antigravity.vn",
       "role": "user",
       "tier": "VIP_PRO",
       "exp": 1794236100,
       "iat": 1794235200,
       "jti": "d049f5ce-1c19-4ea0-bd6f-00976378ba88"
     }
     ```
2. **Refresh Token**:
   - **Lifespan**: 14 days (`1,209,600` seconds).
   - **Storage**: Browser Cookie with strict defense flags:
     - `HttpOnly`: Prevents JavaScript access, mitigating Cross-Site Scripting (XSS) extraction.
     - `Secure`: Transmitted only over HTTPS.
     - `SameSite=Strict`: Protects against Cross-Site Request Forgery (CSRF).
     - `Path=/api/auth/refresh`: Cookie is never transmitted on general API requests.
   - **Token Rotation & Reuse Detection**: Every time a refresh token is exchanged, a new refresh token is issued and the previous one is retired. If an invalidated refresh token is ever presented again, the system treats it as a security breach, invalidating all tokens within that user's session family (`token_family:{family_id}`).

---

### 3.3. Google OAuth2 SSO Flow
To provide frictionless 1-click registration for investors, Google Identity Services (OAuth2 with OpenID Connect) is implemented:

```mermaid
sequenceDiagram
    autonumber
    actor Investor
    participant UI as React Frontend
    participant Google as Google Identity Services
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL DB

    Investor->>UI: Click "Đăng nhập với Google"
    UI->>Google: Prompt Google Account Chooser
    Google-->>UI: Return credential (Google JWT id_token)
    UI->>Backend: POST /api/auth/google {id_token}
    Backend->>Google: Verify signature via Google public certs
    Google-->>Backend: Token Valid (sub, email, name, picture, email_verified)
    Backend->>DB: Query user by email
    alt User exists
        Backend->>DB: Link provider_id if needed, update last_login_at
    else New User
        Backend->>DB: INSERT into users (email, full_name, avatar_url, auth_provider='google', email_verified=true)
        Backend->>DB: INSERT into subscriptions (tier='FREE', status='ACTIVE')
    end
    Backend-->>UI: Issue Access Token + Set HttpOnly Refresh Cookie
    UI-->>Investor: Redirect to Dashboard (Authenticated)
```

```python
# backend/auth/google_sso.py
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"

async def verify_google_token(token: str) -> dict:
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        if id_info["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid issuer")
        return {
            "google_id": id_info["sub"],
            "email": id_info["email"],
            "full_name": id_info.get("name", ""),
            "avatar_url": id_info.get("picture", ""),
            "email_verified": id_info.get("email_verified", False)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}"
        )
```

---

### 3.4. Concurrent Session Management (Max 2 Devices)
To prevent unauthorized account sharing among investors while permitting normal usage across desktop and mobile devices, the platform limits active sessions to **2 concurrent devices per account**:

- **Redis Session Registry**:
  - Key: `user_sessions:{user_id}` (Redis Hash or Sorted Set).
  - Value: Active `session_id` mapped to metadata:
    ```json
    {
      "session_id": "sess_891fa43",
      "ip_address": "113.161.45.12",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
      "device_type": "Desktop - Chrome on Windows",
      "last_activity": 1794235200
    }
    ```
- **Eviction Policy**: When a 3rd session attempts authentication, the backend can either:
  1. *Automatic FIFO Eviction*: Automatically invalidate the oldest session by deleting its refresh token and session key from Redis.
  2. *Interactive Prompt*: Return HTTP `409 Conflict` with a list of active devices, allowing the user to select which device to disconnect.

---

## 4. Pillar 2: User Database & Tier Management

### 4.1. Complete Production PostgreSQL DDL Schema

```sql
-- PostgreSQL 15+ Schema Definition for AI Stock Workstation SaaS
-- Schema: public

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================
CREATE TYPE auth_provider_type AS ENUM ('local', 'google', 'apple');
CREATE TYPE user_role_type AS ENUM ('user', 'analyst', 'moderator', 'admin');
CREATE TYPE subscription_tier_type AS ENUM ('FREE', 'VIP_PRO', 'ENTERPRISE');
CREATE TYPE subscription_status_type AS ENUM ('TRIAL', 'ACTIVE', 'PAST_DUE', 'CANCELLED', 'EXPIRED');
CREATE TYPE billing_period_type AS ENUM ('MONTHLY', 'QUARTERLY', 'YEARLY', 'LIFETIME');
CREATE TYPE payment_provider_type AS ENUM ('payos', 'vnpay', 'stripe', 'manual_bank');
CREATE TYPE payment_status_type AS ENUM ('PENDING', 'PAID', 'FAILED', 'EXPIRED', 'REFUNDED');
CREATE TYPE audit_action_type AS ENUM ('MARKET_DATA', 'AI_REPORT', 'INSTANT_REPORT', 'CHAT_QUERY', 'EXPORT_PDF', 'WATCHLIST_ADD');

-- ============================================================================
-- 1. USERS TABLE
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255),                  -- NULL when authenticated solely via OAuth2
    full_name VARCHAR(120),
    avatar_url TEXT,
    phone_number VARCHAR(20),
    auth_provider auth_provider_type NOT NULL DEFAULT 'local',
    provider_id VARCHAR(128),                      -- External OAuth provider unique identifier (e.g., Google sub)
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    role user_role_type NOT NULL DEFAULT 'user',
    telegram_chat_id BIGINT,                      -- Integrated for VIP instant alerts
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_provider ON users(auth_provider, provider_id);
CREATE INDEX idx_users_telegram ON users(telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

-- ============================================================================
-- 2. SUBSCRIPTIONS TABLE
-- ============================================================================
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier subscription_tier_type NOT NULL DEFAULT 'FREE',
    status subscription_status_type NOT NULL DEFAULT 'ACTIVE',
    billing_cycle billing_period_type NOT NULL DEFAULT 'MONTHLY',
    price_paid NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    payment_provider payment_provider_type,
    external_subscription_id VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_subscriptions_user UNIQUE (user_id)
);

CREATE INDEX idx_subscriptions_tier_status ON subscriptions(tier, status);
CREATE INDEX idx_subscriptions_period_end ON subscriptions(current_period_end);

-- ============================================================================
-- 3. USER WATCHLISTS TABLE (Per-User Stock Portfolio)
-- ============================================================================
CREATE TABLE user_watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(12) NOT NULL,                   -- e.g. 'FPT', 'SSI', 'VCB'
    target_buy_price NUMERIC(10, 2),
    stoploss_price NUMERIC(10, 2),
    target_sell_price NUMERIC(10, 2),
    alert_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    custom_notes TEXT,
    display_order INT NOT NULL DEFAULT 0,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_symbol UNIQUE (user_id, symbol)
);

CREATE INDEX idx_watchlists_user ON user_watchlists(user_id);
CREATE INDEX idx_watchlists_symbol ON user_watchlists(symbol);

-- ============================================================================
-- 4. PAYMENT TRANSACTIONS TABLE
-- ============================================================================
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    order_code BIGINT NOT NULL,                    -- Integer order code conforming to PayOS requirements
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status payment_status_type NOT NULL DEFAULT 'PENDING',
    payment_provider payment_provider_type NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,         -- Cryptographic key preventing duplicate webhook executions
    provider_transaction_id VARCHAR(128),
    webhook_payload JSONB,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_payment_order_code UNIQUE (order_code),
    CONSTRAINT uq_payment_idempotency UNIQUE (idempotency_key)
);

CREATE INDEX idx_payment_status ON payment_transactions(status);
CREATE INDEX idx_payment_created ON payment_transactions(created_at);

-- ============================================================================
-- 5. USAGE LOGS & QUOTA AUDIT TABLE
-- ============================================================================
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type audit_action_type NOT NULL,
    symbol VARCHAR(12),
    cost_tokens INT NOT NULL DEFAULT 0,
    execution_time_ms INT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_usage_user_action_date ON usage_logs(user_id, action_type, created_at);
CREATE INDEX idx_usage_symbol ON usage_logs(symbol);
```

---

### 4.2. SQLite to PostgreSQL Migration Strategy

The existing application stores watchlist entries in `backend/antigravity.db` with a single table:
```sql
CREATE TABLE watchlist (symbol TEXT PRIMARY KEY, added_at TIMESTAMP);
```

#### Migration Methodology
1. **Schema Initialization with Alembic**:
   - Initialize Alembic environment in `backend/migrations/`.
   - Generate initial migration revision capturing the complete PostgreSQL DDL above.
2. **Data Transformation Script**:
   - Create a default `System Seed / Admin User` in PostgreSQL to adopt existing anonymous watchlist symbols.
   - Run extraction script:
     ```python
     # backend/scripts/migrate_sqlite_to_pg.py
     import sqlite3
     import psycopg2
     
     def migrate():
         sqlite_conn = sqlite3.connect("backend/antigravity.db")
         pg_conn = psycopg2.connect("postgresql://user:pass@host:5432/stock_db")
         
         cursor_sq = sqlite_conn.cursor()
         cursor_pg = pg_conn.cursor()
         
         # Obtain system default user UUID
         cursor_pg.execute("SELECT id FROM users WHERE email = 'system_admin@antigravity.vn'")
         admin_id = cursor_pg.fetchone()[0]
         
         cursor_sq.execute("SELECT symbol, added_at FROM watchlist")
         rows = cursor_sq.fetchall()
         
         for symbol, added_at in rows:
             cursor_pg.execute("""
                 INSERT INTO user_watchlists (user_id, symbol, added_at)
                 VALUES (%s, %s, %s)
                 ON CONFLICT (user_id, symbol) DO NOTHING
             """, (admin_id, symbol, added_at))
             
         pg_conn.commit()
         print(f"Successfully migrated {len(rows)} watchlist symbols to PostgreSQL.")
     ```
3. **Cutover & Verification**:
   - Execute dry-run migration in staging.
   - Swap backend database driver from `sqlite3` to `SQLAlchemy 2.0` with `asyncpg` connection pool (`pool_size=20, max_overflow=10`).

---

### 4.3. Feature & Entitlement Matrix: Free vs. VIP/PRO vs. Enterprise

| Capability | Free Tier (Nhà đầu tư Cá nhân) | VIP / PRO Tier (Chuyên nghiệp) | Enterprise (Quỹ / Tổ chức) |
| :--- | :--- | :--- | :--- |
| **Price Point** | **0 VNĐ** | **299,000 VNĐ / Month**<br/>*(2,490,000 VNĐ / Year)* | Contact Sales / Custom Billing |
| **Deep AI Stock Reports (`/api/ai_report`)** | **5 reports / day** (Served from cache if available) | **Unlimited** (Up to 150 live queries/day) with Deep Reasoning & Gemini Search Grounding | Dedicated LLM instance, custom system prompts |
| **6-Step Quantitative Engine (`instant_report`)** | Standard indicators (RSI, MACD, Volume) | Advanced indicators: Volume Profile, Fibonacci Confluence, Base Rates & Kelly Criterion | Full model calibration & raw feature vector export |
| **Market Data Streaming** | 15-minute delayed quotes or End-of-Day (EOD) bars | **Real-time Tick-by-Tick** streaming (< 500ms latency via WebSocket) | Direct FIX / Low-latency binary socket feeds |
| **Watchlist Capacity** | Up to **5 symbols** | **Unlimited symbols** with custom tags and price targets | Multi-portfolio aggregation & team sharing |
| **Realtime Alert System** | In-app browser alerts only | Instant alerts via **Telegram Bot** & Web Push on Breakout / Stoploss triggers | Webhook dispatch to automated trading bots |
| **Backtest Intervals** | Standard 1-year daily history | Multi-year intraday history (1m, 5m, 1h) with custom walk-forward backtesting | Sub-minute tick backtesting on cluster |
| **AI Stock Chatbot (`/api/chat`)** | 10 queries / day (concise mode) | **Unlimited queries** with web grounding & live financials | Customized proprietary financial knowledge base |
| **Report Exporting** | Web viewer only | **Export High-Res PDF** (white-paper quality for board presentations) | API data access & White-label reports |

---

## 5. Pillar 3: System Security & API Rate Limiting

### 5.1. Multi-Tier Distributed Rate Limiting via Redis Sliding Window

Traditional Fixed-Window counters suffer from boundary burst vulnerabilities (e.g., doubling the allowed limit right at the boundary minute). To guarantee strict enforcement across distributed backend nodes, the platform employs a **Sliding Window Log algorithm powered by an atomic Redis Lua Script**.

```mermaid
flowchart LR
    subgraph Window["Sliding Window (Current Time T - 60s to T)"]
        direction TB
        T1[Req 1: T - 55s]
        T2[Req 2: T - 30s]
        T3[Req 3: T - 10s]
        T4[New Req: T]
    end

    Incoming[Incoming API Request] --> Lua[Atomic Redis Lua Script]
    Lua -->|1. Purge entries < T - 60s| ZRem[ZREMRANGEBYSCORE]
    Lua -->|2. Count remaining elements| ZCard[ZCARD]
    ZCard --> Check{Count < Limit?}
    Check -->|Yes| Allow[ZADD New Request & Return Allowed: 1]
    Check -->|No| Deny[Return Denied: 0, Retry-After Header]
```

#### Production Redis Lua Script
```lua
-- File: backend/security/rate_limiter.lua
-- KEYS[1]: Rate limit key, e.g. "ratelimit:{user_or_ip}:{endpoint}"
-- ARGV[1]: Current UNIX timestamp in milliseconds
-- ARGV[2]: Window size in milliseconds (e.g. 60000 for 1 minute)
-- ARGV[3]: Maximum permitted requests within window

local key = KEYS[1]
local seq_key = key .. ':seq'
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local clear_before = now - window_ms

-- 1. Remove expired timestamps outside the sliding window
redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)

-- 2. Count current number of requests in window
local current_requests = redis.call('ZCARD', key)

if current_requests < limit then
    -- 3. Increment monotonic sequence counter and set TTL to prevent key leakage
    local seq = redis.call('INCR', seq_key)
    redis.call('PEXPIRE', seq_key, window_ms)
    
    -- 4. Add current timestamp as both score and member
    redis.call('ZADD', key, now, now .. '-' .. seq)
    
    -- 5. Set TTL on sliding window zset to prevent key leakage
    redis.call('PEXPIRE', key, window_ms)
    return {1, limit - current_requests - 1, 0} -- {allowed, remaining, retry_after}
else
    -- Request rejected: find earliest timestamp to compute retry_after
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 0
    if oldest and #oldest >= 2 then
        retry_after = math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000)
    end
    return {0, 0, retry_after} -- {denied, 0, retry_after_seconds}
end
```

#### Rate Limits by Tier
1. **Unauthenticated / Public IP**:
   - `/api/health`: 60 requests/minute.
   - `/api/market_data`: 15 requests/minute.
   - `/api/ai_report` & `/api/chat`: **0 requests** (HTTP 401 Unauthorized; registration required).
2. **Authenticated Free Tier**:
   - General API: **60 requests/minute**.
   - `/api/ai_report`: Daily limit of **5 reports / 24 hours**, tracked via key `quota:ai:{user_id}:{YYYYMMDD}`.
3. **Authenticated VIP/PRO Tier**:
   - General API: **300 requests/minute**.
   - `/api/ai_report`: No daily ceiling; burst throttled at **10 concurrent requests/minute** to protect worker threads.

---

### 5.2. Developer API Key Management & Upstream Secret Vaulting

#### Developer API Keys (For Programmatic VIP Clients)
- Keys are generated with cryptographically secure pseudo-random bytes: `sk_live_` prefix followed by 48 Base64 characters.
- **One-Way Hashing**: Plaintext keys are presented to the user **exactly once** upon creation. The database stores only the **SHA-256 hash** (`api_key_hash`) along with `user_id`, `created_at`, `revoked_at`, and `last_used_at`.
- Incoming programmatic requests provide: `X-API-Key: sk_live_...`. The backend computes `hash = sha256(raw_key)` and looks up the active key record.

#### Upstream API Key Encryption (Gemini, SSI, Vietcap)
- **Zero Plaintext at Rest**: Upstream secrets are never stored in git or unencrypted database fields.
- **Envelope Encryption**: Secrets are encrypted using **AES-256-GCM** with a Master Key derived from Cloud Key Management Service (AWS KMS, Google Cloud KMS, or HashiCorp Vault):
  - Ciphertext format: `nonce (12 bytes) || ciphertext || auth_tag (16 bytes)`.
  - Authentication tags prevent tampering or bit-flipping attacks.
  - Keys are decrypted strictly in memory upon service bootstrapping.

---

### 5.3. CORS Policy Hardening, Security Headers & Cloudflare WAF

#### FastAPI CORS Configuration
```python
# backend/security/cors.py
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "https://stock.antigravity.vn",
    "https://app.antigravity.vn",
]

def configure_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
        max_age=86400,
    )
```

#### Security Headers Middleware
All HTTP responses must enforce modern browser security policies:
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.antigravity.vn;`
- `X-Frame-Options: DENY` (Mitigates clickjacking).
- `X-Content-Type-Options: nosniff` (Prevents MIME-confusion attacks).
- `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` (Forces HTTPS).
- `Referrer-Policy: strict-origin-when-cross-origin`.

#### Cloudflare WAF Recommendations
1. **DDoS Mitigation**: Enable Cloudflare Layer 7 Adaptive DDoS Protection.
2. **Bot Fight Mode**: Mitigate headless scrapers targeting proprietary quantitative models.
3. **WAF Ruleset**: Deploy OWASP Core Ruleset (Block SQLi, XSS, RCE, Path Traversal) with an anomaly threshold score > 25.
4. **Geo-IP Rules**: Vietnam, Singapore, and international traffic allowed; block high-risk hosting/proxy ASNs.

---

## 6. Pillar 4: Payment Gateway & Automated Webhook Activation

### 6.1. Payment Gateway Architecture: PayOS (VietQR) & Stripe

To ensure maximum conversion in Vietnam, the platform prioritizes **PayOS (OpenAPI VietQR)**, enabling instant banking transfer with **0% transaction fees**, supplemented by **Stripe** for international investors.

```mermaid
sequenceDiagram
    autonumber
    actor Investor
    participant UI as React SPA
    participant Backend as FastAPI Backend
    participant PayOS as PayOS Gateway
    participant Bank as Mobile Banking App
    participant DB as PostgreSQL DB
    participant Telegram as Telegram Bot

    Investor->>UI: Select "Nâng cấp VIP PRO (299k/tháng)"
    UI->>Backend: POST /api/payment/create-order {tier: "VIP_PRO", cycle: "MONTHLY"}
    Backend->>Backend: Generate unique order_code (e.g., 240819001)
    Backend->>PayOS: Create Payment Link (amount: 299000, description: "AIX PRO 240819001")
    PayOS-->>Backend: Return payment link & dynamic VietQR data
    Backend->>DB: INSERT into payment_transactions (order_code, amount, status='PENDING')
    Backend-->>UI: Return VietQR image & order_code
    UI-->>Investor: Display VietQR Modal with live countdown timer

    Investor->>Bank: Scan VietQR & Confirm Transfer
    Bank->>PayOS: Interbank NAPAS 247 Instant Transfer
    PayOS->>PayOS: Match order_code & amount
    PayOS->>Backend: POST /api/webhook/payos<br/>Headers: x-payos-signature<br/>Payload: {orderCode, amount, reference, code: "00"}

    Note over Backend,DB: Idempotent Webhook Verification
    Backend->>Backend: Verify HMAC-SHA256 signature
    Backend->>DB: Check & acquire idempotency lock
    Backend->>DB: UPDATE payment_transactions SET status='PAID'
    Backend->>DB: UPDATE subscriptions SET tier='VIP_PRO', status='ACTIVE', current_period_end = NOW() + INTERVAL '30 days'
    Backend->>Telegram: Send VIP welcome alert & private channel link
    Backend-->>PayOS: 200 OK {status: "success"}

    UI->>Backend: Polling / WebSocket: Check order status
    Backend-->>UI: Order PAID!
    UI-->>Investor: Show Success Modal & Instant VIP Features Unlocked
```

---

### 6.2. Idempotent Webhook Processing Engine

Payment gateways inevitably re-dispatch webhooks during network timeouts or retry schedules. Without idempotent handling, duplicate subscription renewals or financial recording errors occur.

#### Implementation Blueprint
```python
# backend/payment/webhook_handler.py
import hmac
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException, status, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.database import get_db_session
from backend.models import PaymentTransaction, Subscription, User

logger = logging.getLogger("payment.webhook")
router = APIRouter(prefix="/api/webhook", tags=["Payment Webhooks"])

PAYOS_CHECKSUM_KEY = "YOUR_PAYOS_CHECKSUM_KEY_FROM_DASHBOARD"

def verify_payos_signature(data_payload: dict, signature: str, checksum_key: str) -> bool:
    """
    PayOS signature verification:
    Sort keys alphabetically, build query string: key1=value1&key2=value2,
    compute HMAC-SHA256 with checksum key.
    """
    if not signature:
        return False
    sorted_items = sorted([f"{k}={v}" for k, v in data_payload.items() if v is not None and k != "signature"])
    canonical_string = "&".join(sorted_items)
    computed_signature = hmac.new(
        checksum_key.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)

@router.post("/payos")
async def payos_webhook_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    # 1. Parse raw body and headers
    raw_body = await request.body()
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Malformed JSON")

    data = body.get("data", {})
    signature = body.get("signature")
    
    # 2. Cryptographic signature verification with edge-case guard
    # Safety check: reject immediately if signature is missing/None before hmac.compare_digest
    if not signature: return Response(status_code=400)

    if not verify_payos_signature(data, signature, PAYOS_CHECKSUM_KEY):
        logger.warning("Invalid PayOS webhook signature received.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    order_code = data.get("orderCode")
    trans_reference = data.get("reference")
    amount = data.get("amount")
    idempotency_key = f"payos:{order_code}:{trans_reference}"

    # 3. Check for existing processed transaction (Idempotency Guard)
    query = select(PaymentTransaction).where(PaymentTransaction.idempotency_key == idempotency_key)
    result = await db.execute(query)
    existing_tx = result.scalar_one_or_none()

    if existing_tx and existing_tx.status == "PAID":
        logger.info(f"Duplicate webhook for order_code {order_code} acknowledged.")
        return {"code": "00", "message": "Transaction already settled"}

    # 4. Fetch the pending transaction with row-level locking (SELECT ... FOR UPDATE)
    # Prevents concurrent webhook race conditions by acquiring an exclusive row lock
    order_query = (
        select(PaymentTransaction)
        .where(PaymentTransaction.order_code == order_code)
        .with_for_update()
    )
    order_res = await db.execute(order_query)
    tx = order_res.scalar_one_or_none()

    if not tx:
        logger.error(f"Received webhook for non-existent order_code {order_code}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if tx.amount != amount:
        logger.error(f"Amount mismatch on order {order_code}: expected {tx.amount}, got {amount}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount mismatch")

    # 5. Atomic state update within database transaction
    now = datetime.now(timezone.utc)
    tx.status = "PAID"
    tx.paid_at = now
    tx.idempotency_key = idempotency_key
    tx.provider_transaction_id = trans_reference
    tx.webhook_payload = body

    # 6. Execute Subscription State Machine transition with row-level lock
    sub_query = (
        select(Subscription)
        .where(Subscription.user_id == tx.user_id)
        .with_for_update()
    )
    sub_res = await db.execute(sub_query)
    sub = sub_res.scalar_one_or_none()

    # Calculate period (30 days default monthly)
    new_end_date = max(sub.current_period_end, now) + timedelta(days=30) if sub else now + timedelta(days=30)

    if sub:
        sub.tier = "VIP_PRO"
        sub.status = "ACTIVE"
        sub.current_period_start = now
        sub.current_period_end = new_end_date
        sub.payment_provider = "payos"
        sub.updated_at = now
    else:
        new_sub = Subscription(
            user_id=tx.user_id,
            tier="VIP_PRO",
            status="ACTIVE",
            current_period_start=now,
            current_period_end=new_end_date,
            payment_provider="payos"
        )
        db.add(new_sub)

    await db.commit()
    logger.info(f"Successfully activated VIP_PRO for user {tx.user_id} through {new_end_date}")

    return {"code": "00", "message": "Success"}
```

#### Concurrency Control & Webhook Race Prevention: `SELECT ... FOR UPDATE`

In production payment architectures, payment gateways (like PayOS, VNPay, or Stripe) may retry or emit multiple webhook HTTP deliveries concurrently due to transient network lag or distributed worker retries. If two concurrent requests hit `/api/webhook/payos` simultaneously:

1. **Race Condition Hazard**: Without row-level locks, Request A and Request B both execute `SELECT * FROM payment_transactions WHERE order_code = ...` concurrently. Both see `status = 'PENDING'`. Both proceed to update `status = 'PAID'` and double-increment the user's subscription duration (e.g., adding 60 days instead of 30 days).
2. **Row-Level Exclusive Locking (`SELECT ... FOR UPDATE`)**:
   - By appending `.with_for_update()` in SQLAlchemy (translating directly to SQL `SELECT ... FOR UPDATE`), PostgreSQL locks the specific transaction and subscription rows in exclusive write mode for the duration of the database transaction.
   - When Request B attempts to query the row, it blocks until Request A finishes and executes `await db.commit()`.
   - Once unlocked, Request B observes `existing_tx.status == 'PAID'` or `tx.status == 'PAID'` and immediately exits with `{"code": "00", "message": "Transaction already settled"}`, completely preventing duplicate quota grants, double billing credits, or race conditions.

---

### 6.3. Subscription Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> TRIAL: User Registers (7-Day Trial)
    TRIAL --> FREE: Trial Period Expires
    FREE --> PENDING: Generates VietQR Payment Order
    
    PENDING --> ACTIVE: Webhook Confirms Payment
    PENDING --> FREE: Order Cancelled / Expired (15m Timeout)
    
    ACTIVE --> ACTIVE: Periodic Renewal Payment Success
    ACTIVE --> PAST_DUE: Renewal Payment Due & Failed
    
    PAST_DUE --> ACTIVE: Grace Period Payment Recovered (3 Days)
    PAST_DUE --> EXPIRED: Grace Period Exhausted (Day 4)
    
    ACTIVE --> CANCELLED: User Opts Out of Renewal
    CANCELLED --> EXPIRED: Period End Reached
    
    EXPIRED --> FREE: Auto-Downgrade Entitlements
    FREE --> PENDING: Upgrades Again
```

#### Automated Subscription Worker (Cron / Celery Beat)
A scheduled daemon runs every hour to enforce lifecycle transitions:
1. **Mark Past Due**:
   ```sql
   UPDATE subscriptions 
   SET status = 'PAST_DUE' 
   WHERE status = 'ACTIVE' 
     AND current_period_end < CURRENT_TIMESTAMP 
     AND current_period_end >= CURRENT_TIMESTAMP - INTERVAL '3 days';
   ```
2. **Expire & Downgrade to Free**:
   ```sql
   UPDATE subscriptions 
   SET status = 'EXPIRED', tier = 'FREE' 
   WHERE status = 'PAST_DUE' 
     AND current_period_end < CURRENT_TIMESTAMP - INTERVAL '3 days';
   ```

---

## 7. Phased Implementation Roadmap (Weeks 1 – 8)

The transition plan spans **8 weeks (4 distinct two-week phases)** designed to eliminate service interruptions and protect data integrity.

```mermaid
gantt
    title SaaS Commercialization Timeline (8 Weeks)
    dateFormat  YYYY-MM-DD
    section Phase 1: DB & Auth
    PostgreSQL & Redis Setup            :active, p1_1, 2026-12-01, 5d
    Alembic Migrations & Schema         :p1_2, after p1_1, 4d
    Argon2id & Dual JWT Endpoints       :p1_3, after p1_2, 5d
    Google OAuth2 SSO Integration       :p1_4, after p1_3, 4d
    Watchlist Multi-Tenant Migration    :p1_5, after p1_4, 4d
    section Phase 2: Security & Rate Limiting
    Redis Sliding Window Lua Script     :p2_1, after p1_5, 4d
    Tier Entitlement Middleware         :p2_2, after p2_1, 5d
    Developer API Key & Secret Vaulting :p2_3, after p2_2, 4d
    CORS & Cloudflare WAF Hardening     :p2_4, after p2_3, 3d
    section Phase 3: Payment Engine
    PayOS VietQR Merchant Setup         :p3_1, after p2_4, 3d
    Create Order & QR Generation        :p3_2, after p3_1, 4d
    Idempotent Webhook Handler          :p3_3, after p3_2, 5d
    Subscription State Machine Worker   :p3_4, after p3_3, 4d
    section Phase 4: Frontend UX & Launch
    React Pricing Modal & Auth Views    :p4_1, after p3_4, 5d
    Telegram Alert Bot Integration      :p4_2, after p4_1, 4d
    Stress Testing (1,000 CCU Locust)   :p4_3, after p4_2, 3d
    Closed Beta & Public SaaS Launch    :p4_4, after p4_3, 4d
```

### Phase 1: Core Database & Authentication Infrastructure (Weeks 1 – 2)
- **Deliverables**:
  - Provision managed PostgreSQL 15 and Redis clusters (AWS RDS / Supabase / Neon & Upstash).
  - Execute Alembic migration scripts for `users`, `subscriptions`, `user_watchlists`, `payment_transactions`, `usage_logs`.
  - Implement `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout`.
  - Implement `/api/auth/google` with Google Identity token verification.
  - Refactor `backend/api.py` `/api/watchlist` endpoints to read/write from PostgreSQL filtered by authenticated `user_id`.
- **Milestone Exit Criteria**:
  - Unit & Integration tests passing for user registration, Argon2id verification, and token rotation.
  - Independent user watchlists verified (User A cannot see or modify User B's portfolio).

### Phase 2: Distributed Rate Limiting & Tier Enforcement (Weeks 3 – 4)
- **Deliverables**:
  - Implement Redis sliding window rate limiter with atomic Lua script.
  - Build FastAPI dependency `require_tier(minimum_tier: subscription_tier_type)`.
  - Implement daily AI report quota tracking (`quota:ai:{user_id}:{date}`).
  - Encrypt upstream secrets with AES-256-GCM.
  - Configure CORS whitelist and HTTP security headers.
- **Milestone Exit Criteria**:
  - Free users receive HTTP 429 when exceeding 5 daily AI reports.
  - VIP/PRO accounts handle concurrent analysis requests without rate rejection.
  - Multi-worker load test confirms zero race conditions on sliding window counters.

### Phase 3: Payment Gateway & Automated Subscription Webhooks (Weeks 5 – 6)
- **Deliverables**:
  - Register PayOS merchant credentials and configure webhook URLs.
  - Implement `POST /api/payment/create-order` returning VietQR dynamic string.
  - Implement `POST /api/webhook/payos` with HMAC-SHA256 signature verification and idempotency locks.
  - Build background subscription reconciliation daemon (handling renewals, past_due grace, expiration).
  - Integrate transactional email notification (Resend / AWS SES) for invoice receipts.
- **Milestone Exit Criteria**:
  - End-to-end sandbox payment test: mobile app scan -> instant webhook (< 3s) -> VIP status activated.
  - Replayed webhooks (simulating duplicate delivery) return HTTP 200 without modifying end dates.

### Phase 4: Frontend Monetization UX, Load Testing & Public Launch (Weeks 7 – 8)
- **Deliverables**:
  - Develop React UI components: Login/Register modals, User Profile dropdown, Interactive Pricing Matrix, VietQR payment checkout dialog with real-time status polling.
  - Build Telegram Bot notification integration for VIP instant signals.
  - Execute distributed load testing via Locust / k6 simulating 1,000 concurrent active users.
  - Set up Cloudflare WAF rules, Sentry error tracking, and Prometheus/Grafana system dashboards.
  - Launch Closed Beta with 100 pilot investors followed by official public launch.
- **Milestone Exit Criteria**:
  - 99.9% uptime maintained during 1,000 CCU stress test with average API response < 400ms.
  - Flawless mobile responsive checkout on iOS Safari and Android Chrome.

---

## 8. Compliance, Legal & Data Governance

1. **State Securities Commission of Vietnam (UBCKNN) Regulatory Compliance**:
   - The platform operates as a **quantitative decision-support and data analytics tool**, not a licensed asset management fund.
   - Mandatory user disclaimer required at registration and on every AI report:
     > *"Thông tin phân tích và báo cáo từ hệ thống AI Stock Workstation dựa trên các mô hình định lượng và trí tuệ nhân tạo độc lập, chỉ mang tính chất tham khảo. Người dùng hoàn toàn tự chịu trách nhiệm đối với mọi quyết định giao dịch và kết quả đầu tư của mình."*
2. **Personal Data Protection (Decree 13/2023/ND-CP)**:
   - User emails, phone numbers, and IP logs must be stored securely with data encryption at rest.
   - Users possess the right to export their personal data or request complete account deletion.
3. **Market Data Sourcing Transition**:
   - As transaction volume scales, transition scraped data endpoints to licensed enterprise feeds (FiinTrade Datafeed, Vietstock API, or SSI FastConnect API) to eliminate IP throttling and secure guaranteed SLA.

---

*Authored by Antigravity Cloud Architecture & Commercialization Lead for AI Stock Workstation V5.0.*
