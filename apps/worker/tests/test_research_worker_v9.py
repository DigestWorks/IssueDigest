"""v9 ordered metadata and real PG/DBOS synthetic three-call integration."""
import json
import pytest
from issuedigest_worker import research_recovery
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse,ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_recovery_v3 import seed,output,client

EXPECTED=[(1,'issuedigest_research_plan_v7__model.request'),(2,'issuedigest_research_search_v9'),(3,'issuedigest_research_select_v9__model.request'),(4,'issuedigest_research_apply_v9'),(5,'issuedigest_research_v9__model.request')]

@pytest.mark.parametrize('stage,count,valid',[('queued',0,True),*[(s,n,n==5 if s!='retrieving' else 1<=n<=4) for s in ['retrieving','generating','validating'] for n in range(6)]])
def test_exact_v9_metadata_prefix_before_deserialization(stage,count,valid):
    assert hasattr(research_recovery,'completed_v9_checkpoint'), 'missing recovery9 guard'
    class Metadata:
        def list_workflow_steps(self,*args,**kwargs):
            assert kwargs==dict(load_output=False,limit=21)
            return [dict(function_id=i,function_name=n,completed_at_epoch_ms=1) for i,n in EXPECTED[:count]]
    assert research_recovery.completed_v9_checkpoint(Metadata(),'synthetic',stage)==valid

@pytest.mark.parametrize('decision',['retain','uncertain','exclude'])
def test_default_v9_selector_and_known_combined_usage(engine,database_url,decision):
    bundle,token,repo,run=seed(engine,database_url)
    calls=[]
    def respond(messages,info):
        name=info.output_tools[0].name
        calls.append(name)
        if name=='search_evidence': payload={'queries':['80%']}
        elif name=='classify_relevance':
            prompt=json.loads(messages[-1].parts[0].content)
            payload={'decisions':[{'snapshot_id':s['snapshot_id'],'decision':decision} for s in prompt['sources']]}
        else: payload=output(bundle,classified=True,core=True)
        return ModelResponse(parts=[ToolCallPart(name,payload)],usage=RequestUsage(input_tokens=100,output_tokens=50))
    run_worker(database_url,model=FunctionModel(respond),once=True)
    after=repo.get_run(token,run.workspace_id,run.run_id)
    assert after.status==('failed' if decision=='exclude' else 'completed')
    assert calls==['search_evidence','classify_relevance']+([] if decision=='exclude' else ['answer'])
    assert (after.input_tokens,after.output_tokens)==((200,100) if decision=='exclude' else (300,150))
    inspector=client(database_url)
    try:
        steps=inspector.list_workflow_steps(f'research-{run.run_id}',load_output=False)
        assert [(s['function_id'],s['function_name']) for s in steps]==EXPECTED[:4 if decision=='exclude' else 5]
    finally: inspector.destroy()
