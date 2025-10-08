# CLAUDE.md — Service (서비스 계층, v1 Focus)

> **Purpose**  
> 이 문서는 **서비스 계층(service)** 에서 Claude가 따라야 할 **계약(Contract) + 작업 절차(Playbook)** 를 정의합니다.  
> v1에서는 HTTP API 계층(`app/`)과 도메인/인프라 계층(`analysis/`, `generation/`, `core/`) 사이에서 **오케스트레이션**을 담당합니다.

---

## Versioning Policy
- **Current Target:** **v1**
- v1 범위를 벗어나는 기능은 **`TODO:V2`** 로만 기록하고, 지금은 구현하지 않습니다.
- 질문은 **최대 1회**까지만 하고, 합리적 가정으로 **즉시 구현**을 진행합니다.
- **코드 제안은 patch/diff** 형태로 제시합니다(파일 전체 재작성 금지).

---

## Responsibilities (이 모듈이 하는 일)
- **유스케이스 오케스트레이션**: 입력 검증 완료된 DTO를 받아 분석/생성/DB를 **순서대로 호출**하고 결과를 합성하여 반환합니다.
- **트랜잭션 경계**: 필요한 경우 DB 트랜잭션을 열고, 실패 시 롤백합니다.
- **에러 매핑**: 하위 계층 예외를 **의도한 도메인 에러**로 변환하여 API에 전달합니다.
- **로깅/추적**: `trace_id`를 **전파/기록**합니다(UTC, JSON 라인).
- **Idempotency(선택)**: 요청 중복 방지를 위한 키를 수용하되, v1에선 기본 비활성.

> HTTP 라우팅/직렬화는 `app/`에서 담당, 비즈니스 흐름/규칙은 `service/`에서 담당합니다.

---

## Public Interfaces (v1)

### 1) Health
```python
def get_health() -> dict:
    \"\"간단한 헬스 체크 결과 반환(고정 값) - DB 핑은 v2에서 확장\"\"
    return { "ok": True }
```

### 2) Ideas (핵심)
```python
from service.dto import IdeaRequestDTO, IdeaResponseDTO

def create_ideas(dto: IdeaRequestDTO, *, trace_id: str, session, model_client) -> IdeaResponseDTO:
    \"\"입력 DTO를 받아 generation 계층을 호출하고, 가드레일/스키마 검증을 통과한 결과를 반환\"\"
```

- **입력 DTO**: `video_id | None`, `keywords: list[str]`, `signals: dict`, `style: dict`
- **출력 DTO**: `titles: list[str]`, `tags: list[str]`, `script_beats: dict`, `metadata: dict`
- **의존성**: `session(SQLAlchemy)`, `model_client(IdeaModelClient)`

---

## Contracts & Rules

### 입력/출력 계약
- `app/` 레이어에서 **Pydantic 요청 스키마** 검증을 통과한 후에만 `service/`로 진입합니다.
- `service/`는 도메인 규칙(가드레일) 위반 시 **재시도 지시**(generation 계층) 또는 **도메인 예외**를 던집니다.

### 에러 모델 (API에 노출될 최소 형태)
```json
{ "error": { "code": "VALIDATION_FAILED", "message": "title length > 35", "trace_id": "..." } }
```
- 대표 코드: `VALIDATION_FAILED`, `RATE_LIMITED`, `DEPENDENCY_UNAVAILABLE`, `INTERNAL_ERROR`

### 로깅(JSON 라인, 예시)
```json
{"ts":"2025-01-01T00:00:00Z","level":"INFO","logger":"service.ideas","msg":"generate ok","trace_id":"...","latency_ms":312,"model":"...","retry_count":1}
```

### 공통 규칙
- **UTC 시간**, **.env**에서 **시크릿 로드**, **개인정보 로그 금지**.
- **부분 성공 허용**: 일부 실패 항목은 스킵하고 `metadata.safety_flags`로 수집.

---

## Files to Create (Claude에게 요청할 작업)

1) `service/dto.py`
- Pydantic DTO (**API 스키마와 거의 동일하지만**, 내부 전용 기본값/검증을 약간 다르게 둘 수 있음)
- `IdeaRequestDTO`, `IdeaResponseDTO`

2) `service/ideas_service.py`
- `create_ideas(dto, trace_id, session, model_client)` 구현
- 가드레일/재시도 정책은 `generation`의 반환값에 따라 조정
- 실패 시 예외 매핑(도메인 에러 → API 에러 코드로 변환)

3) `service/health_service.py`
- `get_health()` 간단 구현(v1 고정값)

4) (연결) `app/api/ideas.py`, `app/api/health.py`
- **주의:** 본 문서는 `service/` 규칙이므로 실제 라우터 구현은 `app/`에서 수행  
- 라우터에선 `deps`로 `session`, `model_client`, `trace_id`를 주입

5) `app/deps/common.py` (선택)
- `get_db_session()`, `get_trace_id()`, `get_model_client()` 등 DI 헬퍼

---

## Commands (from repo root)

### 로컬 서버 실행
```bash
uvicorn app.main:app --reload
```

### 헬스 체크
```bash
curl -s http://localhost:8000/health | jq
```

### 아이디어 생성 (예시)
```bash
curl -s -X POST http://localhost:8000/ideas   -H 'Content-Type: application/json'   -d '{"video_id": null, "keywords": ["아이폰17","루머"], "signals": {"views_per_min": 123.4}, "style": {"tone":"info","language":"ko","length_sec":20}}' | jq
```

---

## Implementation Notes

### 트랜잭션 & 의존성 주입
- 짧은 요청/응답 수명 주기: `session`을 요청 단위로 열고 종료
- `model_client`는 팩토리 또는 DI 컨테이너에서 생성
- `trace_id`는 미들웨어/헤더에서 전달받아 서비스까지 전파

### 재시도/가드레일
- `generation`에서 Pydantic/가드레일 실패 시 **최대 N회 재생성**(기본 2–3회)
- 실패 사유는 `metadata.safety_flags`로 누적

### 에러 매핑 전략
- 하위 계층(HTTP/DB) 예외 → `DependencyError`
- 규칙 위반/입력 이상 → `DomainValidationError`
- 위 예외는 `app/` 레이어에서 HTTP 4xx/5xx로 변환

### 보안/CORS (v1 최소)
- v1은 퍼블릭 엔드포인트로 인증 없음. (v2에서 OAuth/JWT/레이트리밋 추가)

---

## DoD Checklist (v1)
- [ ] `/health`가 200 OK로 `{ "ok": true }` 반환
- [ ] `/ideas`가 **스키마 검증 통과한 JSON**을 200 OK로 반환
- [ ] 가드레일 위반 시 **재생성 또는 4xx**로 적절히 응답
- [ ] 서비스 로그가 **JSON 라인(UTC)** 으로 남고 `trace_id` 포함
- [ ] 예외가 **도메인 에러 → API 에러 코드**로 일관되게 매핑

---

## Patch/Diff 규칙
- **전체 파일 재작성 금지** — 변경은 **Unified Diff** 로 제시
- 새 파일 추가 시 경로/파일명/핵심 코드만 **patch 형태**로 제안
- Alembic 마이그레이션 파일은 기존 리비전 **수정 금지**(새 리비전만 추가)

---

## Safety & Policy
- **시크릿/키:** `.env`에서만 로드, 하드코딩 금지
- **개인정보:** 로그/응답에 PII 금지
- **시간/로깅:** UTC 통일, JSON 라인 포맷

---

## TODO:V2 (미래 작업 메모)
- `/trending`, `/ideas/batch` 엔드포인트 추가
- 레이트리밋, 인증/인가(OAuth/JWT), 캐시/메트릭/알림
- DB 헬스(핑) 포함한 심층 헬스체크, 준비성/활성성 프로브
- 서킷브레이커/리트라이 정책 고도화, Idempotency-Key 지원
