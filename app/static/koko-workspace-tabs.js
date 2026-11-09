/* SABT workspace tabs over the existing page navigation. */
(() => {
  'use strict';

  const storageKey = 'sabt.workspace.tabs.v1';
  const host = document.getElementById('koko-workspace-tabs');
  if (!host) return;
  host.dataset.workspaceTabsVersion = 'delegated-1';

  const buttons = () => [...document.querySelectorAll('nav button[data-page]')];
  const currentPage = () => buttons().find(button => button.classList.contains('active'))?.dataset.page;
  const labelFor = id => buttons().find(button => button.dataset.page === id)?.textContent.trim() || id;
  const save = () => {
    try { sessionStorage.setItem(storageKey, JSON.stringify(tabs.slice(-8))); } catch (_) {}
  };

  let tabs = [];
  try {
    const stored = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
    if (Array.isArray(stored)) {
      tabs = stored
        .filter(tab => tab && typeof tab.id === 'string' && buttons().some(button => button.dataset.page === tab.id))
        .map(tab => ({ id: tab.id, label: labelFor(tab.id) }))
        .slice(-8);
    }
  } catch (_) {}

  const render = () => {
    host.replaceChildren();
    const activeId = currentPage();
    tabs.forEach(tab => {
      const item = document.createElement('div');
      item.className = 'koko-tab' + (tab.id === activeId ? ' active' : '');
      item.dataset.page = tab.id;

      const activate = document.createElement('button');
      activate.type = 'button';
      activate.textContent = tab.label;
      activate.setAttribute('aria-current', tab.id === activeId ? 'page' : 'false');
      activate.addEventListener('click', () => {
        buttons().find(button => button.dataset.page === tab.id)?.click();
      });

      const close = document.createElement('button');
      close.type = 'button';
      close.className = 'koko-tab-close';
      close.textContent = '×';
      close.dataset.closeTab = tab.id;
      close.setAttribute('aria-label', 'بستن ' + tab.label);

      item.append(activate, close);
      host.append(item);
    });
  };

  const sync = () => {
    const activeId = currentPage();
    if (!activeId) return;
    if (!tabs.some(tab => tab.id === activeId)) {
      tabs.push({ id: activeId, label: labelFor(activeId) });
    }
    tabs = tabs.slice(-8);
    save();
    render();
  };

  host.addEventListener('click', event => {
    const closeButton = event.target.closest('button[data-close-tab]');
    if (!closeButton || !host.contains(closeButton)) return;

    const id = closeButton.dataset.closeTab;
    host.dataset.closeDebug = id + '|' + String(currentPage());
    const index = tabs.findIndex(tab => tab.id === id);
    if (index < 0) return;

    const wasActive = currentPage() === id;
    const remaining = tabs.filter(tab => tab.id !== id);
    const next = remaining[Math.min(index, remaining.length - 1)];
    tabs = remaining;
    save();

    if (wasActive) {
      const targetId = next?.id || 'dashboard';
      const target = buttons().find(button => button.dataset.page === targetId);
      if (typeof window.sabtNavigatePage === 'function') {
        window.sabtNavigatePage(targetId);
      } else {
        target?.click();
      }
    }

    render();
  });

  document.addEventListener('click', event => {
    if (event.target.closest('nav button[data-page]') || event.target.closest('.koko-sabt-actions button[data-page]')) {
      setTimeout(sync, 0);
    }
  });

  new MutationObserver(sync).observe(document.body, {
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  });

  sync();
})();
