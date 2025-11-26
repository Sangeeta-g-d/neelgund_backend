document.addEventListener('DOMContentLoaded', () => {
  const projectRows = Array.from(document.querySelectorAll('.project-row'));
  const searchInput = document.getElementById('searchInput');
  const statusFilter = document.getElementById('statusFilter');
  const typeFilter = document.getElementById('typeFilter');
  const sortSelect = document.getElementById('sortSelect');
  const recordsPerPageSelect = document.getElementById('recordsPerPage');
  const showingCount = document.getElementById('showingCount');
  const totalCount = document.getElementById('totalCount');
  const pagination = document.getElementById('pagination');
  const noProjectsRow = document.getElementById('noProjectsRow');
  const exportBtn = document.getElementById('exportBtn');

  if (!projectRows.length) {
    if (totalCount) {
      totalCount.textContent = '0';
    }
    return;
  }

  let rows = [...projectRows];
  let filteredRows = [...rows];
  let currentPage = 1;
  let recordsPerPage = parseInt(recordsPerPageSelect?.value || '10', 10);

  totalCount.textContent = rows.length;

  const filterAndSort = () => {
    const searchTerm = searchInput?.value.trim().toLowerCase() || '';
    const statusValue = statusFilter?.value || 'all';
    const typeValue = typeFilter?.value || 'all';
    const sortValue = sortSelect?.value || 'newest';

    filteredRows = rows.filter(row => {
      const name = row.dataset.name || '';
      const location = row.dataset.location || '';
      const type = row.dataset.type || '';
      const status = row.dataset.status || 'ongoing';

      const matchesSearch =
        !searchTerm ||
        name.includes(searchTerm) ||
        location.includes(searchTerm) ||
        type.includes(searchTerm);

      const matchesStatus = statusValue === 'all' || status === statusValue;
      const matchesType = typeValue === 'all' || type === typeValue;

      return matchesSearch && matchesStatus && matchesType;
    });

    filteredRows.sort((a, b) => {
      switch (sortValue) {
        case 'oldest':
          return (parseInt(a.dataset.date || '0', 10) || 0) -
                 (parseInt(b.dataset.date || '0', 10) || 0);
        case 'name_asc':
          return (a.dataset.name || '').localeCompare(b.dataset.name || '');
        case 'name_desc':
          return (b.dataset.name || '').localeCompare(a.dataset.name || '');
        case 'plots_high':
          return (parseInt(b.dataset.plots || '0', 10) || 0) -
                 (parseInt(a.dataset.plots || '0', 10) || 0);
        case 'plots_low':
          return (parseInt(a.dataset.plots || '0', 10) || 0) -
                 (parseInt(b.dataset.plots || '0', 10) || 0);
        case 'newest':
        default:
          return (parseInt(b.dataset.date || '0', 10) || 0) -
                 (parseInt(a.dataset.date || '0', 10) || 0);
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
      showingCount.textContent = pageRows.length
        ? Math.min(end, filteredRows.length)
        : 0;
    }
    if (totalCount) {
      totalCount.textContent = rows.length;
    }

    updateStats();
    toggleEmptyState();
    buildPagination();
  };

  const toggleEmptyState = () => {
    if (!noProjectsRow) return;
    noProjectsRow.style.display = filteredRows.length ? 'none' : '';
  };

  const buildPagination = () => {
    if (!pagination) return;
    const pageCount = Math.ceil(filteredRows.length / recordsPerPage);
    pagination.innerHTML = '';
    if (pageCount <= 1) return;

    const createPageItem = (label, page, disabled = false, active = false) => {
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

    pagination.appendChild(createPageItem('Previous', Math.max(1, currentPage - 1), currentPage === 1));

    for (let page = 1; page <= pageCount; page += 1) {
      pagination.appendChild(createPageItem(page, page, false, currentPage === page));
    }

    pagination.appendChild(createPageItem('Next', Math.min(pageCount, currentPage + 1), currentPage === pageCount));
  };

  const updateStats = () => {
    const statusTotals = filteredRows.reduce(
      (acc, row) => {
        const status = row.dataset.status || 'ongoing';
        if (status === 'ready_to_move') acc.ready += 1;
        else if (status === 'under_construction') acc.construction += 1;
        else if (status === 'upcoming') acc.upcoming += 1;
        acc.total += 1;
        return acc;
      },
      { total: 0, ready: 0, construction: 0, upcoming: 0 }
    );

    const totalEl = document.getElementById('totalProjects');
    const readyEl = document.getElementById('readyProjects');
    const constructionEl = document.getElementById('constructionProjects');
    const upcomingEl = document.getElementById('upcomingProjects');

    if (totalEl) totalEl.textContent = rows.length;
    if (readyEl) readyEl.textContent = statusTotals.ready;
    if (constructionEl) constructionEl.textContent = statusTotals.construction;
    if (upcomingEl) upcomingEl.textContent = statusTotals.upcoming;
  };

  const handleRecordsChange = () => {
    recordsPerPage = parseInt(recordsPerPageSelect.value, 10) || 10;
    currentPage = 1;
    render();
  };

  const handleExport = () => {
    if (!filteredRows.length) {
      window.alert('No projects to export with current filters.');
      return;
    }
    window.alert('Export functionality coming soon.');
  };

  const attachDeleteHandlers = () => {
    document.querySelectorAll('.delete-project-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const projectId = btn.dataset.projectId;
        if (!projectId) return;
        if (!window.confirm('Delete this project? This action cannot be undone.')) {
          return;
        }
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

        fetch(`/delete-project/${projectId}/`, {
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
            if (data.success) {
              const row = btn.closest('tr');
              if (row) {
                row.remove();
                rows = rows.filter(r => r !== row);
                filterAndSort();
              }
            }
            if (data.message) {
              window.alert(data.message);
            }
          })
          .catch(err => {
            console.error('Error deleting project:', err);
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash"></i>';
            window.alert('An error occurred while deleting the project.');
          });
      });
    });
  };

  if (searchInput) searchInput.addEventListener('input', filterAndSort);
  if (statusFilter) statusFilter.addEventListener('change', filterAndSort);
  if (typeFilter) typeFilter.addEventListener('change', filterAndSort);
  if (sortSelect) sortSelect.addEventListener('change', filterAndSort);
  if (recordsPerPageSelect) recordsPerPageSelect.addEventListener('change', handleRecordsChange);
  if (exportBtn) exportBtn.addEventListener('click', handleExport);

  attachDeleteHandlers();
  filterAndSort();
});

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}


