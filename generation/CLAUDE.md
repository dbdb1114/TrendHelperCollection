# CLAUDE.md — Generation (생성 계층, v1 Focus)

> **Purpose**  
> 이 문서는 **생성 계층(generation)** 에서 Claude가 따라야 할 **계약(Contract) + 작업 절차(Playbook)** 를 정의합니다.  
> v1에서는 분석 신호(예: `views_per_min`)를 입력으로 받아 **제목 3~5개, 태그 5~10개, 3-Beat 스크립트**를 생성하고 **스키마 검증 + 가드레일**을 통과한 결과만 반환합니다.

---

## Versioning Policy
- **Current Target:** **v1**
- v1 범위를 벗어나는 기능은 **`TODO:V2`** 로만 기록하고, 지금은 구현하지 않습니다.
- 질문은 **최대 1회**까지만 하고, 합리적 가정으로 **즉시 구현**을 진행합니다.
- **코드 제안은 patch/diff** 형태로 제시합니다(파일 전체 재작성 금지).

---

## Responsibilities (이 모듈이 하는 일)
- 입력(JSON 또는 DB 조회)을 받아 **아이디어 산출물(제목/태그/스크립트)** 을 생성합니다.
- 생성 결과는 **Pydantic 스키마로 엄격 검증**하고, **가드레일**을 통과하지 못하면 **자동 재생성**합니다.
- 로깅은 **JSON 라인(UTC)** 으로 남기며, `trace_id`를 포함합니다.

---

## Contracts (v1)

### Input (요청 JSON 스키마)
```json
{
  "video_id": "string or null",
  "keywords": ["아이폰17","루머"],
  "signals": {"views_per_min": 123.4},
  "style": {"tone":"info","language":"ko","length_sec":20}
}
```
- `video_id`: 특정 영상 기준으로 생성 시 지정(없어도 됨)
- `keywords`: 생성에 참고할 키워드(선택)
- `signals`: 분석 신호(최소한 `views_per_min` 권장)
- `style`: 톤/언어/길이 등 스타일링 옵션

### Output (응답 JSON 스키마)
```json
{
  "titles": ["...","...","..."],
  "tags": ["#아이폰17","#루머","#테크"],
  "script_beats": {"hook":"...","body":"...","cta":"..."},
  "metadata": {"model":"<provider>:<model_name>","safety_flags":[]}
}
```
- **Pydantic로 검증**: 길이/문자 제한/이모지 규칙 위반 시 실패 처리 → **자동 재생성**

### Guardrails (v1)
- **제목**
  - 길이: **20–35자**
  - 낚시성/과장 금지, **숫자 남용 금지**, **이모지 ≤ 1**
  - 금칙어/PII 금지
- **태그**
  - **핵심 3 + 롱테일 2–7**
  - 비속어/PII 금지, 중복/유사어 과다 금지
- **스크립트 (3-Beat)**
  - **Hook → Body → CTA**
  - **사실 기반·간결**, 길이 제한(`style.length_sec`) 준수

---

## Commands (from repo root)

### 아이디어 1건 생성
```bash
python generation/jobs/generate_ideas.py   --video-id <some_video_id>   --signals '{"views_per_min": 123.4}'   --style '{"tone":"info","language":"ko","length_sec":20}'   --out-file /tmp/idea.json
```
- 인자 없으면 인터랙티브/기본값으로 동작 가능
- 실패 시 **최대 N회** 재시도(기본 2–3회)

---

## Implementation Notes

### 모델 호출 추상화
- **환경변수 기반**으로 모델 공급자 선택(예: `MODEL_PROVIDER=anthropic|openai|...`, `MODEL_NAME=...`)
- 추상 인터페이스:
  ```python
  class IdeaModelClient:
      def generate(self, payload: dict) -> dict: ...
  ```
- 네트워크 오류/429/5xx는 **지수 백오프+Jitter** 로 재시도

### Pydantic 스키마 검증
- `TitlesSchema`, `TagsSchema`, `ScriptBeatsSchema`, `IdeaResponseSchema`
- 검증 실패 시 **가드레일 위반 종류**를 `metadata.safety_flags`에 기록
- 재시도 시 **위반 사유를 힌트**로 제공(프롬프트 내 system 규칙 보강)

### 로깅(JSON 라인)
- 공통: `ts(UTC)`, `level`, `logger`, `msg`, `trace_id`
- 생성 전/후: `job=generate_ideas`, `model`, `retry_count`, `violations`, `latency_ms`

### 결정적 재현(옵션)
- 입력 payload + `model` + `seed`(지원되는 경우)를 `metadata`에 보관

---

## Files to Create (Claude에게 요청할 작업)

1) `generation/jobs/generate_ideas.py`
   - CLI 인자 파싱(`argparse`)
   - 입력(payload) 준비 → **IdeaModelClient** 호출 → **스키마 검증/가드레일 검사** → 실패 시 **재시도**
   - 결과 출력(JSON) 및 `--out-file` 저장
   - 로깅(JSON 라인, UTC)

2) `generation/clients/model_client.py`
   - `IdeaModelClient` 추상화 + 구현 스텁(예: Anthropic/OpenAI)
   - `.env`에서 키/모델명 로드(**하드코딩 금지**)

3) `generation/schemas/idea.py`
   - Pydantic 스키마 정의(입력/출력/검증 로직 포함)

4) `generation/guardrails/rules.py`
   - 제목/태그/스크립트 규칙 함수화(길이/이모지/금칙어/PII 등)
   - 위반 사유 집계 유틸

---

## DoD Checklist (v1)
- [ ] `generate_ideas.py` 로 **제목 3–5, 태그 5–10, 3-Beat 스크립트** 생성 가능
- [ ] Pydantic 검증 통과 실패 시 **자동 재생성** 동작
- [ ] 가드레일 위반 종류가 `metadata.safety_flags`에 기록
- [ ] 로깅이 **JSON 라인(UTC)** 으로 남고 `trace_id` 포함
- [ ] `--out-file` 저장 시 올바른 JSON 생성

---

## Patch/Diff 제안 규칙
- **전체 파일 재작성 금지** — 변경은 **Unified Diff** 로 제시
- 새 파일 추가 시 경로/파일명/핵심 코드만 **patch 형태**로 제안

예시:
```diff
diff --git a/app/api/ideas.py b/app/api/ideas.py
--- a/app/api/ideas.py
+++ b/app/api/ideas.py
@@ -1,6 +1,10 @@
-from fastapi import APIRouter
+from fastapi import APIRouter
 from pydantic import BaseModel, Field
 router = APIRouter()

 class IdeaRequest(BaseModel):
     video_id: str | None = None
     keywords: list[str] = Field(default=[])
     signals: dict = Field(default_factory=dict)
     style: dict = Field(default_factory=dict)
+
+# TODO: import IdeaModelClient and wire up the generation call
```

---

## Safety & Policy
- **시크릿/키:** `.env`에서만 로드, 하드코딩 금지
- **콘텐츠 안전:** 비속어/혐오/PII 등 금칙어 필터링
- **시간/로깅:** UTC 통일, 개인정보 로그 금지

---

## TODO:V2 (미래 작업 메모)
- 배치 생성(`ideas/batch`), 프롬프트 튜닝 A/B, 사용자 피드백 루프
- 다국어 템플릿, 주제 버킷별 템플릿, 길이/톤 자동 보정
- Redis 캐시/중복 방지, 실패 원인 태깅 고도화
- 품질 평가 메트릭(제목 클릭률/시청유지율 연계) 설계
