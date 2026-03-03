# CERN Systems Portal Demo: High-Availability Telemetry & Management

![Status](https://img.shields.io/badge/Status-Live-success)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![C++](https://img.shields.io/badge/C++-17-00599C?logo=cplusplus&logoColor=white)
![Java](https://img.shields.io/badge/Java-17-ED8A00?logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.4-6DB33F?logo=springboot&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)
![Vue](https://img.shields.io/badge/Vue.js-3-4FC08D?logo=vuedotjs&logoColor=white)
![Django](https://img.shields.io/badge/Django-5-092E20?logo=django&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-EC2-FF9900?logo=amazonec2&logoColor=white)

**Live Demo:** [https://smcm-cern-demo.com](https://smcmahon-cms-glance-demo.com)  
*(Login: `cern` / `cms123`)*

## Overview
This project serves as a technical demonstration of a distributed systems portal designed for the CMS Experiment at CERN. The system integrates real-time telemetry processing with an administrative management dashboard, bridging the gap between low-level hardware simulation and high-level data orchestration.

It provides a comprehensive solution for managing 5,000+ personnel records, M&O qualifications, and scientific publication lifecycles, while simultaneously processing live beam intensity data (BCTDC) from a dedicated C++ simulation engine.

## Distributed Telemetry Module

The system features a live telemetry pipeline that mirrors the data flow in a physical experiment environment:

- **C++ Beam Simulator:** A dedicated engine simulating Beam Current Transformer (BCTDC) signals, modeling proton intensity and energy ramps.

- **Java Spring Boot Service:** A high-throughput telemetry harvester that ingests sensor data, manages time-series persistence, and provides a RESTful interface for historical trend analysis.

- **Uplink Observer:** A Vue.js 3 frontend that visualizes live data via Chart.js and allows for operator-led state transitions (Ramp, Stable Beams, and Emergency Dump).



## Key Features

- **LHC Live Telemetry:** Real-time monitoring of circulating beam intensity with interactive hardware control capabilities.

- **Incubator Dashboard:** Analytical view of workforce composition, shift distribution, and publication throughput.

- **Member Directory:** Searchable directory with performance-optimized filtering by institute, country, and contract type.

- **Analysis Lifecycle Tracker:** Tracking of scientific papers through the four-stage CMS internal approval process.

- **Shift Management:** Interactive calendar system for scheduling and auditing control room shifts across global sites.
    
- **Legacy Mode:** A toggleable interface theme inspired by vintage X11 and Java Swing applications used in early CERN computing environments.

## Tech Stack

- **Languages:** C++ 17, Java 17, Python 3.12, JavaScript (ES6+).

- **Frameworks:** Vue.js 3 (Composition API), Spring Boot 3.4, Django 5 (REST Framework).

- **Infrastructure:** Docker, Docker Compose, Nginx (API Gateway).

- **Deployment:** AWS EC2, Route 53, SSL/TLS via Let's Encrypt.

## Architecture

The portal utilizes a containerized microservices architecture to maintain service isolation and scalability. 

Services communicate over an internal Docker bridge network; the C++ engine pushes telemetry to the Java harvester via high-frequency REST calls, while the Django management API coordinates machine state overrides:

1. **Nginx Gateway:** Operates as a Reverse Proxy and API Gateway, handling SSL termination and routing traffic to the internal Docker network.

2. **Telemetry Service (Java):** Optimized for high-frequency data ingestion and historical retrieval.

3. **Management API (Python):** Handles relational data, user authentication (JWT), and personnel records.

4. **Hardware Simulator (C++):** An independent service simulating sensor signals via low-level logic.

5. **Database (PostgreSQL):** Centralized persistence for both time-series telemetry and administrative records.

## Local Installation

**Prerequisites:** Docker & Docker Compose.

The project includes a unified deployment script to handle container orchestration, migrations, and mock data seeding automatically.

```bash
# 1. Clone the repository
git clone [https://github.com/yourusername/smcm-cern-demo.git](https://github.com/yourusername/smcm-cern-demo.git)
cd smcm-cern-demo

# 2. Run deployment script
chmod +x deploy.sh
./deploy.sh
```

**Access Locally:** http://localhost

**Django Admin:** http://localhost/admin

**Java API:** http://localhost:8080/api/v1/telemetry/history

## Testing

The system includes a comprehensive suite of integration tests to ensure data integrity across the stack.

**Backend Integration Tests (Django)**

Validates API security, KPI accuracy, and shift scheduling logic.
Bash
```
docker compose exec backend python manage.py test
```

Coverage includes Dashboard metrics, Shift CRUD operations, and Analysis lifecycle filtering.

**Frontend Unit Tests (Vitest)**

Ensures UI components and telemetry mapping logic remain stable.

Bash
```
cd frontend && npm run test:unit                                        
```

## Deployment (AWS)

This project is deployed on an AWS EC2 t3.micro instance.

- Infrastructure: AWS EC2 t3.micro.

- Security: HTTPS enforced via Certbot and Nginx.

- Persistence: Volume-mapped PostgreSQL data to ensure durability.

## Gallery

<div align="center">
  <img src="screenshots/LHC-Monitor.png" width="800" alt="LHC Monitor">
  <p><em>LHC Telemetry Monitor: Real-time monitor of simulated telemetry data generated by a C++ script and ingested by a Java service.</em></p>

  <img src="screenshots/calendar_view.png" width="800" alt="Shift Scheduler">
  <p><em>Shift Management: Interactive calendar for assigning Control Room duties</em></p>

  <img src="screenshots/incubator_dashboard.png" width="800" alt="Incubator Dashboard">
  <p><em>The Main Dashboard: Real-time KPIs and workforce composition</em></p>
</div>  

---

