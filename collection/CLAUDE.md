# CLAUDE.md — Collection (수집, v1 Focus)

> **Purpose**  
> 이 문서는 **수집 계층(collection)**에서 Claude가 따라야 할 **계약(Contract) + 작업 절차(Playbook)** 를 정의합니다.  
> 처음 파이썬/데이터 파이프라인을 다루는 사람도 실행할 수 있도록 **설명 + 명령 + 완료기준(DoD)** 을 명확히 적습니다.

---

## Versioning Policy
- **Current Target:** **v1**
- v1 범위를 벗어나는 기능/최적화는 **`TODO:V2`** 로만 표시하고 지금은 구현하지 않는다.
- 질문은 **최대 1회**까지만 하고, 합리적 가정으로 **즉시 구현**을 진행한다.
- **코드 제안은 patch/diff** 형태로 제시(파일 전체 재작성 금지).

---

## Responsibilities (이 모듈이 하는 일)
- YouTube Data API v3로 **KR 인기급상승(mostPopular)** 상위 N개(기본 50) 영상을 수집한다.
- **메타데이터 upsert** → `videos` 테이블, **지표 스냅샷 insert** → `video_metrics_snapshot` 테이블.
- **재실행해도 중복/오염이 발생하지 않도록(idempotent)** 처리한다.
- (v2) **증분 스냅샷**(주기 실행), (옵션) Google Trends/댓글 수집.

---

## Contracts (v1)

### Data Sources
- **YouTube Data API v3**
  - 엔드포인트: `videos.list`
  - 필수 파라미터: `chart=mostPopular`, `regionCode=KR`, `maxResults=50`
  - `part`: `snippet,statistics` (v1은 이 2개면 충분)
  - 사용 필드 매핑:
    - `id` → `videos.video_id`
    - `snippet.title` → `videos.title`
    - `snippet.description` → `videos.description`
    - `snippet.publishedAt`(UTC) → `videos.published_at`
    - `snippet.tags[]` → `videos.tags`(JSONB, 없으면 `[]`)
    - `snippet.categoryId` → `videos.category`(임시로 문자열 보관)
    - `snippet.channelTitle` → `videos.channel`
    - `statistics.viewCount/likeCount/commentCount` → `video_metrics_snapshot.*`
  - **쿼터/리밋**: 429/5xx 발생 시 **지수 백오프+Jitter**, 요청 당 타임아웃 10s

### Database (PostgreSQL) — v1 범위
- **`videos` (upsert)**
  - `video_id TEXT PK`
  - `title TEXT`, `description TEXT`, `channel TEXT`, `category TEXT`, `tags JSONB`, `country_code TEXT`
  - `published_at TIMESTAMPTZ`
- **`video_metrics_snapshot` (insert)**
  - `id BIGSERIAL PK`
  - `video_id TEXT FK → videos.video_id`
  - `captured_at TIMESTAMPTZ` *(수집 시각, UTC; 분 단위로 반올림 권장)*
  - `view_count BIGINT`, `like_count BIGINT`, `comment_count BIGINT`
  - **Index:** `(video_id, captured_at)` (중복 방지/정렬)
- **Idempotency 규칙**
  - `videos`: `video_id` 기준 **UPSERT** (제목/설명/태그/카테고리/채널/국가코드 갱신)
  - `video_metrics_snapshot`: `(video_id, captured_at_minute)` **유니크** 보장(분 단위 라운딩)

> 스키마는 **루트 CLAUDE.md의 DB 계약**을 준수한다. 새로운 컬럼/테이블은 지금은 `TODO:V2`.

---

## Commands (from repo root)

### 1) 트렌딩 1회 수집 (v1 핵심)
```bash
python collection/jobs/collector_trending.py --country KR --limit 50
```
- 동작: YouTube에서 상위 N(기본 50) 조회 → `videos` upsert + `video_metrics_snapshot` insert
- 로그: `job=collector_trending country=KR fetched=50 upserts=... snapshots=...`

### 2) 증분 스냅샷 (v2에서 활성화)
```bash
python collection/jobs/collector_incremental.py --last-hours 6
```
- 동작: 최근 N시간 내 트렌딩에 등장한 video_id를 다시 조회 → snapshot 추가
- 로그: `job=collector_incremental last_hours=6 refreshed=... snapshots=...`

### 3) (옵션) Google Trends (v2)
```bash
python collection/jobs/collector_trends.py --keywords "아이폰17,루머"
```
- `keywords_trend` 테이블은 v2에서 설계/도입

---

## Implementation Notes (요령)

### HTTP 클라이언트
- **httpx** 사용, 타임아웃 10s, 커넥션 풀 기본.
- 429/5xx: **지수 백오프 + Jitter(±20%)**, 최대 5회 재시도.
- 장애 시 로그에 `attempt`, `sleep_ms`, `status` 포함.

### 시간/타임존
- 모든 시각은 **UTC**. Python에서는 `datetime.now(timezone.utc)` 사용.
- `captured_at`는 **분 단위로 내림/반올림**(중복 스냅샷 방지).

### 로깅(JSON line)
- 공통 필드: `ts`, `level`, `logger`, `msg`
- 수집 전용 확장: `job`, `request_id`, `country`, `limit`, `http_status`, `retry_count`, `quota_cost`, `upserts`, `snapshots`
- 예시:  
  `{"ts":"...Z","level":"INFO","logger":"collector","job":"collector_trending","country":"KR","fetched":50,"upserts":50,"snapshots":50}`

### 예외 처리
- 네트워크 예외/Timeout/HTTP 오류는 **잡 실패로 올리지 말고** 재시도 후 **부분 성공**도 인정.
- 실패한 항목은 **스킵**하고 `errors` 카운트로 집계, 로그에 남김.

### 성능/쿼터
- 기본 limit=50, **QPS를 1~2 정도로 제한** (필요 시 지수 백오프와 함께).
- v1은 단일 스레드로 충분. 병렬은 `TODO:V2`.

---

## Files to Create (Claude에게 요청할 작업)

1) `collection/clients/youtube.py`
   - `YoutubeClient` 클래스: `fetch_trending(country: str, limit: int) -> list[dict]`
   - 내부: httpx 클라이언트, 키는 `.env`(`YOUTUBE_API_KEY`), 파라미터/필드 매핑 처리
   - 예외/재시도/백오프 내장

2) `collection/jobs/collector_trending.py`
   - `main(country="KR", limit=50)`
   - 흐름: fetch → normalize → upsert(`videos`) → insert snapshot(`video_metrics_snapshot`)
   - `argparse`로 커맨드 인자 처리

3) (v2) `collection/jobs/collector_incremental.py`
   - 최근 등장 영상 재조회 → snapshot insert

---

## DoD (Definition of Done)

- [ ] **KR 트렌딩 50** 수집이 **한 번에 성공**한다.
- [ ] `videos`에 **중복 없이** upsert (video_id PK 기반).
- [ ] `video_metrics_snapshot`에 **스냅샷이 누적**되고, `(video_id,captured_at)` 인덱스로 **중복 방지**된다.
- [ ] 재실행해도 결과가 **변하지 않거나(동일 시각)**, 최신 필드만 안전하게 갱신된다.
- [ ] JSON 로깅에 `job, country, fetched, upserts, snapshots, errors`가 포함된다.

---

## Testing (수동)

1) **드라이런**: `--dry-run` 옵션을 지원해 DB에 쓰지 않고 콘솔에 upsert/snapshot 예정 건수만 출력.
2) **경계값**: limit=5로 실행해 샘플 확인.
3) **재실행**: 같은 명령을 연속 2회 실행 → 레코드 카운트가 증가하지 않음(스냅샷 분 라운딩 기준).
4) **오류 유발**: 잘못된 키로 실행해 403/401 처리/로깅 확인.

---

## Safety & Policy

- **저작권**: v1에서는 원본 영상/썸네일 **다운로드/재업로드 금지** (메타/지표만 저장)
- **개인정보**: PII 저장 금지
- **키 관리**: `.env`만 사용, PR/로그에 키 노출 금지

---

## Patch/Diff 규칙 (중요)

- 전체 파일 재작성 금지. **Unified Diff**로 변경점을 제시한다.
- 새 파일 생성 시에도 **경로/파일명/내용**을 명시하고 patch 형태를 우선한다.

---

## TODO:V2 (미래 작업 메모)

- APScheduler 등록(30–60분), 증분 수집
- Google Trends: `keywords_trend` 테이블 설계(`keyword`, `score`, `captured_at`, `raw_payload`)
- 댓글 스냅샷(정책 검토 후 최소 필드)
- 병렬/배치 처리, API 비용 모니터링
