"""Simulate two independent CV analysis batches without paid API requests."""
import json
import matching

def test_cv_review_parallel_batches(monkeypatch):
 monkeypatch.setenv("OPENAI_API_KEY","unit-test-token")
 seen=[]
 class Response:
  def __init__(self,job_candidates):
   self.job_candidates=job_candidates
  def raise_for_status(self):pass
  def json(self):
   return {"choices":[{"message":{"content":json.dumps({
      "matches":[{"id":j["id"],"cv_fit":85,"evidence":"Experienced operations"}
                  for j in self.job_candidates]})}}]}
 def fake_post(*args,**kwargs):
  jobs=json.loads(kwargs["json"]["messages"][1]["content"])["job_candidates"]
  seen.append([v["id"] for v in jobs])
  return Response(jobs)
 monkeypatch.setattr(matching.requests,"post",fake_post)
 profile={"cv_for_matching":"Experienced operations manager and project coordinator."}
 jobs=[{"title":"Operations Manager","description":"Business operations, governance and reporting"}
       for i in range(35)]
 result=matching.ai_cv_fit(profile,jobs)
 assert len(seen)==2
 assert set(result)==set(range(35))
 assert all(item["cv_fit"]==85 for item in result.values())

def test_empty_cv_never_calls_api(monkeypatch):
 monkeypatch.setenv("OPENAI_API_KEY","unit-test-token")
 monkeypatch.setattr(matching.requests,"post",
                     lambda *a,**kw:(_ for _ in ()).throw(AssertionError("unexpected API call")))
 assert matching.ai_cv_fit({"cv_for_matching":""},[{"title":"Finance Manager"}])=={}
