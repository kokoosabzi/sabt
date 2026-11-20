from pathlib import Path

from playwright.sync_api import expect


ROOT = Path(__file__).resolve().parents[1]
INDEX_SOURCE = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
OPERATIONS_MARKUP_START = INDEX_SOURCE.index('<section id="operationsPage"')
OPERATIONS_MARKUP_END = INDEX_SOURCE.index("</main>", OPERATIONS_MARKUP_START)
OPERATIONS_MARKUP = INDEX_SOURCE[OPERATIONS_MARKUP_START:OPERATIONS_MARKUP_END]
LISTENERS_START = INDEX_SOURCE.index("  $('operationForm').addEventListener")
LISTENERS_END = INDEX_SOURCE.index("  $('projectId').addEventListener", LISTENERS_START)
OPERATIONS_LISTENERS = INDEX_SOURCE[LISTENERS_START:LISTENERS_END]
HELPERS_START = INDEX_SOURCE.index("  function setSelectOptions(")
HELPERS_END = INDEX_SOURCE.index("  async function loadPropertiesPage()", HELPERS_START)
OPERATIONS_HELPERS = INDEX_SOURCE[HELPERS_START:HELPERS_END]


def test_operations_portal_exposes_the_transfer_workflow_controls():
    assert 'data-page="operations"' in INDEX_SOURCE
    assert 'id="operationForm"' in OPERATIONS_MARKUP
    assert 'id="operationParentNumber"' in OPERATIONS_MARKUP
    assert 'id="operationPartyForm"' in OPERATIONS_MARKUP
    assert 'id="operationStartButton"' in OPERATIONS_MARKUP
    assert 'id="operationReadyButton"' in OPERATIONS_MARKUP
    assert 'id="operationFinalizeButton"' in OPERATIONS_MARKUP


def test_browser_can_create_and_finalize_a_transfer_through_the_portal(page):
    page.set_content(
        '<!doctype html><html lang="fa" dir="rtl"><head><style>.hidden{display:none!important}</style></head>'
        '<body><main>' + OPERATIONS_MARKUP + '</main></body></html>'
    )
    page.locator("#operationsPage").evaluate("(element) => element.classList.remove('hidden')")
    setup = """
      const $ = id => document.getElementById(id);
      let activeOperation = null;
      let operationsProjectId = null;
      const operationState = {
        operation_id: 101, project_id: 7, status: 'DRAFT',
        workflow_state: 'DRAFT', version: 1, created_at: '2026-11-20T10:00:00Z',
        updated_at: '2026-11-20T10:00:00Z', parent_contract_id: 55
      };
      let operationCreated = false;
      const parties = [];
      const calls = [];
      function selectedProjectId(){ return 7; }
      function fmt(value){ return value || '—'; }
      function query(values){ return new URLSearchParams(values).toString(); }
      function showError(message){ window.lastOperationError = message; }
      function renderTextRows(bodyId, items, fields, emptyText){
        const body=$(bodyId);body.replaceChildren();
        if(!items.length){const row=document.createElement('tr');const cell=document.createElement('td');cell.colSpan=fields.length;cell.textContent=emptyText;row.appendChild(cell);body.appendChild(row);return;}
        items.forEach(item=>{const row=document.createElement('tr');fields.forEach(field=>{const cell=document.createElement('td');cell.textContent=typeof field==='function'?field(item):(item[field]??'—');row.appendChild(cell)});body.appendChild(row)});
      }
      async function api(path, options={}){
        calls.push({path,method:options.method||'GET',body:options.body?JSON.parse(options.body):null});
        if(path==='/projects/7/operation-types')return {items:[{id:3,code:'TRANSFER',name:'انتقال مالکیت'}]};
        if(path.startsWith('/people?'))return {items:[{id:21,first_name:'علی',last_name:'رضایی'}]};
        if(path.startsWith('/properties?'))return {items:[{id:31,unit_number:'۱۰۱',block_tower:'برج الف'}]};
        if(path==='/projects/7/party-roles')return {items:[{id:8,code:'BUYER_TRANSFEREE',name:'خریدار / منتقل‌الیه مورد تأیید'}]};
        if(path==='/contracts/parent/760123/history')return {parent:{id:55,project_id:7,contract_number:'760123',property_id:31}};
        if(path.startsWith('/operations?'))return {items:operationCreated?[{...operationState,operation_type_name:'انتقال مالکیت',parent_contract_number:'760123',property_id:31,child_contract_number:operationState.child_contract_number||null,transfer_sequence:operationState.transfer_sequence||null}]:[],pagination:{limit:100,offset:0,total:operationCreated?1:0,has_more:false}};
        if(path==='/operations'&&options.method==='POST'){operationCreated=true;return {...operationState,operation_id:101,parent_contract_id:55,version:1};}
        if(path==='/operations/101')return {...operationState};
        if(path==='/operations/101/parties'&&options.method==='POST'){
          const body=JSON.parse(options.body);parties.push({party_id:1,person_id:body.person_id,first_name:'علی',last_name:'رضایی',role_id:body.role_id,role_name:'خریدار / منتقل‌الیه مورد تأیید',sequence_no:body.sequence_no});
          operationState.version++;return {party_id:1};
        }
        if(path==='/operations/101/parties')return {operation_id:101,parties};
        if(path==='/operations/101/transition'&&options.method==='POST'){
          const body=JSON.parse(options.body);operationState.workflow_state=body.target_state;operationState.version++;
          return {...operationState};
        }
        if(path==='/operations/101/finalize'&&options.method==='POST'){
          operationState.status='FINALIZED';operationState.workflow_state='FINALIZED';operationState.version++;operationState.child_contract_number='760123/1';
          return {operation_id:101,status:'FINALIZED',workflow_state:'FINALIZED',version:operationState.version,child_contract_number:'760123/1'};
        }
        throw new Error('Unexpected API call: '+path+' '+(options.method||'GET'));
      }
    """
    page.add_script_tag(content=setup + OPERATIONS_LISTENERS + OPERATIONS_HELPERS + """
      window.loadOperationsPage = loadOperationsPage;
      window.getOperationCalls = () => calls;
      window.getOperationState = () => activeOperation;
      window.clearActiveOperation = () => { activeOperation = null; $('operationWorkspace').classList.add('hidden'); };
    """)

    page.evaluate("async () => await window.loadOperationsPage()")
    expect(page.locator("#operationTypeSelect option")).to_have_count(2)
    expect(page.locator("#operationPersonSelect option")).to_have_count(2)
    expect(page.locator("#operationRoleSelect")).to_have_value("8")

    page.locator("#operationTypeSelect").select_option("3")
    page.locator("#operationParentNumber").fill("760123")
    page.locator("#operationForm").evaluate("(form) => form.requestSubmit()")
    expect(page.locator("#operationWorkspace")).to_be_visible()
    expect(page.locator("#operationSummary")).to_contain_text("760123")
    expect(page.locator("#operationsRows")).to_contain_text("101")

    page.evaluate("window.clearActiveOperation()")
    page.locator("#operationsRefreshButton").click()
    page.locator("#operationsRows button[data-operation-id='101']").click()
    expect(page.locator("#operationWorkspace")).to_be_visible()
    expect(page.locator("#operationSummary")).to_contain_text("760123")

    page.locator("#operationPersonSelect").select_option("21")
    page.locator("#addOperationPartyButton").click()
    expect(page.locator("#operationPartyRows")).to_contain_text("علی رضایی")

    page.locator("#operationStartButton").click()
    expect(page.locator("#operationSummary")).to_contain_text("IN_PROGRESS")
    page.locator("#operationReadyButton").click()
    expect(page.locator("#operationSummary")).to_contain_text("READY_FOR_FINALIZATION")
    page.locator("#operationFinalizeButton").click()
    expect(page.locator("#operationActionStatus")).to_contain_text("760123/1")
    expect(page.locator("#operationSummary")).to_contain_text("FINALIZED")

    state = page.evaluate("window.getOperationState()")
    assert state["version"] == 5
    assert state["workflow_state"] == "FINALIZED"
    calls = page.evaluate("window.getOperationCalls()")
    assert any(call["path"] == "/operations" and call["method"] == "POST" for call in calls)
    assert any(call["path"] == "/operations/101/finalize" for call in calls)
    assert page.evaluate("window.lastOperationError || null") is None
