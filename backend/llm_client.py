"""
Lớp gọi Gemini dùng chung cho toàn hệ thống.

Sửa lỗi gốc của bản cũ: google-genai xếp HTTP 429 (hết quota) vào `errors.ClientError`, nên code cũ coi 429
là "lỗi xác thực", dừng ngay và trả về bản phân tích định lượng sơ sài — dù các model khác vẫn còn quota.
Ở đây chỉ dừng hẳn khi khóa API sai/không có quyền; hết quota / quá tải / model không tồn tại → chuyển model kế tiếp,
và tạm "cách ly" model hết quota trong 15 phút để các request sau không tốn thời gian thử lại.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("llm_client")

# Ưu tiên model mạnh nhất trước; có thể ghi đè bằng biến môi trường GEMINI_MODELS="m1,m2,..."
DEFAULT_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
# Free tier giới hạn theo PHÚT (RPM/TPM) và theo NGÀY (RPD). 429 theo phút → cách ly ngắn; theo ngày → cách ly 1 giờ.
COOLDOWN_PER_MINUTE_S = 65
COOLDOWN_PER_DAY_S = 3600
COOLDOWN_NOT_FOUND_S = 24 * 3600
RETRY_WAIT_S = 20
COOLDOWN_TIMEOUT_S = 300
# Timeout từng lần gọi (giây). Bản cũ 300s/lần × 6 model => có thể treo ~30 phút khi tra cứu web bị nghẽn.
CALL_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "90"))
SEARCH_CALL_TIMEOUT_S = float(os.getenv("GEMINI_SEARCH_TIMEOUT_S", "75"))
# Ngân sách tổng cho một lần generate() qua mọi model (giây)
TOTAL_BUDGET_S = float(os.getenv("GEMINI_TOTAL_BUDGET_S", "180"))

_cooldown: dict[str, float] = {}
_lock = threading.Lock()
_clients: dict[str, genai.Client] = {}


class LLMAuthError(RuntimeError):
    """Khóa API sai / bị thu hồi / không có quyền — không nên thử model khác."""


class LLMUnavailable(RuntimeError):
    """Mọi model đều không dùng được (quota, quá tải, lỗi mạng...)."""


def get_api_key() -> Optional[str]:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key or key == "your_gemini_api_key_here":
        return None
    return key


def _ck(model: str, use_search: bool) -> str:
    # Hạn mức Google Search grounding tách biệt với hạn mức sinh văn bản → cách ly riêng
    return f"{model}|search" if use_search else model


def candidate_models(use_search: bool = False) -> list[str]:
    env = os.getenv("GEMINI_MODELS", "").strip()
    models = [m.strip() for m in env.split(",") if m.strip()] if env else list(DEFAULT_MODELS)
    now = time.time()
    with _lock:
        ready = [m for m in models if _cooldown.get(_ck(m, use_search), 0) <= now and _cooldown.get(m + "|404", 0) <= now]
    # Nếu tất cả đang bị cách ly, vẫn thử lại toàn bộ (quota có thể đã hồi)
    return ready or models


def _client(api_key: str) -> genai.Client:
    c = _clients.get(api_key)
    if c is None:
        c = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=300_000))
        _clients[api_key] = c
    return c


def classify_error(e: Exception) -> str:
    code = getattr(e, "code", None)
    msg = str(e)
    if code in (401, 403) or "API_KEY_INVALID" in msg or "API key not valid" in msg or "PERMISSION_DENIED" in msg:
        return "auth"
    if code == 429 or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return "quota"
    if code == 404 or "NOT_FOUND" in msg or "is not found" in msg:
        return "not_found"
    if isinstance(e, errors.ServerError) or (isinstance(code, int) and code >= 500) or "UNAVAILABLE" in msg or "overloaded" in msg.lower():
        return "unavailable"
    if code == 400:
        return "bad_request"
    low = msg.lower()
    if "timed out" in low or "timeout" in low or type(e).__name__ in ("ReadTimeout", "ConnectTimeout", "TimeoutException"):
        return "timeout"
    return "other"


def generate(
    prompt: str,
    system: Optional[str] = None,
    json_schema: Optional[dict] = None,
    use_search: bool = False,
    temperature: float = 0.3,
    models: Optional[list[str]] = None,
    label: str = "LLM",
    retry_on_rate_limit: bool = True,
    budget_s: Optional[float] = None,
) -> tuple[str, str, object]:
    """
    Gọi Gemini với cơ chế failover giữa các model.
    Trả về (text, model_name, raw_response). Ném LLMAuthError hoặc LLMUnavailable khi thất bại.
    """
    api_key = get_api_key()
    if not api_key:
        raise LLMUnavailable("Chưa cấu hình GEMINI_API_KEY trong file .env")

    client = _client(api_key)
    cfg = {"temperature": temperature}
    if system:
        cfg["system_instruction"] = system
    if json_schema is not None:
        cfg["response_mime_type"] = "application/json"
        cfg["response_json_schema"] = json_schema
    if use_search:
        cfg["tools"] = [types.Tool(google_search=types.GoogleSearch())]
    per_call_s = SEARCH_CALL_TIMEOUT_S if use_search else CALL_TIMEOUT_S
    deadline = time.time() + (budget_s if budget_s is not None else TOTAL_BUDGET_S)

    def _config_for_remaining() -> types.GenerateContentConfig:
        # Không để một lần gọi vượt quá phần ngân sách còn lại (tối thiểu 10s)
        remaining = max(10.0, min(per_call_s, deadline - time.time()))
        return types.GenerateContentConfig(**cfg, http_options=types.HttpOptions(timeout=int(remaining * 1000)))

    model_list = list(models or candidate_models(use_search))
    errors_seen = []
    for attempt in range(2):
        kinds = []
        for model in model_list:
            if time.time() >= deadline:
                errors_seen.append("hết ngân sách thời gian")
                logger.warning(f"[{label}] Hết ngân sách {TOTAL_BUDGET_S:.0f}s → dừng thử model khác")
                raise LLMUnavailable("; ".join(errors_seen))
            t0 = time.time()
            try:
                logger.info(f"[{label}] Gọi model {model}...")
                resp = client.models.generate_content(model=model, contents=prompt, config=_config_for_remaining())
                text = (resp.text or "").strip()
                if not text:
                    errors_seen.append(f"{model}: phản hồi rỗng")
                    kinds.append("empty")
                    continue
                logger.info(f"[{label}] {model} trả lời sau {time.time() - t0:.1f}s ({len(text)} ký tự)")
                return text, model, resp
            except Exception as e:  # noqa: BLE001 — phân loại bên dưới
                kind = classify_error(e)
                kinds.append(kind)
                short = str(e).split("\n")[0][:120]
                per_day = "PerDay" in str(e)
                errors_seen.append(f"{model}: {kind}{' (theo ngày)' if per_day else ''}")
                logger.warning(f"[{label}] {model} lỗi [{kind}{'/ngày' if per_day else ''}] sau {time.time() - t0:.1f}s: {short}")
                if kind == "auth":
                    raise LLMAuthError(f"Khóa GEMINI_API_KEY không hợp lệ hoặc không có quyền: {short}") from e
                with _lock:
                    if kind == "quota":
                        _cooldown[_ck(model, use_search)] = time.time() + (COOLDOWN_PER_DAY_S if per_day else COOLDOWN_PER_MINUTE_S)
                    elif kind == "not_found":
                        _cooldown[model + "|404"] = time.time() + COOLDOWN_NOT_FOUND_S
                    elif kind == "timeout":
                        # Model đang nghẽn (thường gặp với Google Search grounding) → bỏ qua tạm 5 phút
                        _cooldown[_ck(model, use_search)] = time.time() + COOLDOWN_TIMEOUT_S
                continue
        # Mọi model đều bị giới hạn THEO PHÚT → chờ ngắn rồi thử lại một lượt (giới hạn RPM hồi lại rất nhanh)
        retryable = [m for m, k in zip(model_list, kinds) if k in ("quota", "unavailable", "empty")]
        if (retry_on_rate_limit and attempt == 0 and retryable and not any("theo ngày" in e for e in errors_seen)
                and deadline - time.time() > RETRY_WAIT_S + 15):
            logger.warning(f"[{label}] Tất cả model đang bị giới hạn tạm thời → chờ {RETRY_WAIT_S}s rồi thử lại")
            time.sleep(RETRY_WAIT_S)
            model_list = retryable
            continue
        break
    raise LLMUnavailable("; ".join(errors_seen) or "Không có model nào khả dụng")


def grounding_sources(resp) -> list[dict]:
    """Bóc danh sách nguồn web từ grounding metadata của Google Search."""
    out, seen = [], set()
    try:
        gm = resp.candidates[0].grounding_metadata
        for ch in (getattr(gm, "grounding_chunks", None) or []):
            web = getattr(ch, "web", None)
            uri = getattr(web, "uri", None) if web else None
            if uri and uri not in seen:
                seen.add(uri)
                out.append({"title": getattr(web, "title", None) or "Nguồn web", "url": uri})
    except Exception:
        pass
    return out


def force_required(schema: dict) -> dict:
    """
    Chuẩn hóa JSON schema của Pydantic cho Gemini:
    - Inline toàn bộ $ref/$defs (tránh phụ thuộc mức hỗ trợ $ref của API).
    - Đánh dấu mọi thuộc tính là bắt buộc (đệ quy) để model không bỏ sót mục nào.
    - Bỏ 'default'/'title' của từng node schema (không đụng tới tên thuộc tính).
    """
    s = json.loads(json.dumps(schema))
    defs = s.pop("$defs", {})

    def resolve(node):
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                merged = {**defs.get(name, {}), **{k: v for k, v in node.items() if k != "$ref"}}
                return resolve(merged)
            out = {}
            for k, v in node.items():
                if k == "properties" and isinstance(v, dict):
                    out[k] = {pk: resolve(pv) for pk, pv in v.items()}
                elif k in ("default", "title"):
                    continue
                else:
                    out[k] = resolve(v)
            if out.get("type") == "object" and isinstance(out.get("properties"), dict):
                out["required"] = list(out["properties"].keys())
            return out
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(s)
