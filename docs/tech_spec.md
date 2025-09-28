# YouTube Trend Shorts Helper — 기술 문서

> **버전**: v0.2 (Living Doc)  
> **범위**: 본 문서는 _수집계층_과 _분석계층_의 기술 명세 및 개념 설명을 다룹니다. 차후 _생성계층_과 _서비스계층_을 동일 형식으로 확장합니다.  
> **목적**: 웹개발자/비전공자도 이해할 수 있도록 개념 위주로 설명하여, Google/Reddit/Threads 등에서 추가 학습과 질문이 가능하도록 돕습니다.

---

## 목차
1. [문서 범위 & 배경](#문서-범위--배경)
2. [아키텍처 한눈에 보기](#아키텍처-한눈에-보기)
3. [수집계층 (Data Collection Layer)](#수집계층-data-collection-layer)
   - 3.1 [기능 명세](#31-기능-명세)
   - 3.2 [데이터 플로우](#32-데이터-플로우)
   - 3.3 [사용 기술 스택 (개념 설명 포함)](#33-사용-기술-스택-개념-설명-포함)
     - Python 3.11+
     - APScheduler
     - requests / httpx
     - Pandas (경량 정제)
     - SQLAlchemy + SQLite(PostgreSQL)
   - 3.4 [외부 API 연계 목록](#34-외부-api-연계-목록)
   - 3.5 [데이터 모델 (MVP)](#35-데이터-모델-mvp)
   - 3.6 [스케줄링 & 쿼터 전략](#36-스케줄링--쿼터-전략)
   - 3.7 [운영 고려사항](#37-운영-고려사항)
   - 3.8 [검색 키워드 가이드(What to Google/Reddit)](#38-검색-키워드-가이드what-to-googlereddit)
4. [분석계층 (Data Processing & Analysis Layer)](#분석계층-data-processing--analysis-layer)
   - 4.1 [기능 명세](#41-기능-명세)
   - 4.2 [사용 기술 스택 (개념 설명 포함)](#42-사용-기술-스택-개념-설명-포함)
     - Pandas
     - NLP (MeCab/Okt, 정규식, 불용어, N-gram, 동의어 통합)
     - Scikit-learn (TF-IDF, SVD, KMeans/MiniBatchKMeans)
   - 4.3 [핵심 알고리즘 & 지표](#43-핵심-알고리즘--지표)
   - 4.4 [데이터 품질 체크리스트](#44-데이터-품질-체크리스트)
   - 4.5 [성능 & 확장성 팁](#45-성능--확장성-팁)
   - 4.6 [검색 키워드 가이드(What to Google/Reddit)](#46-검색-키워드-가이드what-to-googlereddit)
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
- **문서 범위**: “하루하루 뜨는 주제를 포착해 쇼츠 아이디어로 전환”하기 위해, 데이터를 _어떻게 수집_하고 _어떻게 분석_할지에 대한 **MVP 수준의 기술 명세 + 개념 설명**을 제공합니다.
- **독자**: 웹개발자(비전공자 포함), 데이터 처리에 익숙하지 않아도 이해 가능하도록 구성.
- **스타일**: 구현 세부 코드보다 **개념→의사결정 포인트→간단 예시** 중심. (필요 시 코드/ERD/수식은 순차적으로 보강)

---

## 아키텍처 한눈에 보기
```
[YouTube API] → [수집 스케줄러/APScheduler] → [원시 스냅샷 저장(DB)]
                                       ↘
                                     [Google Trends(pytrends)]
                                              ↓
                              [정제/전처리(Pandas & NLP)]
                                              ↓
                    [특징 벡터화/군집화(Scikit-learn: TF-IDF, SVD, KMeans)]
                                              ↓
                                [트렌드 점수화 & 주제 버킷 산출]
                                              ↓
                         (차후) [생성계층: 제목/태그/GPT] → [서비스계층: API/UI]
```

---

## 수집계층 (Data Collection Layer)

### 3.1 기능 명세
- **유튜브 인기 급상승(국가별) 수집**: `id, 제목, 설명, 태그, 채널, 업로드 시각, 조회수, 좋아요, 댓글 수` 등 메타데이터 저장
- **조회수 변화 추적**: 동일 `video_id`의 시계열 스냅샷을 쌓고 `Δ조회수/Δ시간`(분/시간 단위) 계산에 활용
- **검색 트렌드 확보**: Google Trends로 동일/연관 키워드의 검색량 추이 수집 → 수요 검증
- **확장 신호(선택)**: 댓글(감성/밈 포인트), SNS(트위터/X, 틱톡) 언급량

### 3.2 데이터 플로우
1. APScheduler가 주기적으로 수집 Job 실행(기본 30~60분)
2. YouTube Data API → 인기 급상승 목록/세부 메트릭 호출
3. (선택) commentThreads로 댓글 스냅샷
4. pytrends로 키워드 검색량 추세/연관어 수집
5. DB에 “스냅샷” 형태로 적재(원본 보존 → 추후 diff/리플레이 가능)

### 3.3 사용 기술 스택 (개념 설명 포함)

#### ▷ Python 3.11+
- **왜 필요한가**: 데이터 처리/스크립팅에 특화된 표준 언어. 생태계가 풍부해서 빠르게 프로토타이핑 가능.
- **알아둘 개념**: 가상환경(venv/conda), 타입힌트, 패키지 관리(pip/uv), 로깅(logging).
- **검색 가이드**: `python virtualenv best practices`, `python logging structured`

#### ▷ APScheduler
- **역할**: “정해진 주기”로 작업 실행(크론/인터벌). Python 내부에서 스케줄러를 운영할 수 있음.
- **사용 포인트**: `BackgroundScheduler`로 앱과 함께 구동, Job별 크론표현식, 실패 재시도/예외 처리.
- **주의**: 프로세스 재시작 시 스케줄 상태 초기화 → 운영 단계에선 외부 스케줄러/작업큐 병행 고려.
- **검색 가이드**: `APScheduler cron example`, `APScheduler jobstore persistence`

#### ▷ requests / httpx
- **역할**: 외부 REST API 호출. httpx는 비동기/타임아웃/재시도 어댑터가 편리.
- **사용 포인트**: 공용 `Client(Session)`로 커넥션 풀 재사용, Backoff(429/5xx) 처리.
- **주의**: 과도한 동시 호출로 쿼터 초과 방지, 타임아웃/에러 핸들링 꼼꼼히.
- **검색 가이드**: `httpx retries timeout`, `requests session pool`

#### ▷ Pandas (경량 정제)
- **역할**: API 응답을 표 형태로 변환해 타입 정리, 중복 제거, 타임존 통일 등 **경량 클리닝**.
- **사용 포인트**: `to_datetime`, `drop_duplicates`, `astype`로 dtypes 맞추기.
- **주의**: 수집 단계는 “가벼운” 정제만 — 무거운 분석은 분석계층으로 위임.
- **검색 가이드**: `pandas to_datetime timezone`, `pandas drop_duplicates subset`

#### ▷ SQLAlchemy + SQLite(PostgreSQL)
- **역할**: ORM으로 테이블 스키마/CRUD를 코드로 관리. MVP는 SQLite(무설치·간편), 확장 시 PostgreSQL 권장.
- **사용 포인트**: 세션 관리, 인덱스 설계(video_id, captured_at), JSON 컬럼(tags/related_queries).
- **주의**: SQLite는 동시쓰기·락 이슈, 운영 전환시 마이그레이션 계획.
- **검색 가이드**: `SQLAlchemy ORM tutorial`, `SQLite concurrency`, `PostgreSQL JSONB index`

### 3.4 외부 API 연계 목록
- **YouTube Data API v3**
  - `videos.list (chart=mostPopular)` — 국가별 인기 급상승
  - `videos.list (id=...)` — 개별 메트릭 갱신(조회수/좋아요/댓글수)
  - `commentThreads.list (videoId=...)` — 댓글 수집(선택)
  - _검색_: `YouTube Data API quota cost`, `chart=mostPopular parameters`
- **Google Trends (pytrends)**
  - `interest_over_time()` — 검색량 시계열
  - `related_queries()` — 연관 검색어 Top/Rising
  - _검색_: `pytrends interest_over_time`, `pytrends related_queries`
- **(선택) SNS API**
  - Twitter/X, TikTok: 키워드 언급량/해시태그 트렌드

### 3.5 데이터 모델 (MVP)
- **videos**
  - `video_id (PK)`, `title`, `description`, `channel`, `published_at(UTC)`, `category`, `tags(JSON)`, `country_code`
- **video_metrics_snapshot**
  - `id (PK)`, `video_id (FK)`, `captured_at(UTC)`, `view_count`, `like_count`, `comment_count`
- **keywords_trend**
  - `id (PK)`, `keyword`, `source (youtube|google_trends|sns)`, `captured_at`, `score/raw_payload(JSON)`

> **포인트**: _스냅샷_ 테이블을 유지하면, “그때 그 시각”의 상태를 **재현**할 수 있어 시계열 분석·A/B 비교가 쉬워집니다.

### 3.6 스케줄링 & 쿼터 전략
- **주기**: 30~60분 간격이면 “실시간 느낌” 유지 + API 쿼터 부담 낮음
- **쿼터**: `chart=mostPopular` 1호출=1unit(50개), 국가 수 늘릴 때만 주의
- **증분 갱신**: 동일 `video_id`만 메트릭 재조회 → 비용 절약
- **캐싱/백오프**: 동일 데이터 반복 호출 방지, 429/5xx 시 지수 백오프

### 3.7 운영 고려사항
- **타임존 통일(UTC)**, 문자열 → 날짜형 변환 철저
- **API 장애/속도저하 대비**: 재시도·스킵·알림
- **비식별 저장**: 댓글 수집 시 개인정보 노출에 유의(정책/약관 준수)
- **관측 가능성**: 로깅/메트릭 대시보드(추가 예정)

### 3.8 검색 키워드 가이드(What to Google/Reddit)
- “APScheduler vs cron reliability”
- “YouTube Data API mostPopular best practices”
- “Handling API rate limits backoff python httpx”
- “Data snapshot pattern analytics warehouse”

---

## 분석계층 (Data Processing & Analysis Layer)

### 4.1 기능 명세
- **데이터 정제**: 특수문자/URL/이모지 제거, 대소문자/공백/타임존 정규화
- **조회수 상승 속도 계산**: 스냅샷 간 `diff`로 증가량 → 분/시간 단위 속도화
- **키워드 추출(NLP)**: 형태소 분석(명사/고유명사 중심), 불용어 제거, N-gram 구성, 동의어/표기 통합
- **주제 군집화 & 트렌드 점수화**: TF-IDF → (선택)SVD → KMeans로 “오늘의 주제 버킷” 생성, 조회수/검색량/댓글 지표 가중합으로 순위화
- **생성계층 준비**: 상위 키워드·감성 포인트를 생성 모델(GPT) 입력 형식으로 정리

### 4.2 사용 기술 스택 (개념 설명 포함)

#### ▶ Pandas
- **개념**: “엑셀 고급판” 테이블 라이브러리. 시계열 계산, groupby 집계, join/merge에 강함.
- **우리의 사용 포인트**: `diff()`로 증가량 계산, `groupby(video_id)`로 분당/시간당 속도, `merge()`로 Trends/댓글 지표 결합.
- **찾아볼 키워드**: “pandas groupby diff time series”, “pandas merge join performance”

#### ▶ NLP (MeCab/Okt, 정규식, 불용어, N-gram, 동의어 통합)
- **개념**: 문장을 기계가 다룰 수 있게 “단어/어근” 단위로 나눠 의미 있는 토큰만 남기는 작업.
- **우리의 사용 포인트**:
  - MeCab(정확/빠름) 또는 Okt(설치 간편)로 한글 토큰화
  - 불용어(예: ‘영상, 구독, 오늘’) 제거, `("아이폰","17")` → “아이폰17” 식 표기 통합
  - 해시태그는 별도 추출 후 본문 토큰과 합침
- **찾아볼 키워드**: “mecab-ko install”, “open-korean-text tokenizer”, “Korean stopwords list”, “ngram collocation”

#### ▶ Scikit-learn (TF-IDF, SVD, KMeans/MiniBatchKMeans)
- **개념**: 텍스트를 벡터(숫자열)로 바꾸고 비슷한 것끼리 묶는(군집화) 머신러닝 툴킷.
- **우리의 사용 포인트**:
  - `TfidfVectorizer(tokenizer=...)`로 희소행렬 생성(1~2gram)
  - 대용량 시 `TruncatedSVD`로 차원 축소 후 `KMeans`/`MiniBatchKMeans`
  - 각 군집의 상위 TF-IDF 단어로 “군집=주제” 해석
- **찾아볼 키워드**: “TF-IDF tutorial sklearn”, “KMeans vs MiniBatchKMeans text”, “TruncatedSVD LSA text”

### 4.3 핵심 알고리즘 & 지표
- **조회수 상승 속도**  
  `views_per_min = (view_t - view_{t-1}) / minutes_diff`
- **트렌드 점수(예시)**  
  `score = 0.5*z(views_per_min) + 0.3*z(google_trend_delta) + 0.2*z(comment_freq)`  
  ※ `z(·)`: 표준화(평균0, 표준편차1)
- **주제 군집화**: TF-IDF → (선택)SVD → KMeans, 군집별 Top-n 키워드 도출

### 4.4 데이터 품질 체크리스트
- 타임존이 혼재되지 않았는가(반드시 UTC)?
- 분모(시간차)가 0 또는 너무 작지 않은가(무한대/폭주 값 방지)?
- 토큰화 후 한 글자/숫자만 남는 토큰을 과도 생성하지 않는가?
- 클러스터 라벨이 불안정하지 않은가(랜덤시드 고정)?
- 상위 키워드가 사람 기준으로도 “주제”로 해석 가능한가?

### 4.5 성능 & 확장성 팁
- Pandas: `category` dtype, Parquet 파일, 벡터화 연산, 불필요한 컬럼 드랍
- Scikit-learn: `max_features` 제한, `MiniBatchKMeans`, 파이프라인/모델 `joblib` 저장
- NLP: 사용자 사전(도메인 신조어) 운영, 해시태그/이모지 별도 처리

### 4.6 검색 키워드 가이드(What to Google/Reddit)
- “pandas time series diff pitfalls”
- “Korean NLP tokenizer comparison mecab okt”
- “sklearn TF-IDF ngram text clustering best practices”
- “topic labeling from kmeans tfidf top terms”
- “standardization z-score why and when”

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
