document.addEventListener('DOMContentLoaded', () => {
  const leadRows = Array.from(document.querySelectorAll('.lead-row'));
  const searchInput = document.getElementById('searchInput');
  const statusFilter = document.getElementById('statusFilter');
  const sortSelect = document.getElementById('sortSelect');
  const recordsPerPageSelect = document.getElementById('recordsPerPage');
  const showingCount = document.getElementById('showingCount');
  const totalCount = document.getElementById('totalCount');
  const pagination = document.getElementById('pagination');
  const noLeadsRow = document.getElementById('noLeadsRow');
  const exportBtn = document.getElementById('exportBtn');

  if (!leadRows.length) {
    if (totalCount) totalCount.textContent = '0';
    return;
  }

  let rows = [...leadRows];
  let filteredRows = [...rows];
  let currentPage = 1;
  let recordsPerPage = parseInt(recordsPerPageSelect?.value || '10', 10);

  if (totalCount) totalCount.textContent = rows.length;

  const filterAndSort = () => {
    const term = (searchInput?.value || '').trim().toLowerCase();
    const statusValue = statusFilter?.value || 'all';
    const sortValue = sortSelect?.value || 'newest';

    filteredRows = rows.filter(row => {
      const { name = '', email = '', phone = '', city = '', agent = '', status = '' } = row.dataset;

      const matchesSearch =
        term === '' ||
        name.includes(term) ||
        email.includes(term) ||
        phone.includes(term) ||
        city.includes(term) ||
        agent.includes(term);

      const matchesStatus = statusValue === 'all' || status === statusValue;
      return matchesSearch && matchesStatus;
    });

    filteredRows.sort((a, b) => {
      const dateA = parseInt(a.dataset.date || '0', 10) || 0;
      const dateB = parseInt(b.dataset.date || '0', 10) || 0;
      const nameA = a.dataset.name || '';
      const nameB = b.dataset.name || '';
      const budgetA = parseFloat(a.dataset.budget || '0') || 0;
      const budgetB = parseFloat(b.dataset.budget || '0') || 0;

      switch (sortValue) {
        case 'oldest':
          return dateA - dateB;
        case 'name_asc':
          return nameA.localeCompare(nameB);
        case 'name_desc':
          return nameB.localeCompare(nameA);
        case 'budget_high':
          return budgetB - budgetA;
        case 'budget_low':
          return budgetA - budgetB;
        case 'newest':
        default:
          return dateB - dateA;
      }
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
      const showing = filteredRows.length ? Math.min(end, filteredRows.length) : 0;
      showingCount.textContent = showing;
    }
    if (totalCount) totalCount.textContent = rows.length;

    toggleEmptyState();
    updateStats();
    buildPagination();
  };

  const toggleEmptyState = () => {
    if (!noLeadsRow) return;
    noLeadsRow.style.display = filteredRows.length ? 'none' : '';
  };

  const buildPagination = () => {
    if (!pagination) return;
    pagination.innerHTML = '';
    const pageCount = Math.ceil(filteredRows.length / recordsPerPage);
    if (pageCount <= 1) return;

    const createItem = (label, page, disabled = false, active = false) => {
      const li = document.createElement('li');
      li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`.trim();
      const a = document.createElement('a');
      a.href = '#';
      a.className = 'page-link rounded-2';
      a.textContent = label;
      a.addEventListener('click', evt => {
        evt.preventDefault();
        if (disabled || page === currentPage) return;
        currentPage = page;
        render();
      });
      li.appendChild(a);
      return li;
    };

    pagination.appendChild(createItem('Previous', Math.max(1, currentPage - 1), currentPage === 1));
    for (let page = 1; page <= pageCount; page += 1) {
      pagination.appendChild(createItem(page, page, false, currentPage === page));
    }
    pagination.appendChild(createItem('Next', Math.min(pageCount, currentPage + 1), currentPage === pageCount));
  };

  const updateStats = () => {
    const totals = filteredRows.reduce(
      (acc, row) => {
        const status = row.dataset.status || 'new';
        if (status === 'new') acc.new += 1;
        else if (status === 'in_progress') acc.progress += 1;
        else if (status === 'closed') acc.closed += 1;
        acc.total += 1;
        return acc;
      },
      { total: 0, new: 0, progress: 0, closed: 0 }
    );

    const totalEl = document.getElementById('totalLeads');
    const newEl = document.getElementById('newLeads');
    const progressEl = document.getElementById('inProgressLeads');
    const closedEl = document.getElementById('closedLeads');

    if (totalEl) totalEl.textContent = rows.length;
    if (newEl) newEl.textContent = totals.new;
    if (progressEl) progressEl.textContent = totals.progress;
    if (closedEl) closedEl.textContent = totals.closed;
  };

  const handleRecordsChange = () => {
    recordsPerPage = parseInt(recordsPerPageSelect.value, 10) || 10;
    currentPage = 1;
    render();
  };

  const handleExport = () => {
    if (!filteredRows.length) {
      window.alert('No leads to export with the current filters.');
      return;
    }
    window.alert('Export functionality will be added soon.');
  };

  const attachDeleteHandlers = () => {
    document.querySelectorAll('.delete-lead-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const leadId = btn.dataset.leadId;
        if (!leadId) return;
        if (!window.confirm('Are you sure you want to delete this lead?')) return;

        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

        fetch(`/delete-lead/${leadId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
          .then(res => res.json())
          .then(data => {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash"></i>';

            if (data.message && window.Toastify) {
              Toastify({
                text: data.message,
                duration: 3000,
                gravity: 'top',
                position: 'right',
                backgroundColor: data.success
                  ? 'linear-gradient(to right, #00b09b, #96c93d)'
                  : 'linear-gradient(to right, #ff5f6d, #ffc371)'
              }).showToast();
            } else if (data.message) {
              window.alert(data.message);
            }

            if (data.success) {
              const row = document.getElementById(`lead-row-${leadId}`);
              if (row) {
                row.remove();
                rows = rows.filter(r => r !== row);
                filterAndSort();
              }
            }
          })
          .catch(err => {
            console.error('Failed to delete lead:', err);
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash"></i>';
            if (window.Toastify) {
              Toastify({
                text: '❌ Something went wrong!',
                duration: 3000,
                gravity: 'top',
                position: 'right',
                backgroundColor: 'linear-gradient(to right, #ff5f6d, #ffc371)'
              }).showToast();
            } else {
              window.alert('Something went wrong while deleting the lead.');
            }
          });
      });
    });
  };

  if (searchInput) searchInput.addEventListener('input', filterAndSort);
  if (statusFilter) statusFilter.addEventListener('change', filterAndSort);
  if (sortSelect) sortSelect.addEventListener('change', filterAndSort);
  if (recordsPerPageSelect) recordsPerPageSelect.addEventListener('change', handleRecordsChange);
  if (exportBtn) exportBtn.addEventListener('click', handleExport);

  attachDeleteHandlers();
  filterAndSort();
});

function getCookie(name) {
  const decoded = decodeURIComponent(document.cookie || '');
  const parts = decoded.split(';');
  for (const part of parts) {
    const [key, value] = part.trim().split('=');
    if (key === name) return value;
  }
  return null;
}


