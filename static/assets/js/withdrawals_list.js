document.addEventListener('DOMContentLoaded', () => {
  const rows = Array.from(document.querySelectorAll('.withdrawal-row'));
  const searchInput = document.getElementById('searchInput');
  const statusFilter = document.getElementById('statusFilter');
  const recordsPerPageSelect = document.getElementById('recordsPerPage');
  const showingCount = document.getElementById('showingCount');
  const totalCount = document.getElementById('totalCount');
  const pagination = document.getElementById('pagination');
  const noRequestsRow = document.getElementById('noRequestsRow');
  const exportBtn = document.getElementById('exportBtn');

  if (!rows.length) {
    if (totalCount) totalCount.textContent = '0';
    return;
  }

  let filteredRows = [...rows];
  let currentPage = 1;
  let recordsPerPage = parseInt(recordsPerPageSelect?.value || '10', 10);

  const filterRows = () => {
    const term = (searchInput?.value || '').trim().toLowerCase();
    const statusValue = statusFilter?.value || 'all';

    filteredRows = rows.filter(row => {
      const agent = row.dataset.agent || '';
      const project = row.dataset.project || '';
      const amount = row.dataset.amount || '';
      const status = row.dataset.status || 'pending';

      const matchesSearch =
        !term ||
        agent.includes(term) ||
        project.includes(term) ||
        amount.includes(term);

      const matchesStatus = statusValue === 'all' || status === statusValue;

      return matchesSearch && matchesStatus;
    });

    currentPage = 1;
    render();
  };

  const render = () => {
    rows.forEach(row => row.classList.add('hidden'));

    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    const pageRows = filteredRows.slice(start, end);

    pageRows.forEach(row => row.classList.remove('hidden'));

    if (showingCount) {
      showingCount.textContent = filteredRows.length ? Math.min(end, filteredRows.length) : 0;
    }
    if (totalCount) {
      totalCount.textContent = rows.length;
    }

    toggleEmptyState();
    updateStats();
    buildPagination();
  };

  const toggleEmptyState = () => {
    if (!noRequestsRow) return;
    noRequestsRow.style.display = filteredRows.length ? 'none' : '';
  };

  const buildPagination = () => {
    if (!pagination) return;
    pagination.innerHTML = '';

    const pageCount = Math.ceil(filteredRows.length / recordsPerPage);
    if (pageCount <= 1) return;

    const createPageItem = (label, page, disabled = false, active = false) => {
      const li = document.createElement('li');
      li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`.trim();
      const link = document.createElement('a');
      link.href = '#';
      link.className = 'page-link rounded-2';
      link.textContent = label;
      link.addEventListener('click', evt => {
        evt.preventDefault();
        if (disabled || page === currentPage) return;
        currentPage = page;
        render();
      });
      li.appendChild(link);
      return li;
    };

    pagination.appendChild(createPageItem('Previous', Math.max(1, currentPage - 1), currentPage === 1));

    for (let i = 1; i <= pageCount; i += 1) {
      pagination.appendChild(createPageItem(i, i, false, currentPage === i));
    }

    pagination.appendChild(createPageItem('Next', Math.min(pageCount, currentPage + 1), currentPage === pageCount));
  };

  const updateStats = () => {
    const totals = filteredRows.reduce(
      (acc, row) => {
        const status = row.dataset.status || 'pending';
        if (status === 'pending') acc.pending += 1;
        if (status === 'approved') acc.approved += 1;
        acc.total += 1;
        return acc;
      },
      { total: 0, pending: 0, approved: 0 }
    );

    const totalEl = document.getElementById('totalRequests');
    const pendingEl = document.getElementById('pendingRequests');
    const approvedEl = document.getElementById('approvedRequests');

    if (totalEl) totalEl.textContent = rows.length;
    if (pendingEl) pendingEl.textContent = totals.pending;
    if (approvedEl) approvedEl.textContent = totals.approved;
  };

  const handleRecordsChange = () => {
    recordsPerPage = parseInt(recordsPerPageSelect.value, 10) || 10;
    currentPage = 1;
    render();
  };

  const handleExport = () => {
    if (!filteredRows.length) {
      window.alert('No requests to export for the current filters.');
      return;
    }
    window.alert('Export functionality will be implemented soon.');
  };

  if (searchInput) searchInput.addEventListener('input', filterRows);
  if (statusFilter) statusFilter.addEventListener('change', filterRows);
  if (recordsPerPageSelect) recordsPerPageSelect.addEventListener('change', handleRecordsChange);
  if (exportBtn) exportBtn.addEventListener('click', handleExport);

  filterRows();
});


