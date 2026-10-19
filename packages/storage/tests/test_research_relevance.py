"""Explicit journal candidates narrowed atomically in synthetic PostgreSQL."""
from uuid import uuid4
import pytest
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import StorageCorruption
from issuedigest_storage.research import ResearchRepository
from issuedigest_storage.research_schema import research_runs
from sqlalchemy import update
from test_research_repository import setup_run, add_topic


def prepared(engine):
    bundle,sid,user,token=setup_run(engine)
    repo=ResearchRepository(engine)
    run=repo.submit(token,bundle.document.workspace_id,ResearchRequest(request_id=uuid4(),question='80% 의미는?'))
    repo.worker_transition(run.run_id,'retrieving')
    fixed=repo.worker_search_and_fix(run.run_id,('80%',))
    return repo,run,token,user,fixed


def test_explicit_candidates_are_reopened_after_atomic_selection(engine):
    repo,run,token,_,fixed=prepared(engine)
    assert hasattr(repo,'worker_load_relevance_candidates'), 'missing explicit relevance load'
    loaded=repo.worker_load_relevance_candidates(run.run_id,fixed)
    assert tuple(s[0] for s in loaded[1])==fixed
    assert repo.worker_apply_relevance_selection(run.run_id,fixed,fixed,input_tokens=200,output_tokens=100)==fixed
    assert repo.worker_apply_relevance_selection(run.run_id,fixed,fixed,input_tokens=200,output_tokens=100)==fixed


@pytest.mark.parametrize('mutation',['unknown','duplicate','reorder','oversize','row','empty-candidates'])
def test_invalid_selection_never_changes_fixed_ids(engine,mutation):
    repo,run,token,_,fixed=prepared(engine)
    assert hasattr(repo,'worker_apply_relevance_selection'), 'missing atomic relevance apply'
    candidates=fixed
    selected=(uuid4(),)
    if mutation=='duplicate': selected=fixed+fixed
    if mutation=='reorder':
        other,_=add_topic(engine,run.workspace_id,'80%')
        candidates=(*fixed,other)
        with engine.begin() as conn: conn.execute(update(research_runs).where(research_runs.c.run_id==run.run_id).values(snapshot_ids=list(map(str,candidates))))
        selected=candidates[::-1]
    if mutation=='oversize': candidates=tuple(uuid4() for _ in range(6))
    if mutation=='row': candidates=(uuid4(),); selected=candidates
    if mutation=='empty-candidates': candidates=(); selected=()
    with pytest.raises((ValueError,StorageCorruption)):
        repo.worker_apply_relevance_selection(run.run_id,candidates,selected,input_tokens=200,output_tokens=100)


def test_all_excluded_is_atomic_known_usage_failure(engine):
    repo,run,token,_,fixed=prepared(engine)
    assert hasattr(repo,'worker_apply_relevance_selection'), 'missing atomic relevance apply'
    assert repo.worker_apply_relevance_selection(run.run_id,fixed,(),input_tokens=200,output_tokens=100) is None
    after=repo.get_run(token,run.workspace_id,run.run_id)
    assert after.snapshot_ids==() and after.error_code=='insufficient_evidence'
    assert (after.input_tokens,after.output_tokens)==(200,100)
