
제기된 비판(추상화 부족, 외부 연동성 미흡)을 수용하여, **"단순 루프"** 수준의 기획을 **"엔터프라이즈급 프레임워크"** 아키텍처로 격상시킨 수정된 프로젝트 계획(WBS)입니다.

핵심 변경점은 **[Layer 2: Abstraction & Compiler]**의 신설입니다. DB의 JSON 정의를 바로 실행하지 않고, 중간 언어(IR)로 변환하여 `SNAKES` 등 외부 수학적 모델과 소통하는 **'프로토콜 레이어'**를 구축합니다.

---

### **TB-CSPN Framework Development Plan (Revised)**

#### **Phase 0. 아키텍처 설계 (Architecture Definition)**

- **Goal:** 4-Layer 아키텍처(Data - Compiler - Verification - Runtime)의 명세 확립.
    
    - **0.1. 데이터 스키마 표준화:** `TASK_SPECIFICATION_DB`, `RESOURCE_SPECS`, `TOPIC_DB`의 JSON Schema 확정.
		- [x] 현재 완료사항 ; Token Spec 정의 완료
		- [ ] Task_Specification_DB
		- [ ] 
    - **0.2. JSON-to-CPN 매핑 프로토콜 정의:** DB의 "Role/Transition"을 Petri Net의 "Transition/Arc"로 변환하는 수학적 매핑 규칙 수립.
        
    - **0.3. 에이전트 인터페이스 계약(Contract) 정의:** 에이전트가 지켜야 할 입/출력 규격 및 Context 주입 방식 표준화.
        

#### **Phase 1. 데이터 레이어 구축 (The Foundation)**

- **Goal:** 정적 정의(Static Definition)의 저장소 및 관리 체계 구현.
    
    - **1.1. Process DB & Version Control:** JSONB 기반의 프로세스 저장소 구현 (CRUD 및 버전 관리).
        
    - **1.2. Knowledge Base (TOPIC_DB) 구축:** 에이전트 공용 지식/임계치 저장소 구현.
        
    - **1.3. Resource Registry:** 토큰 규격(`RESOURCE_SPECS`) 저장 및 조회 모듈 구현.
        

#### **Phase 2. 추상화 및 검증 레이어 (The Compiler & Gatekeeper)**

- **Goal:** **(핵심 변경)** DB 정의를 정형 모델로 변환하고 무결성을 보증.
    
    - **2.1. CSPN Compiler 개발:** JSON Spec을 읽어 `snakes.PetriNet` 객체(Python Object)로 변환하는 파서(Parser) 구현.
        
    - **2.2. Formal Verification Module:** `SNAKES` 라이브러리를 연동하여 컴파일된 모델의 Deadlock, Liveness, Reachability 분석 기능 구현.
        
    - **2.3. Deployment Gate:** 검증을 통과한 프로세스만 `Runtime Engine`이 로드할 수 있도록 승인(Signing)하는 로직.
        

#### **Phase 3. 런타임 엔진 고도화 (The Executor)**

- **Goal:** 검증된 명세를 기반으로 실제 에이전트를 구동하는 결정론적 엔진.
    
    - **3.1. Generic Execution Loop:** 하드코딩된 로직을 제거하고, 컴파일된 명세(Transition Map)를 순회하는 범용 루프 구현.
        
    - **3.2. Dynamic Registry Loader:** 실행 시점에 필요한 `Guard`, `Agent` 함수를 동적으로 메모리에 매핑.
        
    - **3.3. Token Sandbox & Validator:** 각 Transition 진입/진출 시 `RESOURCE_SPECS`에 따라 토큰 데이터를 검증하고, 규격 위반 시 격리(Exception Handling)하는 로직.
        
    - **3.4. Nested Process Handler:** 서브 프로세스 호출 시 현재 토큰 스택을 저장(Push)하고 새 프로세스를 로드하는 Context Switch 로직.
        

#### **Phase 4. 에이전트 및 지식 연동 (The Intelligence)**

- **Goal:** "철도" 위에 올릴 "지능형 기차"와 "신호 체계" 구현.
    
    - **4.1. Agent Wrapper (Adapter Pattern):** LangGraph/LangChain 에이전트를 TB-CSPN 인터페이스에 맞게 감싸는 어댑터 구현.
        
    - **4.2. Context Injection Mechanism:** `TOPIC_DB`의 데이터를 에이전트 실행 시점에 Read-only Context로 주입.
        
    - **4.3. Adaptive Threshold Logic:** `TOPIC_DB`의 동적 변화(예: 시장 위기 단계 격상)가 엔진의 Guard 조건에 실시간 반영되는 로직.
        

#### **Phase 5. 관측 및 운영 도구 (The Black Box)**

- **Goal:** 시스템 투명성 확보 및 디버깅.
    
    - **5.1. Provenance Recorder:** 토큰 이동 경로, 가드 통과 사유, 에이전트 추론 근거를 토큰 메타데이터에 자동 기록.
        
    - **5.2. Visualizer (Optional):** 현재 실행 중인 Petri Net의 상태(Marking)를 시각화 (SNAKES의 draw 기능 활용 가능).
        

---

### **핵심 차별점 (vs 이전 계획)**

1. **Compiler 도입:** DB(JSON)와 Runtime(Python) 사이에 **중간 언어(Intermediate Representation)** 단계를 두어, `SNAKES`뿐만 아니라 향후 다른 정형 도구와도 연동 가능하도록 유연성 확보.
    
2. **Gatekeeper 개념:** "검증되지 않은 프로세스는 실행하지 않는다"는 원칙을 시스템적으로 강제.
    
3. **Nested Process:** 단일 프로세스가 아닌, 프로세스 간 호출을 염두에 둔 런타임 스택(Stack) 설계 포함.
    
### 로그 깊이 설계

- 로그는 세션로그와 토큰로그로 구분. 
- 세션로그는 말 그대로 세션 중 발생한 이벤트에 대한 로그
- 동일한 정보는 토큰로그에서도 확인 가능하나, 별도 분리하여 관리함

