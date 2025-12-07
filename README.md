# 🕵️ DotasPlus — Automated Dark-web OSINT Threat Intelligence Engine

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async%20API-009688?logo=fastapi&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-distributed%20tasks-37814A?logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

> **DotasPlus**는 다크웹(.onion) 및 OSINT 소스로부터 보안 관련 정보를 자동 수집·정규화·연관 분석하는  
> **Threat Intelligence (CTI) 파이프라인**입니다.  
> 비정형 텍스트를 구조화된 침해지표(IOC)로 변환하고, 조직 자산(Asset)과 매칭하여  
> **실질적인 Incident(침해 징후)**를 식별합니다.

시스템은 다음 세 가지에 중점을 두고 설계되었습니다:

- 🔌 **Extensibility** — 크롤러/정규화/분석 모듈 확장성
- 🧱 **Modularity** — API / Worker / Storage 역할 분리
- ⚡ **Async Processing** — FastAPI + Celery 기반 고성능 비동기 처리

---

## 🎯 Objectives (목표)

- 다크웹 및 OSINT 위협 신호 자동 수집  
- 비정형 텍스트를 IOC 기반 데이터로 정규화  
- 자산 중심(Asset-centric) 위협 분석  
- 노이즈 제거 및 실질 Incident 식별  
- LLM, 대시보드, 샌드박스 등과 연동 가능한 CTI 플랫폼 기반 구축

---

## 🧩 System Overview (시스템 개요)

| 컴포넌트 | 역할 | 설명 |
|----------|------|-------------|
| **FastAPI** | API Gateway | REST API, 파이프라인 트리거 |
| **Celery Worker** | Processing Engine | Crawling, Parsing, Matching, Incident 생성 |
| **Redis** | Message Broker | 태스크 큐 관리 |
| **PostgreSQL** | Storage | 자산/소스/RawDocument/Incident 저장 |
| **Tor Proxy** | Network Layer | .onion 익명 접근 지원 |

---

## 🛠 Architecture (아키텍처)

```mermaid
graph LR
    User[Client / Dashboard] -->|REST API| API[FastAPI Server]
    API -->|Submit Task| Redis[Redis Broker]
    Redis -->|Dispatch| Worker[Celery Worker]

    subgraph "Processing Pipeline"
        Worker -->|1. Crawl| C[Crawler (Tor\HTTP)]
        Worker -->|2. Normalize| N[Normalizer (Text Clean & IOC Extract)]
        Worker -->|3. Match| M[Matcher (IOC ↔ Asset DB)]
        Worker -->|4. Detect| I[Incident Generator]
    end

    C --> DB[(PostgreSQL)]
    N --> DB
    M --> DB
    I --> DB
```

---

## ⚙️ Core Pipeline (핵심 파이프라인)

### 1. Crawling Layer
- Tor(SOCKS5h) 기반 다크웹 접근
- 원본 HTML + 메타데이터 아카이빙
- 비동기 병렬 크롤링

### 2. Normalization Layer
- HTML 제거 및 본문 추출
- Regex 기반 IOC 자동 추출 (IP, Domain, URL, Email, Crypto Wallet 등)
- LLM 기반 Semantic Parsing 연동 가능

### 3. Asset Matching Layer
- IOC ↔ 자산 연관성 분석
- Noise 제거 / FP 최소화
- 심각도 기반 Incident 자동 생성

---

## 🗄 Data Model (Logical ERD)

```text
┌──────────┐        ┌───────────┐        ┌─────────────┐
│  Asset   │1      *│   IOC     │*      1│  Incident   │
│──────────│--------│───────────│--------│─────────────│
│ id       │        │ id        │        │ id          │
│ name     │        │ ioc_type  │        │ title       │
│ type     │        │ value     │        │ severity    │
│ identifier        │ source_id │        │ created_at  │
└──────────┘        │ asset_id  │        │ status      │
                    └───────────┘        └─────────────┘
                          ^
                          │
                    ┌─────────────┐
                    │ RawDocument │
                    │─────────────│
                    │ id          │
                    │ source_id   │
                    │ url         │
                    │ raw_html    │
                    │ fetched_at  │
                    └─────────────┘

┌──────────┐
│ Source   │
│──────────│
│ id       │
│ name     │
│ url      │
│ type     │
│ use_tor  │
└──────────┘
```

---

## 📁 Project Structure

```text
DotasPlus/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── tasks.py
│   ├── api/
│   ├── config.py
│   └── database.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 🔌 API Specification

### ● Register Asset
```http
POST /api/v1/assets
{
  "name": "Corporate Domain",
  "identifier": "example.com",
  "asset_type": "domain"
}
```

### ● Register Source
```http
POST /api/v1/sources
{
  "name": "Leak Forum",
  "url": "http://exampleforum.onion",
  "type": "darkweb",
  "use_tor": true
}
```

### ● Trigger Crawling
```http
POST /api/v1/sources/{id}/run_crawl
```

---

## 🚀 Getting Started

```bash
git clone https://github.com/rasasoe/DotasPlus.git
cd DotasPlus

# (선택) 환경 변수 설정
cp .env.example .env

# 서비스 실행
docker-compose up --build -d
```

Swagger 문서:
```
http://localhost:8000/docs
```

---

## 🛡 Security & Legal Notice

> ⚠️ 이 프로젝트는 **보안 연구 및 방어 목적**으로 설계되었습니다.  
> 불법적 사용 또는 비인가 시스템 접근은 금지됩니다.

- Tor 기반 접근은 국가별 법률을 반드시 확인해야 함  
- 본 프로젝트는 연구·학습·방어용이며 사용 책임은 사용자에게 있음  
- 악성 데이터 취급 시 별도 샌드박스 환경 사용 권장  

---

## 🛣 Roadmap

- [x] 비동기 크롤링 파이프라인 구축  
- [x] IOC 추출 + 자산 매칭  
- [ ] LLM 기반 문맥 분석  
- [ ] React 대시보드  
- [ ] Slack/Telegram 알림  
- [ ] Multi-worker 확장  
- [ ] 샌드박스 분석 연동  

---

## 📜 License
MIT License
