### 연관 태스크 정의
## Task는 Transition이다 (화살표다)
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

    # 구조
    layer = Layer.OBSERVATION,
    required_agent_roles=[AgentRole.CONSULTANT],
    required_agent_types=[AgentNature.LLM],

    # 가드 구조 선언
    guards = [
        GuardCondition(
            target_topic_id = "TOPIC_FINANCE", 
            min_relevance=0.7,
            description="금융 관련성 0.7 이상 필수"
        )
    ],

    # TokenSpec.yaml 파일 참고
    input_spec_id="RS_RISK_TOKEN_V1",
    output_spec_id="RS_RISK_TOKEN_V2"
)

### 연관 태스크 정의
## Task는 Transition이다 (화살표다)
task_B = TaskSpec(
    # 일반 설명
    task_id = "TASK_TEST_002",
    description="분석 결과 추가 분석",
    type=TaskType.PYTHON_FUNC, 
    target="utils.analysis:calculate_sentiment", # 실행 함수 경로

    # config
    config = {
        'business_context' : 'ojs가 분석을 위해 만든 최초 example'
    },

    # 구조
    layer = Layer.OBSERVATION,
    required_agent_roles=[AgentRole.CONSULTANT],
    required_agent_types=[AgentNature.LLM],

    # 가드 구조 선언
    guards = [
        GuardCondition(
            target_topic_id = "TOPIC_FINANCE", 
            min_relevance=0.7,
            description="금융 관련성 0.7 이상 필수"
        )
    ],

    # TokenSpec.yaml 파일 참고
    input_spec_id="RS_RISK_TOKEN_V3",
    output_spec_id="RS_RISK_TOKEN_V2"
)