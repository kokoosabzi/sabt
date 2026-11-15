from pathlib import Path

from playwright.sync_api import expect


ROOT = Path(__file__).resolve().parents[1]
INDEX_SOURCE = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
NAV_BLOCK = INDEX_SOURCE.split("const navToggle=$('navToggle'),navHost=$('sabtNav');", 1)[1].split("$('loadButton')", 1)[0]
NAV_SCRIPT = (
    "const $=id=>document.getElementById(id);"
    "const navToggle=$('navToggle'),navHost=$('sabtNav');"
    "function navigateToPage(){}"
    + NAV_BLOCK
)


def test_sabt_mobile_navigation_escape_outside_click_and_focus_return(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.set_content("""<!doctype html>
    <html lang="fa" dir="rtl"><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
      body{margin:0;min-height:100vh}
      header{height:64px;display:flex;align-items:center}
      #sabtNav{display:none;position:fixed;right:0;top:64px;width:280px;height:calc(100vh - 64px);background:#fff}
      #sabtNav.is-open{display:flex;flex-direction:column}
    </style></head><body>
      <header><button id="navToggle" type="button" aria-controls="sabtNav" aria-expanded="false">منو</button></header>
      <nav id="sabtNav"><button data-page="dashboard">داشبورد</button><button data-page="workflow">گزارش گردش کار</button></nav>
      <main><button id="outside">بیرون منو</button></main>
    </body></html>""")
    page.add_script_tag(content=NAV_SCRIPT)

    toggle = page.locator("#navToggle")
    nav = page.locator("#sabtNav")
    expect(toggle).to_be_visible()
    expect(nav).to_be_hidden()

    toggle.click()
    expect(nav).to_be_visible()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expect(page.locator('#sabtNav button').first).to_be_focused()

    page.keyboard.press("Escape")
    expect(nav).to_be_hidden()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(toggle).to_be_focused()

    toggle.click()
    page.mouse.click(5, 700)
    expect(nav).to_be_hidden()
    expect(toggle).to_have_attribute("aria-expanded", "false")

    toggle.click()
    page.get_by_role("button", name="گزارش گردش کار").click()
    expect(nav).to_be_hidden()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(toggle).to_be_focused()


def test_sabt_workspace_tab_keyboard_focus_survives_closing_inactive_tab(page):
    script = (ROOT / "app/static/koko-workspace-tabs.js").read_text(encoding="utf-8")
    page.set_content("""<!doctype html><html lang="fa" dir="rtl"><body>
      <nav><button data-page="dashboard">داشبورد</button>
      <button data-page="reports" class="active">گزارش‌ها</button></nav>
      <div id="koko-workspace-tabs" role="group" aria-label="صفحه‌های باز"></div>
    </body></html>""")
    page.evaluate("""() => sessionStorage.setItem(
      'sabt.workspace.tabs.v1',
      JSON.stringify([{id: 'dashboard'}, {id: 'reports'}])
    )""")
    page.add_script_tag(content=script)
    reports = page.locator('#koko-workspace-tabs .koko-tab[data-page="reports"] button').first
    expect(reports).to_be_visible()
    close_dashboard = page.get_by_role("button", name="بستن داشبورد")
    close_dashboard.focus()
    page.keyboard.press("Enter")
    expect(page.locator('#koko-workspace-tabs .koko-tab')).to_have_count(1)
    expect(page.locator('#koko-workspace-tabs .koko-tab button').first).to_be_focused()
    expect(page.locator('#koko-workspace-tabs .koko-tab.active')).to_contain_text("گزارش‌ها")
