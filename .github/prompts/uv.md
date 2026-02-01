---
agent: agent
---

# UV 기반 Python 실행 가이드

이 프로젝트는 **uv**를 패키지 관리자 및 Python 실행 도구로 사용합니다. 모든 Python 관련 작업은 uv를 통해 수행해야 합니다.

## 필수 규칙

### 1. Python 스크립트 실행

Python 파일을 실행할 때는 반드시 `uv run`을 사용하세요:

```bash
# ✅ 올바른 방법
uv run python script.py
uv run python main.py

# ❌ 잘못된 방법
python script.py
py script.py
```

### 2. 패키지 설치

패키지를 설치할 때는 `uv add`를 사용하세요:

```bash
# ✅ 올바른 방법
uv add requests
uv add pandas numpy

# ❌ 잘못된 방법
pip install requests
```

### 3. 개발 의존성 설치

개발용 패키지는 `--dev` 플래그를 사용하세요:

```bash
uv add --dev pytest black ruff
```

### 4. 의존성 동기화

프로젝트 의존성을 설치/동기화할 때:

```bash
uv sync
```

### 5. 가상환경

uv는 자동으로 `.venv` 가상환경을 생성하고 관리합니다. 별도의 가상환경 활성화가 필요 없습니다.

## 주의사항

- **절대로** `python` 또는 `pip` 명령어를 직접 사용하지 마세요
- 모든 Python 실행은 `uv run python ...` 형식을 사용하세요
- 패키지 관리는 `uv add`, `uv remove`, `uv sync`를 사용하세요
- `pyproject.toml`에 의존성이 자동으로 기록됩니다

## 예시 명령어

| 작업 | 명령어 |
|------|--------|
| 스크립트 실행 | `uv run python app.py` |
| 모듈 실행 | `uv run python -m pytest` |
| 패키지 추가 | `uv add fastapi` |
| 패키지 제거 | `uv remove fastapi` |
| 의존성 동기화 | `uv sync` |
| Python 버전 확인 | `uv run python --version` |