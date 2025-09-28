# YouTube Trend Shorts Helper — 기술 문서 (v0.3)
> **상태**: Living Doc · 본 문서는 지속 보완 예정  
> **범위**: 수집계층/분석계층(기존) + **생성계층/서비스계층(신규 추가)**  
> **목적**: 웹개발자/비전공자도 이해할 수 있도록 개념 위주로 설명하여, Google/Reddit/Threads 등에서 추가 학습과 질문이 가능하도록 돕습니다.

---

## 목차
1. [문서 범위 & 배경](#문서-범위--배경)
2. [아키텍처 한눈에 보기](#아키텍처-한눈에-보기)
3. [수집계층 (Data Collection Layer) — 요약](#수집계층-data-collection-layer-—-요약)
4. [분석계층 (Data Processing & Analysis Layer) — 요약](#분석계층-data-processing--analysis-layer-—-요약)
5. [**생성계층 (Generation Layer)**](#생성계층-generation-layer)
   - 5.1 [기능 명세](#51-기능-명세)
   - 5.2 [입출력 스키마(초안)](#52-입출력-스키마초안)
   - 5.3 [사용 기술 스택 (개념 설명 포함)](#53-사용-기술-스택-개념-설명-포함)
   - 5.4 [프롬프트 설계 가이드](#54-프롬프트-설계-가이드)
   - 5.5 [가드레일 & 컴플라이언스](#55-가드레일--컴플라이언스)
   - 5.6 [평가·A/B 테스트·피드백 루프](#56-평가ab-테스트피드백-루프)
   - 5.7 [검색 키워드 가이드](#57-검색-키워드-가이드)
6. [**서비스계층 (Service Layer)**](#서비스계층-service-layer)
   - 6.1 [API 설계(초안)](#61-api-설계초안)
   - 6.2 [서버/인증/배포](#62-서버인증배포)
   - 6.3 [관측/로깅/알림](#63-관측로깅알림)
   - 6.4 [성능/안정성/운영 체크리스트](#64-성능안정성운영-체크리스트)
   - 6.5 [검색 키워드 가이드](#65-검색-키워드-가이드)
7. [변경 이력 & 다음 액션](#변경-이력--다음-액션)

---

## 문서 범위 & 배경
- 본 서비스는 “**하루 단위로 뜨는 유튜브 주제**를 포착하여 **쇼츠 아이디어**로 전환”하는 것을 목표로 합니다.
- 이전 버전(v0.2)에서는 **수집/분석**을 정의했고, 본 버전(v0.3)에서 **생성/서비스**를 신규로 추가합니다.
- 구현 세부 코드보다 **개념→의사결정 포인트→간단 예시** 중심. 실제 코드/ERD/수식은 대화에 따라 지속 보완합니다.

---

## 아키텍처 한눈에 보기
```
[YouTube API] → [수집(APScheduler)] → [스냅샷 DB]
                             ↘
                           [Google Trends]
                                    ↓
                    [분석(Pandas+NLP+Scikit-learn)]
                                    ↓
                [생성(GPT: 제목/태그/스크립트 템플릿)]
                                    ↓
                [서비스(FastAPI: REST, Auth, Rate Limit)]
                                    ↓
                       (선택) Notion/Slack/Web UI
```

---

## 수집계층 (Data Collection Layer) — 요약
> 자세한 버전은 v0.2 문서 참고. 본 문서에는 요약만 포함.

- **기능**: 유튜브 인기 급상승(국가별)·조회수 스냅샷·Google Trends 키워드 추세 수집
- **스택**: Python, APScheduler, httpx/requests, Pandas(경량 정제), SQLAlchemy + SQLite(PostgreSQL)
- **외부 API**: YouTube Data API v3, pytrends(interest_over_time/related_queries)
- **포인트**: UTC 시계열 스냅샷, 증분 갱신, 백오프/쿼터 관리

---

## 분석계층 (Data Processing & Analysis Layer) — 요약
> 자세한 버전은 v0.2 문서 참고. 본 문서에는 요약만 포함.

- **기능**: 정제 → 토큰화/불용어/N-gram → TF-IDF(+SVD) → KMeans 군집화 → 트렌드 점수화
- **스택**: Pandas, KoNLPy(MeCab/Okt), Scikit-learn(TfidfVectorizer, TruncatedSVD, KMeans/MiniBatchKMeans)
- **출력**: 클러스터 단위 “오늘의 주제 버킷” + 상위 키워드 + 보조 지표(조회수속도/검색량/댓글빈도)

---

## 생성계층 (Generation Layer)

### 5.1 기능 명세
- **목표**: 분석 결과(주제 버킷/상위 키워드/보조 지표)를 바탕으로 **제목/태그/스크립트 틀**을 자동 생성
- **산출물(권장)**
  - **제목 후보 N개**: 20–35자, 클릭 유도형(낚시성 과도 금지), 한글 우선
  - **태그 세트**: 해시태그 5–10개(핵심+롱테일 혼합, 금칙어 필터링)
  - **스크립트 3-Beat 템플릿**: Hook(0–3s) → Body(3–20s) → CTA(마무리)
  - **썸네일 카피**(선택): 8–12자, 고대비·간결
  - **BGM/길이 추천**(선택): Shorts 평균 15–30초, 트렌딩 사운드 후보
- **제약/정책**
  - 명예훼손·혐오·성적·의료·정치 민감 이슈 자동 차단(가드레일 룰셋/키워드 리스트)
  - 저작권/상표권 주의(브랜드명 언급 시 사실 기반/리뷰 맥락)

### 5.2 입출력 스키마(초안)
**입력 (analysis → generation)**
```json
{
  "topic_bucket_id": "T2025-09-28-001",
  "keywords": ["아이폰17", "루머", "가격", "스펙"],
  "signals": {
    "views_per_min": 1666.0,
    "trend_delta": 0.82,
    "comment_pulse": 0.54
  },
  "style": {
    "tone": "정보형/재미형 선택",
    "language": "ko",
    "length_sec": 20
  }
}
```

**출력 (generation → service)**
```json
{
  "titles": [
    "아이폰17 핵심 스펙 20초 컷🔥",
    "발표 전 루머 총정리, 이건 꼭 봐!"
  ],
  "tags": ["#아이폰17", "#애플", "#루머", "#스펙", "#테크"],
  "script_beats": {
    "hook": "카메라에 가장 큰 변화? 10초면 끝!",
    "body": "A15→A17, 가격 소폭↑, 배터리 용량/무게 변화 요약...",
    "cta": "더 빡센 비교 원하면 구독 알림!"
  },
  "thumbnail_copy": "스펙 진짜 바뀜?",
  "metadata": {
    "model": "gpt-4o-mini",
    "safety_flags": []
  }
}
```

### 5.3 사용 기술 스택 (개념 설명 포함)
- **OpenAI API (GPT)**  
  - 자연어 생성(NLG)에 특화. 프롬프트(지시문)로 스타일/길이/금칙어를 통제 가능.  
  - _검색_: “prompt engineering checklist”, “system prompt style guide”
- **Jinja2 (템플릿 엔진)**  
  - 프롬프트와 출력 포맷을 템플릿화. 모델/실험 버전에 따라 일괄 관리.  
  - _검색_: “jinja2 template best practices”
- **Pydantic (스키마 검증)**  
  - 모델 출력을 지정 스키마로 검증/정규화. 잘못된 필드/빈 값 방지.  
  - _검색_: “pydantic BaseModel validate json”, “pydantic strict types”
- **Redis (캐시/레이트 리밋)**  
  - 동일 입력 재생성 방지, 아이디어 재활용, API 속도/비용 절감.  
  - _검색_: “redis cache stampede”, “token bucket rate limit redis”
- **Rule Engine (간단 룰셋)**  
  - 금칙어·민감 주제·길이/문장부호 규칙 체크. 사후 필터 + 재생성 루프.  
  - _검색_: “content moderation keyword rules”, “post-generation validation”

### 5.4 프롬프트 설계 가이드
- **System**: 브랜드 톤/법적 제한/출력 스키마를 엄격히 정의
- **User**: 주제/키워드/보조 지표를 간결히 제공
- **Assistant (예시)**: “20–35자, 낚시성 금지, 숫자 1회 이하, 한글 우선, 이모지 최대 1” 등 **가드레일형 지시**
- **실험 변수**: `temperature/top_p`(창의성), `presence_penalty`(중복 회피), **템플릿 타입**(정보형/밈형/리액션형)
- **실패 복구**: 포맷 오류 시 재요청, 금칙어 감지 시 대체 프롬프트로 재생성

### 5.5 가드레일 & 컴플라이언스
- **민감 카테고리**: 건강·정치·선정·폭력·차별 표현 필터
- **사실 검증(경량)**: 수치·날짜·제품명은 분석계층 신뢰 점수와 교차 확인
- **저작권**: 음악·이미지 권리 고지, 상표·캐릭터 무단 사용 금지
- **PII**: 개인 신상정보/연락처 비노출, 댓글 인용 시 비식별화

### 5.6 평가·A/B 테스트·피드백 루프
- **오프라인 룰 기반 점수**: 제목 길이/가독성/금칙어/중복률 점수화
- **A/B 테스트**: 제목/태그 묶음 랜덤 분배 → 조회/CTR/시청완료율 비교
- **밴딧(선택)**: Epsilon-Greedy/UCB로 실시간 우승안 가중 강화
- **피드백 저장**: 선택/게시/성과 메타데이터를 **feature store**로 누적 → 차후 프롬프트/룰 자동 수정

### 5.7 검색 키워드 가이드
- “prompt engineering constraints title generation”  
- “content moderation rules youtube shorts”  
- “multi-armed bandit ab testing titles”  
- “redis rate limit token bucket python”

---

## 서비스계층 (Service Layer)

### 6.1 API 설계(초안)
**공통**: `Content-Type: application/json`, `Authorization: Bearer <API_KEY>`, 버저닝 `Accept: application/vnd.trendhelper.v1+json`

- `GET /health` → 상태 점검
- `GET /trending` → (분석계층 요약 제공) 현재 주제 버킷/상위 키워드
- `POST /ideas` → **생성계층 호출**(키워드/버킷 입력 → 제목/태그/스크립트 반환)
- `POST /ideas/batch` → 여러 버킷 일괄 생성
- `POST /analyze-video` → 단일 영상 키워드/점수/생성까지 원스톱(시간 절약용)
- `GET /stats` → 호출량/캐시 히트/최근 오류
- `POST /webhooks/notion` (선택) → Notion 기록용 페이로드 수신

**예시: POST /ideas**
```json
{
  "topic_bucket_id": "T2025-09-28-001",
  "keywords": ["아이폰17", "루머", "가격", "스펙"],
  "style": {"tone":"정보형","language":"ko","length_sec":20}
}
```
**응답**
```json
{
  "titles": ["아이폰17 핵심 스펙 20초 컷🔥", "발표 전 루머 총정리"],
  "tags": ["#아이폰17","#애플","#루머","#스펙","#테크"],
  "script_beats": {"hook":"카메라 변화 10초 정리!","body":"A17, 가격↑...","cta":"더 빡센 비교 원하면 구독!"},
  "metadata": {"model":"gpt-4o-mini","cache":"hit","safety_flags":[]}
}
```

### 6.2 서버/인증/배포
- **FastAPI + Uvicorn/Gunicorn**: 경량 REST 서버
- **Auth**: API Key(초기) → JWT/OAuth(확장)
- **Rate Limit**: SlowAPI/중간 프록시(nginx) + Redis 토큰버킷
- **배포**: Docker(멀티스테이지), 헬스체크, `.env`로 키 관리
- **버저닝**: 경로(`/v1`) 또는 헤더 버전 협상

### 6.3 관측/로깅/알림
- **구조화 로깅**: `trace_id`, `user_id`, `bucket_id`, `latency_ms`, `cache_hit`
- **메트릭**: Prometheus(요청 수/지연/오류율/모델비용), Grafana 대시보드
- **알림**: Slack/Email(오류율↑, OpenAI 실패율↑, 쿼터 임계치)

### 6.4 성능/안정성/운영 체크리스트
- **캐시 전략**: 동일 입력 해시 → TTL 캐시 → 비용/지연 최소화
- **재시도/폴백**: OpenAI 오류 시 대체 프롬프트/모델, 재시도 간격
- **Idempotency**: `Idempotency-Key` 헤더로 중복 요청 방지
- **타임아웃**: 상류(클라이언트)/중간(niginx)/하류(모델) 각각 명시
- **테스트**: Pydantic 스키마 테스트, 골든샘플 스냅샷 테스트, 계약(Contract) 테스트

### 6.5 검색 키워드 가이드
- “fastapi production settings gunicorn”  
- “api versioning best practices header vs path”  
- “idempotency key rest design”  
- “prometheus fastapi metrics middleware”  
- “nginx rate limiting token bucket”

---

## 변경 이력 & 다음 액션
- **v0.3**: 생성계층/서비스계층 신규 추가(입출력 스키마, 프롬프트/가드레일, API 초안, 운영 체크리스트)  
- **다음**: (1) Notion/Slack 연동 명세, (2) 프롬프트 템플릿 저장소 구조, (3) 모델 실험 로깅 스키마 설계, (4) 샘플 E2E 워크플로 제공

> 이 문서는 **지속적으로 보완**됩니다. 실제 운영·실험 결과를 근거로 프롬프트/룰/엔드포인트를 수시로 업데이트하세요.
