"""Gemini tool calling with explicit approval-free, read-only analytics tools."""
import json
import os
import uuid
from .tool_trace import write_trace
from .investigation import execute_tool, evidence_label

SYSTEM = '''You are BankOps AI, a banking-operations analytics assistant.
All records are synthetic demonstration data, not actual banking evidence.
You must call the provided read-only tools before making numeric claims.
Never claim causation from correlations or aggregates.
Synthetic scenario labels are reserved for evaluation. Investigate only the evidence returned by approved tools.
Quote the specific metrics, cohorts, dates, and sample counts from tool outputs.
When reporting numerical results, copy the values directly from the SQL tool output.
Do not independently recalculate, estimate, or round values already returned by a tool.
For estimated excess breaches, use the exact excess_breaches value from compare_segments, formatted to two decimal places.
For percentage-point changes, use the supplied change_pp value rather than recalculating from displayed rates.
Never introduce a different numerical value from the one returned by the cited evidence.
When answering a question about leading teams or categories, cite the corresponding compare_segments result.
Do not assume bank policy thresholds or give a conclusion the data cannot support.
Cite evidence as [E1], [E2], etc., matching the displayed tool results.
If the data is insufficient, say what would be needed.
When investigating recent performance changes, use compare_segments to identify changes by category and team. Do not interpret all-time breakdowns as recent changes.

Keep answers concise: observation, supporting evidence, limitations, next check.'''


def _declarations(types):
    category = {'type':'string','description':'Exact category name; omit to include every category.'}
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(name='get_breakdown',description='Read ticket counts, SLA breaches and average resolution time grouped by category, team, priority or channel; optional category filter.',parameters_json_schema={'type':'object','properties':{'dimension':{'type':'string','enum':['category','team','priority','channel']},'category':category}}),
        types.FunctionDeclaration(name='compare_periods',description='Compare baseline and recent periods and their SLA breach rates.',parameters_json_schema={'type':'object','properties':{'category':category}}),
        types.FunctionDeclaration(name='get_weekly_trend',description='Get the SLA breach trend by week.',parameters_json_schema={'type':'object','properties':{'category':category}}),
        types.FunctionDeclaration(name='get_data_quality',description='Check missing deadlines and inconsistent ticket dates or statuses; optional category filter.',parameters_json_schema={'type':'object','properties':{'category':category}}),
        types.FunctionDeclaration(
            name="compare_segments",
            description="Compare the latest seven days against the preceding 28 days by category, team, priority or channel. Returns historical and recent breach rates, percentage-point changes, and estimated excess breaches.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "dimension": {
                        "type": "string",
                        "enum": ["category", "team", "priority", "channel"]
                    },
                    "category": {"type": "string"}
                }
            }
        ),
        types.FunctionDeclaration(name='get_open_backlog',description='Get open and overdue tickets by priority.',parameters_json_schema={'type':'object','properties':{'category':category}}),
    ])


def investigate(question, api_key, model=None, db_path=None, max_rounds=4):
    """Return (answer, evidence). Requires network and valid Gemini key.

    All database operations are fixed SQL queries selected by approved tools.
    We deliberately run tools ourselves rather than automatic function calling.
    """
    from google import genai
    from google.genai import types
    model = model or os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    if not api_key or not api_key.strip():
        raise ValueError('GEMINI_API_KEY is required')
    if not question or len(question)>2000:
        raise ValueError('Question must contain 1-2000 characters')
    client=genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=15000))
    contents=[types.Content(role='user',parts=[types.Part.from_text(text=question)])]
    tool = _declarations(types)
    cfg=types.GenerateContentConfig(system_instruction=SYSTEM,tools=[tool],temperature=0.1,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    evidence=[]
    run_id=uuid.uuid4().hex[:12]
    write_trace(run_id, "start", question=question, model=model)
    for _ in range(max_rounds):
        try:
            response=client.models.generate_content(model=model,contents=contents,config=cfg)
        except Exception as exc:
            write_trace(run_id, "api_error", error_type=type(exc).__name__, error_message=str(exc)[:300])
            write_trace(run_id, "interrupted", status="partial", evidence_count=len(evidence))
            return "PARTIAL_INVESTIGATION: Gemini API interrupted.", evidence
        calls=response.function_calls or []
        if not calls:
            if not evidence:
                # Require evidence: force a baseline query before letting the model answer.
                result=execute_tool('get_breakdown',{'dimension':'category'},**({'db_path':db_path} if db_path else {}))
                evidence.append({'id':'E1','tool':'get_breakdown','args':{'dimension':'category'},'rows':result})
                contents.append(types.Content(role='user',parts=[types.Part.from_text(text='Before answering, use this verified evidence [E1]: '+json.dumps(result)+'. Cite [E1] and avoid unsupported claims.')]))
                continue
            write_trace(run_id, "finished", status="completed", evidence_count=len(evidence))
            return (response.text or 'The model did not provide a text answer.'), evidence
        contents.append(response.candidates[0].content)
        parts=[]
        for call in calls:
            name=call.name
            args=dict(call.args or {})
            write_trace(run_id, "tool_requested", tool=name, args=args)
            try:
                rows=execute_tool(name,args,**({'db_path':db_path} if db_path else {}))
                record={'id':f'E{len(evidence)+1}','tool':name,'args':args,'rows':rows}
                evidence.append(record)
                write_trace(run_id, "tool_success", evidence_id=record["id"], tool=name, args=args, row_count=len(rows), rows=rows[:25])
                payload={'evidence_id':record['id'],'rows':rows}
            except (ValueError,TypeError) as e:
                write_trace(run_id, "tool_error", tool=name, args=args, error_type=type(e).__name__, error_message=str(e)[:300])
                payload={'error':str(e)}
            parts.append(types.Part.from_function_response(name=name,response=payload))
        contents.append(types.Content(role='user',parts=parts))
    # Return verified evidence without fabricating a model conclusion if the limit is hit.
    write_trace(run_id, "finished", status="tool_limit", evidence_count=len(evidence))
    return 'Investigation stopped at the tool-call limit. Review the evidence below; no unverified conclusion was generated.',evidence


def demo_investigation(db_path=None):
    """Offline demonstration with fixed queries; not an LLM-generated explanation."""
    kwargs={'db_path':db_path} if db_path else {}
    records=[]
    for name,args in [('get_breakdown',{'dimension':'category'}),
                      ('compare_periods',{'category':'Payment Investigation'}),
                      ('get_breakdown',{'dimension':'priority','category':'Payment Investigation'}),
                      ('get_open_backlog',{'category':'Payment Investigation'})]:
        rows=execute_tool(name,args,**kwargs)
        records.append({'id':f'E{len(records)+1}','tool':name,'args':args,'rows':rows})
    return records
