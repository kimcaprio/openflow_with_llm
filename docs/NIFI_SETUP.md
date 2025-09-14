# Apache NiFi 로컬 환경 설정 가이드

이 문서는 Openflow with LLM 프로젝트에서 Apache NiFi를 로컬 환경에서 설정하고 관리하는 방법을 설명합니다.

## 📋 목차

- [환경 요구사항](#환경-요구사항)
- [NiFi 설치 확인](#nifi-설치-확인)
- [환경 설정](#환경-설정)
- [NiFi 제어 방법](#nifi-제어-방법)
- [문제 해결](#문제-해결)

## 🔧 환경 요구사항

### 시스템 요구사항
- **운영체제**: macOS, Linux, Windows
- **Java**: JDK 8 이상 (JDK 11 권장)
- **메모리**: 최소 2GB RAM (4GB 권장)
- **디스크**: 최소 1GB 여유 공간

### 현재 설정
- **NiFi Home**: `/Users/kikim/Downloads/nifi-2.4.0`
- **NiFi Version**: 2.4.0
- **Web UI Port**: 8080
- **API Base URL**: `https://localhost:8443/nifi-api`

## 📦 NiFi 설치 확인

### 1. NiFi 디렉토리 구조 확인

```bash
ls -la /Users/kikim/Downloads/nifi-2.4.0/
```

다음과 같은 구조가 있어야 합니다:
```
nifi-2.4.0/
├── bin/           # 실행 스크립트
├── conf/          # 설정 파일
├── lib/           # 라이브러리
├── logs/          # 로그 파일
└── work/          # 작업 디렉토리
```

### 2. Java 설치 확인

```bash
java -version
echo $JAVA_HOME
```

## ⚙️ 환경 설정

### 1. 환경 변수 설정

프로젝트 루트에서 환경 설정을 로드합니다:

```bash
# 환경 설정 로드
source config/nifi_env.sh

# 설정 확인
echo $NIFI_HOME
echo $NIFI_API_URL
```

### 2. 프로젝트 환경 파일 설정

`config/env.example`을 복사하여 `.env` 파일을 생성하고 필요한 설정을 수정합니다:

```bash
cp config/env.example .env
# .env 파일을 편집하여 NIFI_HOME 경로 확인
```

## 🎮 NiFi 제어 방법

### 1. Shell Script 사용

#### 기본 명령어

```bash
# NiFi 시작
./scripts/nifi_control.sh start

# NiFi 중지
./scripts/nifi_control.sh stop

# NiFi 재시작
./scripts/nifi_control.sh restart

# NiFi 상태 확인
./scripts/nifi_control.sh status

# NiFi 로그 확인
./scripts/nifi_control.sh logs

# NiFi 로그 실시간 모니터링
./scripts/nifi_control.sh follow
```

#### 빠른 명령어 (Quick Commands)

```bash
# 빠른 명령어 로드
source scripts/nifi_quick.sh

# 사용법
nifi-start      # NiFi 시작
nifi-stop       # NiFi 중지
nifi-restart    # NiFi 재시작
nifi-status     # 상태 확인
nifi-logs       # 로그 확인
nifi-follow     # 로그 실시간 모니터링
```

### 2. Python CLI 사용

#### 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# CLI 도움말
python src/cli/nifi_cli.py --help
```

#### 기본 명령어

```bash
# NiFi 시작
python src/cli/nifi_cli.py start

# NiFi 중지
python src/cli/nifi_cli.py stop

# NiFi 재시작
python src/cli/nifi_cli.py restart

# 상태 확인
python src/cli/nifi_cli.py status

# JSON 형태로 상태 확인
python src/cli/nifi_cli.py status --json

# 로그 확인
python src/cli/nifi_cli.py logs -n 100

# API 연결 테스트
python src/cli/nifi_cli.py test-api

# 설치 정보 확인
python src/cli/nifi_cli.py info
```

### 3. Python 코드에서 사용

```python
from src.utils.nifi_manager import NiFiManager

# NiFi 매니저 생성
manager = NiFiManager()

# NiFi 시작
if manager.start():
    print("NiFi started successfully")

# 상태 확인
status = manager.get_status()
print(f"NiFi running: {status['running']}")

# NiFi 중지
if manager.stop():
    print("NiFi stopped successfully")
```

## 🔍 NiFi 접속 및 확인

### 1. Web UI 접속

NiFi가 시작된 후 다음 URL로 접속:
- **Web UI**: https://localhost:8443/nifi

### 2. API 엔드포인트 확인

```bash
# 시스템 진단 정보
curl https://localhost:8443/nifi-api/system-diagnostics

# 클러스터 정보
curl https://localhost:8443/nifi-api/controller/cluster
```

### 3. 상태 확인 스크립트

```bash
# 종합 상태 확인
./scripts/nifi_control.sh status
```

출력 예시:
```
[INFO] NiFi Status:
[SUCCESS] NiFi is running (PID: 12345)
[SUCCESS] NiFi API is responding
[INFO] NiFi Web UI: https://localhost:8443/nifi
[INFO] NiFi API: https://localhost:8443/nifi-api
```

## 🛠️ 문제 해결

### 1. 일반적인 문제

#### NiFi가 시작되지 않는 경우

```bash
# Java 설치 확인
java -version

# JAVA_HOME 설정 확인
echo $JAVA_HOME

# NiFi 홈 디렉토리 확인
ls -la $NIFI_HOME

# 로그 확인
./scripts/nifi_control.sh logs
```

#### 포트 충돌 문제

```bash
# 8080 포트 사용 확인
lsof -i :8080

# 다른 포트로 변경 (nifi.properties 수정)
vim $NIFI_HOME/conf/nifi.properties
# nifi.web.http.port=8081
```

#### 메모리 부족 문제

```bash
# JVM 힙 크기 조정
export NIFI_JVM_HEAP_INIT="1g"
export NIFI_JVM_HEAP_MAX="4g"

# 또는 nifi-env.sh 파일 수정
vim $NIFI_HOME/bin/nifi-env.sh
```

### 2. 로그 분석

#### 주요 로그 파일

```bash
# 애플리케이션 로그
tail -f $NIFI_HOME/logs/nifi-app.log

# 부트스트랩 로그
tail -f $NIFI_HOME/logs/nifi-bootstrap.log

# 사용자 로그
tail -f $NIFI_HOME/logs/nifi-user.log
```

#### 로그 레벨 조정

```bash
# logback.xml 수정
vim $NIFI_HOME/conf/logback.xml

# DEBUG 레벨로 변경
<logger name="org.apache.nifi" level="DEBUG"/>
```

### 3. 데이터 정리

#### 개발 중 데이터 초기화

```bash
# NiFi 중지
./scripts/nifi_control.sh stop

# 데이터 정리 (주의: 모든 플로우와 데이터가 삭제됨)
./scripts/nifi_control.sh clean

# 또는 Python CLI 사용
python src/cli/nifi_cli.py clean
```

#### 수동 데이터 정리

```bash
# NiFi 중지 후 실행
rm -rf $NIFI_HOME/database_repository/*
rm -rf $NIFI_HOME/flowfile_repository/*
rm -rf $NIFI_HOME/content_repository/*
rm -rf $NIFI_HOME/provenance_repository/*
```

### 4. 성능 튜닝

#### JVM 설정 최적화

```bash
# config/nifi_env.sh 수정
export NIFI_JVM_HEAP_INIT="2g"
export NIFI_JVM_HEAP_MAX="8g"

# GC 설정 추가
export JAVA_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=50"
```

#### 리포지토리 설정

```bash
# nifi.properties에서 리포지토리 경로 분산
nifi.database.directory=./database_repository
nifi.flowfile.repository.directory=./flowfile_repository
nifi.content.repository.directory.default=./content_repository
nifi.provenance.repository.directory.default=./provenance_repository
```

## 📚 추가 리소스

### 공식 문서
- [Apache NiFi Documentation](https://nifi.apache.org/docs.html)
- [NiFi System Administrator's Guide](https://nifi.apache.org/docs/nifi-docs/html/administration-guide.html)

### 유용한 명령어 모음

```bash
# NiFi 프로세스 확인
ps aux | grep nifi

# NiFi 포트 확인
netstat -an | grep 8080

# 디스크 사용량 확인
du -sh $NIFI_HOME/database_repository
du -sh $NIFI_HOME/content_repository

# 메모리 사용량 확인
top -p $(cat $NIFI_HOME/run/nifi.pid)
```

## 🔐 보안 설정 (선택사항)

### HTTPS 설정

```bash
# 인증서 생성
$NIFI_HOME/bin/tls-toolkit.sh standalone \
  -n localhost \
  -C 'CN=admin,OU=NIFI' \
  -o target

# nifi.properties 수정
nifi.web.https.host=localhost
nifi.web.https.port=8443
nifi.security.keystore=./conf/keystore.jks
nifi.security.keystorePasswd=password
```

이 가이드를 따라하면 Apache NiFi를 로컬 환경에서 안정적으로 운영할 수 있습니다.
