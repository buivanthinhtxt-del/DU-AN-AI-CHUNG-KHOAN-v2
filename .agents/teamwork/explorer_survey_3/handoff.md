# HANDOFF REPORT — EXPLORER SURVEY 3 (AI/LLM & FRONTEND SPECIALIST)

**Agent Role**: Principal AI/LLM Engineer & Senior Frontend Specialist  
**State Folder**: `d:\2- LÀM VIỆC\2- github du an 1\2-DU-AN-AI-CHUNG-KHOAN\.agents\teamwork\explorer_survey_3\`  
**Target Milestone**: Giai đoạn 1 (Deep Audit & Stress-Test R3 & R5)  
**Handoff Type**: Hard Handoff (Audit Task Complete)

---

## 1. OBSERVATION

1. **AI Hallucination & Missing Grounding Data**:
   - In `backend/ai_analyzer.py:202`:
     `"fundamentals": f"Nhóm ngành: {sector_name}. (Đánh giá nội lực kết hợp từ kiến thức tài chính và tin tức doanh nghiệp bên dưới)",`
     No financial statements (P/E, P/B, ROE, Debt/Equity, Revenue, Net Income) are injected into the LLM prompt.
   - In `backend/prompts/tro_ly_dau_tu_chung_khoan_vn.md:297-298`:
     `- Giá trị giao dịch HOSE: {market_value} tỷ đồng`
     `- Khối ngoại mua/bán ròng: {foreign_net} tỷ đồng`
     In `backend/ai_analyzer.py:180-219`, `market_value` and `foreign_net` are never passed into `values`, defaulting to `"N/A"`.
   - In `backend/.cache/ai_report_FPT_None.json:11-13`:
     Gemini hallucinated or complained: *"Tuy nhiên, dữ liệu đầu vào không cung cấp chất xúc tác cụ thể, rõ ràng cho FPT trong ngắn hạn..."*.

2. **Model Cascade Failure & Lack of Error Differentiation**:
   - In `backend/ai_analyzer.py:370`:
     `candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-4-argon"]`
     Model `"gemini-4-argon"` is invalid / non-existent.
   - In `backend/ai_analyzer.py:373-395`:
     When running `$env:GEMINI_API_KEY="dummy_key_12345"`, execution log showed:
     `[!] Model gemini-3.8-flash gặp lỗi: Error code: 400 - [{'error': {'code': 400, 'message': 'API key not valid...'}}]`
     followed immediately by sequential calls to `gemini-3.5-flash-lite` and `gemini-4-argon`.
     Total elapsed time was 8.6 seconds for a single request, with zero backoff/jitter and zero fast-abort on 4xx client errors.

3. **Cache Incompatibility & Unvalidated Price Predictions**:
   - In `backend/ai_analyzer.py:41-45, 57`:
     `summary: ReportSummary = Field(...)` is a required field without default.
   - In `backend/.cache/ai_report_FPT_None.json:4-55` and `ai_report_HPG_None.json:4-55`:
     Neither file contains the `"summary"` field. Deserialization throws `pydantic.ValidationError`.
   - In `backend/.cache/ai_report_FPT_None.json:32, 38`:
     `days_future: 0` appeared twice in predictions ("Morning" and "Afternoon").
     `PricePredictionItem` lacks validation constraints verifying `days_future > 0` and `high >= low`.

4. **Frontend Architecture Disconnect (Monolithic vs Components)**:
   - In `web/src/App.jsx:1-4`:
     Does not import `web/src/components/StockChart.jsx`, `AnalysisReport.jsx`, `PriceTargetsAndPeers.jsx`, `RadarScoreCard.jsx`, `Sidebar.jsx`, `MacroTicker.jsx`, or `web/src/services/apiClient.js`.
   - In `web/src/App.jsx:40, 55, 63, 84, 99`:
     Hardcoded `fetch('http://127.0.0.1:8000/api/...')` instead of using `apiClient.js`.
   - In `web/src/App.jsx:196-255`:
     The inline chart omitted EMA10, SMA20, and Volume Histogram which were implemented in `web/src/components/StockChart.jsx:48-72`.

5. **Zero Buy/Sell Markers on Candlestick Chart**:
   - Running PowerShell command `Get-ChildItem -Path web\src -Recurse -Filter "*.jsx" | Select-String -Pattern "marker|setMarkers"` returned 0 matches across the entire codebase.

6. **Catastrophic Typewriter CPU Freezing & ESLint Errors**:
   - In `web/src/App.jsx:118-122`:
     `typewriterRef.current = setInterval(() => { setTypedAnalysis((prev) => prev + text.charAt(i)); i++; ... }, 8);`
     For an 8,000-character report, this triggers 8,000 React re-renders every 8ms.
   - In `web/src/App.jsx:351-405`:
     Every re-render executes `formatReport()` which parses all lines, regexes, and tables.
   - Running `cd web; npm run lint` produced 4 problems (3 errors, 1 warning):
     `App.jsx:47` (unused `e`), `App.jsx:234` (unused `e`), `App.jsx:262` (missing dependency in `useEffect`), `AnalysisReport.jsx:135` (synchronous `setState` inside `useEffect`).

7. **Missing Test Dependency in Backend**:
   - Running `.venv\Scripts\python backend\tests\test_api.py` produced:
     `RuntimeError: The starlette.testclient module requires the httpx package to be installed.`
     `backend/requirements.txt` is missing `httpx`.

---

## 2. LOGIC CHAIN

1. **Step 1 (R3 Prompt Grounding)**:
   - Observation 1 showed that `{fundamentals}`, `{market_value}`, and `{foreign_net}` are empty placeholders.
   - Deductions: An LLM without domain facts must synthesize answers from its weights. In financial markets, weights become obsolete within days. Thus, Gemini's scores on Step 2 (FA) and Step 1 (Flow) are ungrounded hallucinations.

2. **Step 2 (R3 Resilience)**:
   - Observation 2 showed that `candidate_models` includes a fictional name (`gemini-4-argon`) and does not stop on 400 fatal errors.
   - Deductions: When an invalid key or transient quota limit occurs, all 3 requests execute sequentially, creating high blocking latency (~9s) and exposing the system to IP banning by Google.

3. **Step 3 (R3 Schema Stability)**:
   - Observation 3 showed that `summary` is required in schema but absent in existing cache files.
   - Deductions: Any call to deserialize cached data using `StockAIReportSchema.model_validate_json()` crashes the API with `ValidationError`.

4. **Step 4 (R5 Frontend Architecture)**:
   - Observation 4 showed that `App.jsx` bypasses `web/src/components/*` entirely.
   - Deductions: The codebase suffers from technical debt where good modular components are abandoned while a bloated 581-line monolith is actively rendered. Charting features (EMA/SMA/Volume) are stripped as a result.

5. **Step 5 (R5 Actionable Trading Insights & Markers)**:
   - Observation 5 and 6 showed that Buy/Sell markers are 0% implemented and the typewriter re-renders 8,000 times.
   - Deductions: The user cannot visually act on trade signals on the chart, and trying to read the text causes browser tab freeze.

---

## 3. CAVEATS

1. The test execution of `backend/tests/test_api.py` could not complete due to missing `httpx` in `.venv`.
2. Did not test live Google GenAI generation with a real funded paid API key, as only the environment key was available. Live behaviour was verified via existing cached responses and error simulations.
3. No changes to source code were performed during this turn, strictly adhering to the Read-Only constraint of Phase 1 (Audit).

---

## 4. CONCLUSION

- **Pillar 3 (R3) Score: 5.5 / 10**
  Prompt design and structured schema foundation are solid, but missing fundamental data (FA/Foreign flow), an invalid model name (`gemini-4-argon`), lack of backoff/jitter, and cache schema drift pose serious reliability risks.
- **Pillar 5 (R5) Score: 4.5 / 10**
  Dark aesthetic is decent, but the frontend suffers from component schism (abandoned `components/`), complete lack of Buy/Sell markers on candlestick chart, severe CPU throttling caused by 8ms typewriter re-renders, and buried trade recommendations.
- **Detailed Audit Report**: Published at `.agents/teamwork/explorer_survey_3/ai_frontend_audit.md`.

---

## 5. VERIFICATION METHOD

1. **Verify Missing Fundamentals & Prompt Data**:
   Inspect `backend/ai_analyzer.py:180-219`. Note that `market_value` and `foreign_net` are absent in `values`, and `fundamentals` is a hardcoded static string.
2. **Verify Sequential Model Cascade & Invalid Model**:
   Inspect `backend/ai_analyzer.py:370-395`. Run:
   `$env:PYTHONPATH="backend"; $env:GEMINI_API_KEY="dummy"; .venv\Scripts\python -c "import pandas as pd; from ai_analyzer import analyze_stock_data; df = pd.DataFrame({'Open': [10], 'High': [11], 'Low': [9], 'Close': [10.5], 'Volume': [1000]}); analyze_stock_data('HPG', df)"`
   Observe the 3 sequential 400 errors and elapsed time.
3. **Verify Zero Buy/Sell Markers**:
   Run: `Get-ChildItem -Path web\src -Recurse -Filter "*.jsx" | Select-String -Pattern "setMarkers"`
   Result will be empty.
4. **Verify Typewriter CPU Freezing & ESLint**:
   Run: `cd web; npm run lint`
   Observe the 4 ESLint problems. Inspect `web/src/App.jsx:118-122` for the 8ms interval.
5. **Verify Missing httpx in Backend**:
   Run: `.venv\Scripts\python backend\tests\test_api.py`
   Observe `RuntimeError: The starlette.testclient module requires the httpx package to be installed.`
