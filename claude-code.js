const commandSearch = document.querySelector('#command-search');
const commandRows = [...document.querySelectorAll('.command-group tbody tr')];
commandSearch?.addEventListener('input', () => {
  const query = commandSearch.value.trim().toLowerCase();
  let count = 0;
  document.querySelectorAll('.command-group').forEach(group => {
    let visible = 0;
    group.querySelectorAll('tbody tr').forEach(row => {
      row.hidden = !row.textContent.toLowerCase().includes(query);
      if (!row.hidden) { count++; visible++; }
    });
    group.hidden = visible === 0;
  });
  document.querySelector('#command-count').textContent = `顯示 ${count} / ${commandRows.length} 個參考條目`;
  document.querySelector('#command-empty').hidden = count > 0;
});
document.addEventListener('keydown', event => {
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey &&
      !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName) &&
      !document.activeElement.isContentEditable) {
    event.preventDefault();
    commandSearch?.focus();
  }
});
