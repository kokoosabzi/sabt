from pathlib import Path

from playwright.sync_api import expect


ROOT = Path(__file__).resolve().parents[1]
INDEX_SOURCE = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
FUNCTION_START = INDEX_SOURCE.index("  async function initializeProjects(){")
FUNCTION_END = INDEX_SOURCE.index("  function period()", FUNCTION_START)
INITIALIZE_PROJECTS_SOURCE = INDEX_SOURCE[FUNCTION_START:FUNCTION_END]


def test_portal_contains_first_project_setup_fields():
    assert 'id="projectSetupForm"' in INDEX_SOURCE
    assert 'id="setupProjectName"' in INDEX_SOURCE
    assert 'id="setupProjectCode"' in INDEX_SOURCE
    assert 'id="setupContractCode"' in INDEX_SOURCE
    assert 'id="setupProjectTimezone"' in INDEX_SOURCE


def test_first_run_project_setup_is_shown_only_when_user_has_no_projects(page):
    page.set_content("""<!doctype html><html lang="fa" dir="rtl"><head><style>.hidden{display:none!important}</style></head><body>
      <section id="projectSetupPanel" class="hidden"></section>
      <div id="appWorkspace" class="layout"></div>
      <input id="projectId" value="1">
    </body></html>""")
    page.add_script_tag(content="""
      const $ = id => document.getElementById(id);
      let contextProjectId = 7;
      let defaultsInitialized = true;
      let response = {items: []};
      async function api(){ return response; }
    """ + INITIALIZE_PROJECTS_SOURCE + """
      window.setProjectResponse = value => { response = value; };
      window.getProjectState = () => ({contextProjectId, defaultsInitialized});
      window.initializeProjects = initializeProjects;
    """)

    result = page.evaluate("async () => await window.initializeProjects()")
    assert result is False
    expect(page.locator("#projectSetupPanel")).to_be_visible()
    expect(page.locator("#appWorkspace")).to_be_hidden()

    page.evaluate("window.setProjectResponse({items:[{id:9,code:'first',name:'پروژه اول'}]})")
    result = page.evaluate("async () => await window.initializeProjects()")
    assert result is True
    expect(page.locator("#projectSetupPanel")).to_be_hidden()
    expect(page.locator("#appWorkspace")).to_be_visible()
    assert page.locator("#projectId").input_value() == "9"
    assert page.evaluate("window.getProjectState()") == {
        "contextProjectId": None,
        "defaultsInitialized": False,
    }
