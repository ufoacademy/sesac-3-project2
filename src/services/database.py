import json
import sqlite3
from contextlib import closing
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS applicants (
    applicant_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    extracted_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_answers (
    analysis_id INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    answer_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    applicant_id TEXT NOT NULL,
    overall_fit REAL,
    coverage REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dimension_results (
    analysis_id INTEGER NOT NULL,
    dimension_id TEXT NOT NULL,
    company_score REAL NOT NULL,
    candidate_score REAL,
    fit_score REAL,
    confidence REAL NOT NULL,
    evidence_quote TEXT
);
"""


def _connect(
    db_path: Path,
) -> sqlite3.Connection:
    """SQLite에 연결하고 필요한 테이블을 생성한다."""

    db_path = Path(db_path)
    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(db_path)
    connection.executescript(SCHEMA)

    return connection


def save_analysis(
    db_path: Path,
    payload: dict,
) -> int:
    """분석 결과를 저장하고 새 분석 번호를 반환한다."""

    with closing(_connect(db_path)) as connection, connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO applicants (
                applicant_id,
                source_file,
                source_hash,
                extracted_text
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                payload["applicant_id"],
                payload["source_file"],
                payload["source_hash"],
                payload["extracted_text"],
            ),
        )

        cursor = connection.execute(
            """
            INSERT INTO analysis_runs (
                company_id,
                applicant_id,
                overall_fit,
                coverage,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload["company_id"],
                payload["applicant_id"],
                payload["overall_fit"],
                payload["coverage"],
                json.dumps(
                    payload,
                    ensure_ascii=False,
                ),
            ),
        )

        analysis_id = int(cursor.lastrowid)

        for question_id, answer_text in (
            payload["scenario_answers"].items()
        ):
            connection.execute(
                """
                INSERT INTO scenario_answers (
                    analysis_id,
                    question_id,
                    answer_text
                )
                VALUES (?, ?, ?)
                """,
                (
                    analysis_id,
                    question_id,
                    answer_text,
                ),
            )

        for dimension_id, detail in (
            payload["dimensions"].items()
        ):
            connection.execute(
                """
                INSERT INTO dimension_results (
                    analysis_id,
                    dimension_id,
                    company_score,
                    candidate_score,
                    fit_score,
                    confidence,
                    evidence_quote
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    dimension_id,
                    detail["company_score"],
                    detail["candidate_score"],
                    detail["fit_score"],
                    detail["confidence"],
                    detail["evidence_quote"],
                ),
            )

        return analysis_id


def load_analysis(
    db_path: Path,
    analysis_id: int,
) -> dict:
    """분석 번호로 저장된 분석 결과를 불러온다."""

    with closing(_connect(db_path)) as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM analysis_runs
            WHERE analysis_id = ?
            """,
            (analysis_id,),
        ).fetchone()

    if row is None:
        raise KeyError(
            f"분석 결과를 찾을 수 없습니다: {analysis_id}"
        )

    return json.loads(row[0])


def list_analyses(
    db_path: Path,
) -> list[dict]:
    """저장된 분석 결과를 최근 순서로 불러온다."""

    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT analysis_id, payload_json
            FROM analysis_runs
            ORDER BY analysis_id DESC
            """
        ).fetchall()

    results = []

    for analysis_id, payload_json in rows:
        payload = json.loads(payload_json)
        payload["analysis_id"] = analysis_id
        results.append(payload)

    return results

def _normalize_answers_for_cache(
    answers: dict[str, str],
) -> dict[str, str]:
    """답변의 줄바꿈과 연속 공백을 정리한다."""

    return {
        question_id: " ".join(
            str(answer).split()
        )
        for question_id, answer in sorted(
            answers.items()
        )
    }


def load_cached_candidate_profile(
    db_path: Path,
    source_hash: str,
    scenario_answers: dict[str, str],
    analysis_version: str | None = None,
) -> dict | None:
    """같은 PDF와 답변으로 분석한 지원자 프로필을 찾는다."""

    db_path = Path(db_path)

    if not db_path.exists():
        return None

    normalized_answers = (
        _normalize_answers_for_cache(
            scenario_answers
        )
    )

    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT payload_json
            FROM analysis_runs
            ORDER BY analysis_id DESC
            """
        ).fetchall()

    for row in rows:
        payload = json.loads(
            row[0]
        )

        if (
            analysis_version is not None
            and payload.get("candidate_analysis_version") != analysis_version
        ):
            continue

        if payload.get(
            "source_hash"
        ) != source_hash:
            continue
        
        saved_answers = (
            _normalize_answers_for_cache(
                payload.get(
                    "scenario_answers",
                    {},
                )
            )
        )

        if saved_answers != normalized_answers:
            continue

        dimensions = []

        for dimension_id, detail in (
            payload.get(
                "dimensions",
                {},
            ).items()
        ):
            candidate_score = detail.get(
                "candidate_score"
            )

            status = detail.get(
                "status",
                (
                    "observed"
                    if candidate_score is not None
                    else "missing"
                ),
            )

            evidence_source = detail.get(
                "evidence_source"
            )

            if evidence_source is None:
                evidence_source = (
                    "missing"
                    if status == "missing"
                    else "application"
                )

            dimensions.append(
                {
                    "dimension_id": dimension_id,
                    "score": candidate_score,
                    "confidence": detail.get(
                        "confidence",
                        0.0,
                    ),
                    "evidence_quote": detail.get(
                        "evidence_quote"
                    ),
                    "evidence_source": (
                        evidence_source
                    ),
                    "reasoning": detail.get(
                        "reasoning",
                        "저장된 분석 결과를 재사용했습니다.",
                    ),
                    "status": status,
                    "follow_up_question": detail.get(
                        "follow_up_question",
                        "면접에서 해당 성향을 확인하세요.",
                    ),
                }
            )

        if len(dimensions) != 6:
            continue

        return {
            "summary": payload.get(
                "candidate_summary",
                "저장된 지원자 성향 분석",
            ),
            "dimensions": dimensions,
        }

    return None