# 5-COMPONENT HANDOFF REPORT: SYSTEMS ARCHITECT & CTO AUDIT
## Phase 1: Stress-Test & Deep Audit (R2 - Data Resilience & R4 - Backend Architecture)

**Agent**: Explorer Survey 2 (`explorer_survey_2`)  
**Role**: CTO & Distributed Systems Architect  
**Recipient**: Orchestrator Council (`561bec3b-3da6-43f1-a97b-5a4ed73cc1c8`)  
**Date**: 2026-11-08  
**Handoff Type**: Hard (Audit survey completed, ready for Phase 2 Remediation)  

---

### 1. OBSERVATION

1. **Observation 1 (Look-ahead Bias / Future Data Leakage)**:
   - File: `backend/data_fetcher.py:90-98`
   - Code:
     ```python
     if target_date:
         end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
     else:
         end_date = datetime.now() + timedelta(days=1)
     start_date = end_date - timedelta(days=days)
     start_str = start_date.strftime('%Y-%m-%d')
     end_str = end_date.strftime('%Y-%m-%d')
     ```
   - Command & Output verification:
     Ran `& .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from data_fetcher import get_historical_data; df = get_historical_data('HPG', 10, target_date='2026-04-14', include_indicators=False); print('Requested target_date: 2026-04-14'); print('Last date in df:', df.index[-1].strftime('%Y-%m-%d'))"`
     Result:
     `Requested target_date: 2026-04-14`
     `Last date in df: 2026-04-15`
     Verbatim finding: The query for 2026-04-14 loaded data up to 2026-04-15 (future day) due to `timedelta(days=1)` because `vnstock`'s `q.history(start, end)` is inclusive of `end`.

2. **Observation 2 (Broken Data Source TCBS in vnstock 3.5.1)**:
   - File: `backend/data_fetcher.py:102`
   - Code: `for source in ('VCI', 'TCBS', 'KBS'):`
   - Verbatim error when running:
     `TCBS FAIL Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`
     `vnstock` version: `3.5.1`. `TCBS` is completely rejected by the `Quote` class.

3. **Observation 3 (Blocking I/O on FastAPI Async Event Loop)**:
   - File: `backend/api.py:84,107,169,203,209`
   - Code:
     `@app.post("/api/market_data") async def fetch_market_data(req: AnalyzeRequest):`
     `df = future_df.result(timeout=45)`
     `@app.post("/api/ai_report") async def fetch_ai_report(req: AnalyzeRequest):`
     `idx_df = fut.result(timeout=20)`
     `analysis_json_str = analyze_stock_data(...)`
   - Synchronous network calls (`client.interactions.create` to Gemini, `.result(timeout=...)` on thread futures) and file reads/writes are called directly inside `async def` endpoints, blocking Uvicorn's main event loop thread for up to 45 seconds per request.

4. **Observation 4 (Cache Concurrency Hazard & Race Condition)**:
   - File: `backend/cache_manager.py:22-23,44-45`
   - Code:
     `with open(cache_file, "r", encoding="utf-8") as f: data = json.load(f)`
     `with open(cache_file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)`
   - No file locking, no atomic write (`open(..., "w")` truncates the file to 0 bytes immediately upon opening), no thread lock, no disk eviction.

5. **Observation 5 (Security Exposure & CORS Misconfiguration)**:
   - File: `backend/api.py:48-54`
   - Code: `app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, ...)`
   - File: `backend/api.py:109,166,232`
   - Code: `raise HTTPException(status_code=500, detail=str(e))`
   - Verbatim: HTTP 500 exposes raw exception strings containing absolute filesystem paths (`D:\2- LÀM VIỆC\...`) and library internals.

6. **Observation 6 (Broken Automated Test Infrastructure)**:
   - File: `backend/tests/test_api.py:2`
   - Command: `& .\.venv\Scripts\python.exe backend\tests\test_api.py`
   - Verbatim error:
     `RuntimeError: The starlette.testclient module requires the httpx package to be installed.`
   - File: `backend/requirements.txt:1-10` lacks `httpx`.

---

### 2. LOGIC CHAIN

1. From **Observation 1**, `target_date + timedelta(days=1)` combined with vnstock's inclusive date boundary yields records from `target_date + 1`. Because `latest = df.iloc[-1]` in `ai_analyzer.py:155` and `calculate_indicators` in `data_fetcher.py:121` process the full returned series, the model and indicators ingest future data. Therefore, the backtest and analysis pipeline suffers from a critical **Look-ahead Bias**.
2. From **Observation 2**, `Quote(symbol=..., source='TCBS')` raises a ValueError on every execution. In `data_fetcher.py:102-127`, this error triggers an exception block, wasting CPU cycles and leaving only `VCI` and `KBS` as operative sources without a true multi-broker resilience layer.
3. From **Observation 3**, in ASGI/FastAPI architecture, an `async def` handler is executed on the primary event loop thread. When blocking methods (`future.result()`, synchronous socket operations, synchronous disk I/O) are called on this thread, the entire event loop is starved. As a result, concurrent incoming HTTP requests are blocked from processing, causing severe latency degradation under concurrency.
4. From **Observation 4**, opening a file in `"w"` mode truncates the file before writing. When another concurrent coroutine or process executes `get_cache()` on that exact file, `json.load()` encounters an empty buffer, resulting in `json.decoder.JSONDecodeError`. On Windows, concurrent open attempts trigger `PermissionError: [WinError 32]`.
5. From **Observation 5**, combining `allow_origins=["*"]` with `allow_credentials=True` violates CORS specifications and allows arbitrary web origins to send requests to the local backend. Relaying `str(e)` in HTTP 500 leaks absolute server paths and environment details to untrusted clients.
6. From **Observation 6**, `fastapi.testclient.TestClient` requires `httpx`. Because `httpx` is absent from `requirements.txt`, running automated API tests immediately crashes with `RuntimeError`, rendering the project's verification test suite non-functional out of the box.

---

### 3. CAVEATS

- **Caveat 1**: The current audit was executed against the local repository in `development` integrity mode without active Gemini API keys (mock/fallback mode was validated).
- **Caveat 2**: While `vnstock` 3.5.1 was evaluated, the impending transition to Vnstock generation 6 (scheduled for Nov 10, 2026 per official notice) was noted as an upcoming external dependency risk; long-term production resilience requires decoupled direct broker adapters (e.g., DNSE, SSI).
- **Caveat 3**: No live production traffic load test (e.g. via Locust or k6) was run against the server; performance evaluations are based on static code analysis, execution tracing, and single-concurrency failure reproduction.

---

### 4. CONCLUSION

1. **System Scores**:
   - **Trụ cột 2 (R2 - Tính Tức thời & Hạ tầng Dữ liệu Đa nguồn)**: **3.5 / 10**
   - **Trụ cột 4 (R4 - Hiệu năng, Kiến trúc Backend & An toàn Dữ liệu)**: **3.0 / 10**
2. **Readiness Verdict**: The system is **NOT production ready**. It contains 6 P0 critical flaws that must be remediated in Phase 2:
   - **P0-DATA-01**: Look-ahead Bias in `data_fetcher.py`.
   - **P0-PERF-01**: Event loop blocking in `api.py`.
   - **P0-RES-01**: Cache race conditions in `cache_manager.py`.
   - **P0-SEC-01**: Permissive CORS + sensitive internal error leaks in `api.py`.
   - **P0-RES-02**: Dead TCBS source & fragile fallback in `data_fetcher.py`.
   - **P0-TEST-01**: Missing test dependency `httpx` breaking test execution.
3. Detailed technical report, vulnerability inventory, and next-generation architecture roadmap are published at:
   `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_2\systems_architect_audit.md`.

---

### 5. VERIFICATION METHOD

To independently verify these findings, run the following commands from the workspace root:

1. **Verify Look-ahead Bias (P0-DATA-01)**:
   ```powershell
   & .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from data_fetcher import get_historical_data; df = get_historical_data('HPG', 10, target_date='2026-04-14', include_indicators=False); print('Target date requested: 2026-04-14'); print('Actual last row in df:', df.index[-1].strftime('%Y-%m-%d'))"
   ```
   *Expected result*: Demonstrates that the last row is `2026-04-15` (leaking future day).

2. **Verify Broken TCBS Source (P0-RES-02)**:
   ```powershell
   & .\.venv\Scripts\python.exe -c "from vnstock.api.quote import Quote; Quote('FPT', source='TCBS').history('2026-04-01', '2026-04-10')"
   ```
   *Expected result*: Raises `ValueError: Lớp Quote chỉ nhận giá trị tham số source là kbs, vci, msn, dnse, binance, fmp, fmarket.`

3. **Verify Broken Test Suite (P0-TEST-01)**:
   ```powershell
   & .\.venv\Scripts\python.exe backend\tests\test_api.py
   ```
   *Expected result*: Raises `RuntimeError: The starlette.testclient module requires the httpx package to be installed.`

4. **Verify Audit Documentation**:
   Inspect files:
   - `.agents\teamwork\explorer_survey_2\systems_architect_audit.md`
   - `.agents\teamwork\explorer_survey_2\handoff.md`
   - `.agents\teamwork\explorer_survey_2\BRIEFING.md`
