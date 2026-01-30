
### 0. 개요

본 프로젝트는 **Beyond Prompt Chaining: The TB-CSPN Architecture for Agentic AI** 논문의 초기 구현체임. 전체 논문 PDF는 다음 링크에서 확인 가능함: [https://www.mdpi.com/1999-5903/17/8/363](https://www.mdpi.com/1999-5903/17/8/363)

본 프로젝트는 금융감독원의 "금융분야 AI 활용 가이드라인"에 대응하기 위한 실험적 시도로서, 특히 에이전트 시스템(Agentic Systems)이 갖는 확률적 불확실성을 통제하는 데 주안점을 둠. 원 논문의 철학을 계승하여, 본 코드는 LLM 프로세스 실행 과정에 '반-결정론적(Semi-deterministic) 프로세스'를 강제 적용함.

해당 프로세스의 기술언어는 본 논문에 따라 Colored Petrinet 체계를 따름. CPN은 단순한 흐름도(Flowchart)가 아니라, "특정 규격(Color/Schema)을 갖춘 토큰만이 정해진 공정(Process)을 통과할 수 있다"는 규칙을 구현한 모델임. 

| **요소**         | **실제 구현체**   | **기능적 역할**                        |
| -------------- | ------------ | --------------------------------- |
| **Token**      | tokens.py    | 데이터 내용물 + 메타데이터(Topic)를 담은 객체     |
| **Transition** | tasks.py     | 입/출력 규격(Schema)을 검사하고 로직을 실행하는 관문 |
| **Place**      | execution.py | 데이터가 다음 공정으로 가기 전 대기하고 병합되는 장소    |
| **Guard**      | tokens.py    | 데이터의 상태나 주제가 기준에 맞는지 판별하는 필터      |
구조의 특징은 다음과 같음. 
1. 스키마 강제 (Schema-First): 각 작업(Task)은 정해진 규격의 토큰이 아니면 절대 수용하지 않음.
	LLM이 뱉는 비정형 데이터를 시스템이 이해할 수 있는 정형 데이터로 즉시 동기화함.

2. 결정론적 공정 관리 (Deterministic Control): LLM의 판단에 경로를 맡기지 않고, 데이터의 값에 따라 시스템이 경로를 결정함.
    - AND-Join(병합): 여러 데이터가 모두 모여야만 다음 단계로 넘어가는 물리적 통제가 가능함.
- 3. Fail-Fast (즉각 차단): 공정 중간에 데이터 규격이 틀어지면 즉시 중단되어, 잘못된 데이터가 후속 공정으로 전파되는 것을 원천 봉쇄함.



**고지 사항** 본 코드의 생성형 AI에 크게 의존하여 작성되었으며, 작성자가 상당 부분 수기 검증을 수행했음에도 오류가 발생할 가능성이 있음. 또한, 실험적 구현체이므로 상업적 용도를 목적으로 하지 않음. 본 코드를 활용해 발생하는 오류에 대해서 작성자는 책임을 지지 않음. 

### 1. 환경 설정 방법

본 Registry의 url을 복사해 로컬 디렉토리로 clone 후, 다음의 명령어를 터미널에 입력. 

```

# 가상환경 생성 (이름: venv) 
python -m venv venv 

# 가상환경 활성화 
# Windows: 
call venv\Scripts\activate 
# Mac/Linux: 
source venv/bin/activate

# requirements 설치
pip install -r requirements.txt
```

### 2. 활용 예시

```
from entity.tokens import Token
from core.utils import load_resource_specs
from entity.validators import TokenValidator

```

#### 2.1. 토큰

- 토큰(Token)은 비즈니스 데이터(Content)와 실행 맥락(History, Topics)을 캡슐화한 '규격화된 데이터 컨테이너'임.
- 단순한 텍스트 메시지 전달을 넘어, 각 공정(Task) 진입 시마다 엄격한 스키마 검증(Schema Validation)을 거쳐야만 이동할 수 있는 '보증된 화물' 역할을 수행함.
- 이를 통해 LLM의 비정형 출력을 시스템이 통제 가능한 정형 데이터로 강제 변환하여, 금융 프로세스에 필수적인 무결성(Integrity)과 추적 가능성(Auditability)을 보장함.

**선언 예시)**
```
#  사전 토큰 스키마 선언 예시 (yaml 타입 선언)
RS_RISK_TOKEN_V1: 
  spec_id: "RS_RISK_TOKEN_V1"
  associated_topic: "Credit_Risk"
  fields:
    text:
      type: "string"
      max_length: 100
    recent_risk:
	  type: "string"
	  max_lenght: None
    risk_score:
      type: "float"
      min_value: 0.0
      max_value: 1.0
      required: true
    timestamp:
      type: "string"
      required: false

# 최초 토큰 생성 예시
valid_token = Token(
    trace_id = "dfhou3898dfalss28fhs", 
    content = {
        "text" : "Loan Holder A Risk Analysis",
        "recent_risk" : "71일 연속 상환금액 연체 | 재무제표 중 유동성비율 지속 하락"
        "risk_score" : 0.96
    }
)

# 토큰 스펙 검증 예시
resource_db = load_resource_specs("./ResourceSpec/TokenSpec.yaml")
validator = TokenValidator(resource_db)
validator.validate(valid_token.content, "CREDIT_RISK_TOKEN_328a103")
# True

```

#### 2.2. 태스크

태스크는 다음과 같이 선언됨.

```
task_A = TaskSpec(
    # 일반 설명
    task_id = "TASK_TEST_001",
    description="금융 뉴스 감성 분석",
    type=TaskType.PYTHON_FUNC,
    target="utils.analysis:calculate_sentiment", # 실행 함수 경로

    # config
    config = {
        'business_context' : 'ojs가 분석을 위해 만든 최초 example'
    },

    # 구조 선언
    layer = Layer.OBSERVATION,
    required_agent_roles=[AgentRole.CONSULTANT],
    required_agent_types=[AgentNature.LLM],
  
    # 가드레일 선언
    guards = [
        GuardCondition(
            target_topic_id = "TOPIC_FINANCE",
            min_relevance=0.7,
            description="금융 관련성 0.7 이상 필수"
        )
    ],

    # 입력 토큰과 출력 토큰의 구조 정의
    input_spec_id="RS_RISK_TOKEN_V1",
    output_spec_id="RS_RISK_TOKEN_V2"
)

```

#### 2.3. 프로세스

프로세스는 다음과 같이 선언되며 연결됨. 프로세스는 분기된 두 개의 태스크가 다시 합쳐지는 프로세스 또한 표현 가능함. 
```
# ChainValidator Instance 선언

chain_check = SpecChainValidator(validator)

  

# 최초 선언시 아이디 선언

process_test = Process("Credit_Risk_Analysis_Process")

  

# 향후 DB에 기록된 Process 선언문 읽고 아래 instance action이 자동 수행되는 로직이 필요

process_test.tasks
process_test.add_task(task_A)
process_test.add_task(task_B)
process_test.add_task(task_C)
process_test.add_task(task_D)
process_test.add_task(task_E)

process_test.add_link(task_A, task_B)
process_test.add_link(task_A, task_C)
process_test.add_link(task_B, task_D)
process_test.add_link(task_C, task_D)
process_test.add_link(task_D, task_E)

# task간의 token spec 일치와 Acyclity 검증
process_test.compile(chain_check)
# TRUE

# process 실행 그래프 확인
process_test.graph

# process 내부 tasks 확인
process_test.tasks
```

#### 2.4. 엔진


### 3. 향후 보완사항

본구조에 대한 비판 가능 사항은 다음과 같음. 
1. 결국 Agent Workflow를 하드코딩하는 것과 큰 차이가 없는 것이 아닌지? 
	1. 맞음. 결국은 활용성의 문제임. 프로세스가 언어화되면 입력 및 제어가 쉬워짐. 다만, 지적한 대로 판단의 정합성을 LLM 지능에 위임하는 것이 아닌, 프로세스를 설계한 인간에게 수행한다는 점이 약점임.
	2. 따라서 수식적 표현 및 Acyclity 검증이 가능한 프로세스 언어화에 큰 의의를 둠. 물리적 구현체와 얽혀있는 공식적 언어화는, 모호한 상태로 남아있는 "프로세스"를 구체화하는데에 큰 도움이 될 것으로 예상됨
	3. **보완**: 프로세스 마이닝도 프로세스의 일종이므로, 마이닝의 언어화를 통해 해당 프로세스를 자동화하는 것을 목표로 함. 
2. 기존 langchain "Message State"(Agent간에 오고 가는 chain message. 본 프로젝트의 토큰에 대응됨)를 과하게 규격화하는 것이 아닌지? 언어처리능력에 강점을 보이는 LLM의 능력을 제한하는 물리적 규제가 되는 것 아닌지? 
	1. 규격화가 중요한 분야가 존재함. 특히 리스크관리 도메인에서, 이전 메시지의 노이즈가 Message State에 섞여 들어가는 것은 지양해야됨. 예를 들어, 특정 문서에서 특정 숫자 필드만 뽑는 태스크를 예시로 들 수 있음. 
	2. **보완** : 이것은 Token Universe가 확장되면서 해결될 문제로 예상됨. 다만, 도메인 맥락을 담는 Token Universe의 다양화는 또 다른 관리책임상의 부담이므로, 구체적 관리체계 마련은 엔지니어가 아닌 컨설턴트의 몫으로 예상됨.  
3. 결국 프로세스 추출 인력이 정합성의 부담을 전부 지는 것이 아닌지?
	1. 해당 부분은 긴 설득이 필요한 사안임. 결국 agent system은 생성형 AI 불확실성을 어떻게 통제하고 (인간을 포함한) 시스템 전체에 부담을 전가시키냐의 문제임. 해당 비판 때문에 통제 시도를 늦출 수는 없음. 
	2. **보완** : 프로세스 추출 및 언어화는 노하우의 영역임. 이를 컨설팅 인력이 선점해야 하는 것으로 예상됨. 