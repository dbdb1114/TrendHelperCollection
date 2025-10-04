# CLAUDE.md — Analysis (분석 계층, v1 Focus)

> **Purpose**  
> 이 문서는 **분석 계층(analysis)** 에서 Claude가 따라야 할 **계약(Contract) + 작업 절차(Playbook)** 을 정의합니다.  
> 데이터 과학/ML에 익숙하지 않은 개발자도 바로 실행할 수 있도록 **설명 + 명령 + 완료기준(DoD)** 을 명확히 적습니다.

---

## Versioning Policy
- **Current Target:** **v1**
- v1 범위를 벗어나는 기능/최적화는 **`TODO:V2`** 로만 기록하고, 지금은 구현하지 않습니다.
- 질문은 **최대 1회**까지만 하고, 합리적 가정으로 **즉시 구현**을 진행합니다.
- **코드 제안은 patch/diff** 형태로 제시합니다(파일 전체 재작성 금지).

---

## Responsibilities (이 모듈이 하는 일)
- `video_metrics_snapshot`을 기반으로 **조회수 증가 속도(velocity)** 를 계산합니다.
- 이상치 제거, 음수/무한대 제거, 클리핑을 통해 **정제된 상위 N개 결과**를 도출합니다.
- (v2) **키워드 추출**, **주제 버킷(topic buckets)** 까지 확장합니다.
- 분석 결과는 콘솔 출력 또는 임시 JSON 저장 방식으로 전달합니다.

---

## Contracts (v1)

### Input
- **Table:** `video_metrics_snapshot`
- **Relevant Columns:** `video_id`, `captured_at`, `view_count`

### Computation Logic
1. `video_id` 별로 `captured_at` 기준 정렬
2. `views_per_min = Δview_count / Δcaptured_minutes`
3. Δt ≤ 0(역순/중복), 음수 증가량, ∞ 값 제거
4. 상위 1% 이상치 **클리핑 처리**(최대값 하향)
5. **Top N 결과 추출** (기본 N=10)

### Output
- `List[Dict]` 형태의 JSON 예시:
```json
[
  {"video_id": "abc123", "views_per_min": 1234.5}
]
```

### DoD (Definition of Done)
- Δt=0, 음수, ∞ 등이 제거됩니다.
- 상위 10개가 정렬된 JSON으로 출력됩니다.
- 반복 실행해도 결과의 정합성이 보장됩니다.

---

## Commands (from repo root)

### 분석 실행
```bash
python analysis/jobs/analyzer_velocity.py --window 3 --top-n 10 --out-file /tmp/velocity_top10.json
```
- `--window`: 최근 몇 개 스냅샷 간 차이를 볼지 설정(기본 3)
- `--top-n`: 출력할 개수(기본 10)
- `--out-file`: 결과 저장 경로(미지정 시 stdout)

---

## Implementation Notes

### Velocity 계산 예시 (개념)
```python
# 개념 예시
df = snapshot_df.sort_values(["video_id", "captured_at"])
dt_min = df.groupby("video_id")["captured_at"].diff().dt.total_seconds() / 60
dv = df.groupby("video_id")["view_count"].diff()
df["views_per_min"] = dv / dt_min
```

### 이상치 제거 (Clipping)
- `views_per_min` 상위 1%를 `np.percentile(values, 99)` 값으로 클립합니다.

### 결측/에러 처리
- Δt ≤ 0, 음수 증가량, NaN, inf 등은 제거합니다.
- 필요 시 로그 경고 포함합니다.

---

## Files to Create (Claude에게 요청할 작업)

1) `analysis/jobs/analyzer_velocity.py`
   - DB에서 `video_metrics_snapshot` 로드
   - Δ계산 → velocity 계산 → 상위 N 출력
   - CLI 인자: `--window`, `--top-n`, `--out-file`
   - 로깅: JSON 라인(UTC, `trace_id`, `job="analyzer_velocity"`)

2) (v2 예정) `analysis/jobs/analyzer_keywords.py`
   - 제목/태그에서 불용어 제거 + 토큰화 → TF-IDF 계산
   - 결과 예: `video_id → [("아이폰", 0.83), ("루머", 0.65)]`

3) (v2 예정) `analysis/jobs/analyzer_topics.py`
   - TF-IDF → SVD → KMeans 클러스터링으로 주제 버킷 도출
   - 결과 예: `bucket_id → [video_id, ...]`

---

## DoD Checklist
- [ ] `video_metrics_snapshot` 기반 velocity 계산 수행
- [ ] Δt 역순/0/NaN/∞ 처리 완료
- [ ] `views_per_min` 정렬 후 상위 10개 출력
- [ ] 결과는 stdout 또는 JSON 파일에 저장
- [ ] 반복 실행 시 결과 일관성/재현성 확보

---

## Safety & Policy
- **시간:** 모든 분석 시각은 **UTC** 기준입니다.
- **에러 처리:** 분석 실패는 시스템 전체 실패로 간주하지 않고, 해당 항목만 스킵 후 로그로 남깁니다.
- **재현성:** 동일 입력 데이터 → 동일 결과를 보장합니다.

---

## TODO:V2 (미래 작업 메모)
- TF-IDF 기반 키워드 추출(`generation`과 연계)
- 주제 버킷(cluster) 모델 학습 및 캐싱
- PostgreSQL → pandas → Redis 캐시 파이프라인
- 시각화(간단한 대시보드) 추가
