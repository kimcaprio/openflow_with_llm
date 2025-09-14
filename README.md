# 🚀 LLM 기반 Apache NiFi 데이터플로우 자동 생성 시스템

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Apache NiFi](https://img.shields.io/badge/Apache%20NiFi-1.20+-orange.svg)](https://nifi.apache.org/)

자연어 요구사항을 Apache NiFi 데이터플로우로 자동 변환하는 지능형 시스템입니다.

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [시스템 아키텍처](#시스템-아키텍처)
- [설치 및 설정](#설치-및-설정)
- [사용법](#사용법)
- [API 문서](#api-문서)
- [개발 가이드](#개발-가이드)
- [기여하기](#기여하기)
- [라이선스](#라이선스)

## 🎯 개요

이 시스템은 Large Language Model(LLM)을 활용하여 사용자의 자연어 요구사항을 분석하고, 최적화된 Apache NiFi 데이터플로우를 자동으로 생성합니다. 복잡한 데이터 파이프라인 구축을 단순화하고, 개발 생산성을 크게 향상시킵니다.

### ✨ 핵심 가치

- **🤖 지능형 자동화**: LLM 기반 자연어 처리로 직관적인 플로우 생성
- **⚡ 빠른 개발**: 수동 구성 대비 90% 시간 단축
- **🔧 최적화**: AI 기반 성능 최적화 및 베스트 프랙티스 적용
- **🔄 재사용성**: 템플릿 기반 플로우 재사용 및 공유

## 🚀 주요 기능

### 1. 자연어 기반 플로우 생성
```
"CSV 파일을 읽어서 JSON으로 변환하고 Kafka에 전송해줘"
↓
자동으로 GetFile → ConvertRecord → PublishKafka 플로우 생성
```

### 2. 지능형 최적화
- 성능 병목 지점 자동 감지
- 리소스 사용량 최적화
- 에러 처리 로직 자동 생성

### 3. 다양한 LLM 모델 지원
- OpenAI GPT-4/3.5-turbo
- Anthropic Claude
- Google Gemini
- Local Ollama 모델

### 4. 웹 기반 사용자 인터페이스
- 직관적인 플로우 생성 인터페이스
- 실시간 플로우 모니터링
- 템플릿 관리 및 공유

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   REST API      │    │   LLM Service   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (OpenAI/etc)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Template      │    │   Core Engine   │    │   NiFi API      │
│   Manager       │◄──►│   (Python)      │◄──►│   (REST)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   (PostgreSQL)  │
                       └─────────────────┘
```

## 📦 설치 및 설정

### 사전 요구사항

- Python 3.8 이상
- Apache NiFi 1.20 이상
- PostgreSQL 12 이상
- Node.js 16 이상 (웹 UI 개발 시)

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/Openflow_with_LLM.git
cd Openflow_with_LLM
```

### 2. Python 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp config/.env.example config/.env
# .env 파일을 편집하여 필요한 설정 입력
```

### 4. 데이터베이스 설정

```bash
# PostgreSQL 데이터베이스 생성
createdb openflow_llm

# 스키마 초기화
python scripts/init_db.py
```

### 5. NiFi 연결 설정

```bash
# NiFi 설정 파일 편집
vim config/nifi_config.yaml
```

## 🎮 사용법

### 1. 서버 시작

```bash
# API 서버 시작
python -m src.api.main

# 웹 UI 시작 (개발 모드)
cd frontend
npm start
```

### 2. 기본 사용 예제

#### CLI를 통한 플로우 생성

```bash
python -m src.cli.main create-flow \
  --description "MySQL에서 데이터를 읽어 Elasticsearch에 저장" \
  --source mysql \
  --target elasticsearch
```

#### Python API 사용

```python
from src.core.flow_generator import FlowGenerator

generator = FlowGenerator()
flow = generator.create_flow(
    description="로그 파일을 읽어서 에러만 필터링하고 알림 전송",
    requirements={
        "source": "log_files",
        "filter": "error_level",
        "target": "notification_system"
    }
)
```

#### REST API 사용

```bash
curl -X POST "http://localhost:8000/api/v1/flows" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "CSV 파일을 JSON으로 변환하여 Kafka에 전송",
    "requirements": {
      "input_format": "csv",
      "output_format": "json",
      "target": "kafka"
    }
  }'
```

### 3. 웹 UI 사용

1. 브라우저에서 `http://localhost:3000` 접속
2. 자연어로 요구사항 입력
3. 생성된 플로우 확인 및 수정
4. NiFi에 배포

## 📚 API 문서

### 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/v1/flows` | 새 플로우 생성 |
| GET | `/api/v1/flows` | 플로우 목록 조회 |
| GET | `/api/v1/flows/{id}` | 특정 플로우 조회 |
| PUT | `/api/v1/flows/{id}` | 플로우 수정 |
| DELETE | `/api/v1/flows/{id}` | 플로우 삭제 |
| POST | `/api/v1/flows/{id}/deploy` | NiFi에 플로우 배포 |

### 상세 API 문서

서버 실행 후 `http://localhost:8000/docs`에서 Swagger UI를 통해 상세한 API 문서를 확인할 수 있습니다.

## 🛠️ 개발 가이드

### 프로젝트 구조

```
src/
├── core/               # 핵심 비즈니스 로직
│   ├── flow_generator.py
│   ├── optimizer.py
│   └── validator.py
├── llm/               # LLM 통합 모듈
│   ├── providers/
│   ├── prompts/
│   └── response_parser.py
├── nifi/              # NiFi 연동 모듈
│   ├── api_client.py
│   ├── processor_factory.py
│   └── template_manager.py
├── api/               # REST API
│   ├── main.py
│   ├── routes/
│   └── middleware/
└── utils/             # 공통 유틸리티
    ├── config.py
    ├── logger.py
    └── validators.py
```

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt

# 코드 포매팅
black src/
isort src/

# 린팅
flake8 src/
mypy src/

# 테스트 실행
pytest tests/
```

### 새로운 LLM 프로바이더 추가

1. `src/llm/providers/` 디렉토리에 새 프로바이더 클래스 생성
2. `BaseLLMProvider` 인터페이스 구현
3. `src/llm/factory.py`에 프로바이더 등록
4. 설정 파일에 프로바이더 설정 추가

### 새로운 NiFi 프로세서 지원 추가

1. `src/nifi/processors/` 디렉토리에 프로세서 클래스 생성
2. `BaseProcessor` 클래스 상속
3. 프로세서 메타데이터 및 설정 정의
4. 테스트 케이스 작성

## 🧪 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 모듈 테스트
pytest tests/test_flow_generator.py

# 커버리지 포함 테스트
pytest --cov=src tests/
```

### 테스트 카테고리

- **Unit Tests**: 개별 함수/클래스 테스트
- **Integration Tests**: 모듈 간 통합 테스트
- **E2E Tests**: 전체 시스템 테스트
- **Performance Tests**: 성능 및 부하 테스트

## 📊 모니터링 및 로깅

### 로그 설정

```python
# config/logging.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    formatter: default
  file:
    class: logging.FileHandler
    filename: logs/app.log
    formatter: default
```

### 메트릭 수집

- Prometheus를 통한 메트릭 수집
- Grafana 대시보드를 통한 시각화
- 주요 메트릭: 응답시간, 처리량, 에러율, 리소스 사용량

## 🤝 기여하기

### 기여 방법

1. 이슈 생성 또는 기존 이슈 선택
2. 브랜치 생성: `git checkout -b feature/your-feature`
3. 변경사항 커밋: `git commit -m 'Add some feature'`
4. 브랜치 푸시: `git push origin feature/your-feature`
5. Pull Request 생성

### 코드 리뷰 가이드라인

- 코드 스타일 가이드 준수
- 테스트 케이스 포함
- 문서 업데이트
- 성능 영향 고려

## 📝 변경 이력

### v1.0.0 (예정)
- 기본 플로우 생성 기능
- OpenAI GPT 모델 지원
- 웹 UI 베타 버전

### v0.2.0 (개발 중)
- 다중 LLM 모델 지원
- 플로우 최적화 기능
- 템플릿 관리 시스템

### v0.1.0 (현재)
- 프로젝트 초기 설정
- 기본 아키텍처 구현
- CLI 인터페이스

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원 및 문의

- **이슈 트래커**: [GitHub Issues](https://github.com/your-org/Openflow_with_LLM/issues)
- **문서**: [Wiki](https://github.com/your-org/Openflow_with_LLM/wiki)
- **이메일**: support@your-org.com

## 🙏 감사의 말

- Apache NiFi 커뮤니티
- OpenAI 및 기타 LLM 제공업체
- 모든 기여자들

---

**⭐ 이 프로젝트가 유용하다면 스타를 눌러주세요!**
