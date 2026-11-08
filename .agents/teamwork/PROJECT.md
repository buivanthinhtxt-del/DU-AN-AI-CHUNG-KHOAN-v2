# Project: AI Chứng Khoán (2-DU-AN-AI-CHUNG-KHOAN) - Stress-Test & Deep Audit + P0 Remediation

## Architecture Overview
System for Vietnamese Stock Market Analysis powered by AI/LLM, real-time/historical data ingestion, technical analysis engine, and web/dashboard interface.
- Core Data Ingestion & Sources: APIs (VCI, KBS, DNSE, etc. - TCBS deprecated)
- Caching & Storage: Local atomic JSON cache + In-memory TTL, SQLite WAL
- Analytics & TA Engine: Standard Wilder's RSI RMA, EMA/MACD, Zero Look-ahead historical filter, Intraday Volume pacing
- AI Reasoning Engine: Gemini API integration, prompt engineering with genuine FA/Foreign flow grounding, structured Pydantic JSON outputs, fast-abort on 4xx & backoff on 429/503
- Frontend / User Interface: Modular React architecture, Lightweight Charts with Candlestick + Volume + EMA + Buy/Sell markers, Actionable Trading HUD, Trading days date-math

## Feature Inventory
| # | Feature / Requirement | Description | Pillar | Assigned Milestone | Status |
|---|----------------------|-------------|--------|--------------------|--------|
| 1 | Market Trading Hours & Calendar | ATO/ATC, continuous, weekend, holiday, off-hour queries | R1 | M1 / M2 / M3 | DONE |
| 2 | Settlement Cycle T+2.5 | T+2.5 13:00 cycle integration in indicators & predictions | R1 | M1 / M2 / M3 | DONE |
| 3 | Critical Market Data Ingestion | Foreign net buy/sell, Prop trading, 3-level order depth, FA metrics | R1 | M1 / M2 / M3 | DONE |
| 4 | Multi-source Data Resilience | Fallbacks (VCI, KBS, DNSE), exponential backoff, circuit breaker | R2 | M1 / M2 / M3 | DONE |
| 5 | Intraday Realtime TA & No Look-ahead Bias | Realtime candle stitching, accurate Wilder RSI/MACD/EMA calculation | R2 | M1 / M2 / M3 | DONE |
| 6 | AI Hallucination & Context Guard | Prompt constraints, raw candle stuffing prevention, factual grounding | R3 | M1 / M2 / M3 | DONE |
| 7 | Structured AI Output & Error Handling | JSON schema enforcement, Gemini 429/503 fallback & fast-abort 4xx | R3 | M1 / M2 / M3 | DONE |
| 8 | Backend Performance & Non-blocking I/O | Eliminating sync blocking network calls, async responsiveness | R4 | M1 / M2 / M3 | DONE |
| 9 | Cache Concurrency & Security | Eliminating JSON race conditions, zero hardcoded API keys, logs | R4 | M1 / M2 / M3 | DONE |
| 10 | Frontend Interactivity & Actionable Insights | Interactive charts, Buy/Sell markers, entry, TP1/2, SL, position size | R5 | M1 / M2 / M3 | DONE |
| 11 | Comprehensive Audit Report Publication | AUDIT_REPORT.md with 4 required sections and 1-10 scores | R6 | M1 (Audit) | DONE |
| 12 | P0 Vulnerability Remediation | Fix security, crash, blocking I/O, cache race, math, Gemini quota | R7 | M2 (P0 Fixes) | DONE |
| 13 | Automated Verification Test Suite | Full syntax/import validation, API endpoint schema verification | R8 | M3 (Verify) | DONE |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Deep Technical & Domain Audit | Exhaustive audit of all 5 pillars by 3 expert council perspectives -> generate AUDIT_REPORT.md at project root | None | DONE |
| M2 | P0 Critical Vulnerability Remediation | Direct remediation of all 14 P0 security, concurrency, blocking I/O, financial formula, and LLM resilience flaws | M1 | DONE |
| M3 | Automated Verification & Integrity Audit | Execute automated verification script, test imports & API endpoints, forensic integrity audit | M2 | DONE |
