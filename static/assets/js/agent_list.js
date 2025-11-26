

  document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Get all agent rows
    const agentRows = document.querySelectorAll('.agent-row');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const sortSelect = document.getElementById('sortSelect');
    const agentsTableBody = document.getElementById('agentsTableBody');
    const showingCount = document.getElementById('showingCount');
    const totalCount = document.getElementById('totalCount');
    const pagination = document.getElementById('pagination');
    
    // Pagination variables
    const rowsPerPage = 10;
    let currentPage = 1;
    let filteredRows = Array.from(agentRows);

    // Initialize
    updateStats();
    filterAndSortAgents();
    setupPagination();

    // Event listeners
    searchInput.addEventListener('input', filterAndSortAgents);
    statusFilter.addEventListener('change', filterAndSortAgents);
    sortSelect.addEventListener('change', filterAndSortAgents);

    // Action buttons event listeners
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const userId = this.getAttribute('data-user-id');
        viewAgentDetails(userId);
      });
    });

    document.querySelectorAll('.approve-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const userId = this.getAttribute('data-user-id');
        approveAgent(userId, this);
      });
    });

    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const userId = this.getAttribute('data-user-id');
        editAgent(userId);
      });
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const userId = this.getAttribute('data-user-id');
        deleteAgent(userId);
      });
    });

    // Export button
    document.getElementById('exportBtn').addEventListener('click', exportAgents);

    // Add agent button
    document.getElementById('addAgentBtn').addEventListener('click', addAgent);

    // Filter and sort function
    function filterAndSortAgents() {
      const searchTerm = searchInput.value.toLowerCase();
      const statusFilterValue = statusFilter.value;
      const sortValue = sortSelect.value;

      // Filter rows
      filteredRows = Array.from(agentRows).filter(row => {
        const name = row.getAttribute('data-name');
        const email = row.getAttribute('data-email');
        const phone = row.getAttribute('data-phone');
        const status = row.getAttribute('data-status');
        
        // Search filter
        const matchesSearch = searchTerm === '' || 
          name.includes(searchTerm) || 
          email.includes(searchTerm) || 
          phone.includes(searchTerm);
        
        // Status filter
        const matchesStatus = statusFilterValue === 'all' || status === statusFilterValue;
        
        return matchesSearch && matchesStatus;
      });

      // Sort rows
      filteredRows.sort((a, b) => {
        switch (sortValue) {
          case 'newest':
            return parseInt(b.getAttribute('data-date')) - parseInt(a.getAttribute('data-date'));
          case 'oldest':
            return parseInt(a.getAttribute('data-date')) - parseInt(b.getAttribute('data-date'));
          case 'name_asc':
            return a.getAttribute('data-name').localeCompare(b.getAttribute('data-name'));
          case 'name_desc':
            return b.getAttribute('data-name').localeCompare(a.getAttribute('data-name'));
          default:
            return 0;
        }
      });

      // Update display
      currentPage = 1;
      updateStats();
      setupPagination();
      displayPage(currentPage);
    }

    // Pagination functions
    function setupPagination() {
      const pageCount = Math.ceil(filteredRows.length / rowsPerPage);
      pagination.innerHTML = '';

      if (pageCount <= 1) return;

      // Previous button
      const prevLi = document.createElement('li');
      prevLi.className = `page-item ${currentPage === 1 ? 'disabled' : ''}`;
      prevLi.innerHTML = `<a class="page-link rounded-2" href="#" data-page="${currentPage - 1}">Previous</a>`;
      pagination.appendChild(prevLi);

      // Page numbers
      for (let i = 1; i <= pageCount; i++) {
        const li = document.createElement('li');
        li.className = `page-item ${currentPage === i ? 'active' : ''}`;
        li.innerHTML = `<a class="page-link rounded-2" href="#" data-page="${i}">${i}</a>`;
        pagination.appendChild(li);
      }

      // Next button
      const nextLi = document.createElement('li');
      nextLi.className = `page-item ${currentPage === pageCount ? 'disabled' : ''}`;
      nextLi.innerHTML = `<a class="page-link rounded-2" href="#" data-page="${currentPage + 1}">Next</a>`;
      pagination.appendChild(nextLi);

      // Add click event listeners to pagination links
      pagination.querySelectorAll('.page-link').forEach(link => {
        link.addEventListener('click', function(e) {
          e.preventDefault();
          const page = parseInt(this.getAttribute('data-page'));
          if (page && page !== currentPage) {
            currentPage = page;
            setupPagination();
            displayPage(currentPage);
          }
        });
      });
    }

    function displayPage(page) {
      // Hide all rows
      agentRows.forEach(row => row.classList.add('hidden'));
      
      // Show rows for current page
      const start = (page - 1) * rowsPerPage;
      const end = start + rowsPerPage;
      const pageRows = filteredRows.slice(start, end);
      
      pageRows.forEach(row => row.classList.remove('hidden'));
      
      // Update showing count
      showingCount.textContent = Math.min(end, filteredRows.length);
      totalCount.textContent = agentRows.length;

      // Show/hide no agents message
      const noAgentsRow = document.getElementById('noAgentsRow');
      if (noAgentsRow) {
        noAgentsRow.style.display = filteredRows.length === 0 ? '' : 'none';
      }
    }

    // Update statistics
    function updateStats() {
      const approvedCount = filteredRows.filter(row => row.getAttribute('data-approved') === 'true').length;
      const pendingCount = filteredRows.filter(row => row.getAttribute('data-approved') === 'false').length;
      
      document.getElementById('approvedAgents').textContent = approvedCount;
      document.getElementById('pendingAgents').textContent = pendingCount;
      document.getElementById('totalAgents').textContent = filteredRows.length;
    }

  
  function approveAgent(userId, button) {
    if (confirm('Are you sure you want to approve this agent?')) {

      // Disable button & show loader icon
      button.disabled = true;
      button.innerHTML = '<i class="bi bi-hourglass-split"></i>';

      // Send API call to backend
      fetch(`/approve-agent/${userId}/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          // ✅ Update the row visually
          const row = button.closest('.agent-row');
          row.setAttribute('data-status', 'approved');
          row.setAttribute('data-approved', 'true');
          
          // Update the status badge
          const statusBadge = row.querySelector('.agent-status');
          statusBadge.className = 'badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 rounded-pill px-3 py-2';
          statusBadge.innerHTML = '<i class="bi bi-check-circle me-1"></i> Approved';
          
          // Replace approve button with disabled one
          const approveBtn = row.querySelector('.approve-btn');
          if (approveBtn) {
            approveBtn.className = 'btn btn-sm btn-outline-secondary rounded-3';
            approveBtn.disabled = true;
            approveBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
            approveBtn.title = 'Already Approved';
            new bootstrap.Tooltip(approveBtn);
          }

          // Optional: refresh total stats
          if (typeof updateStats === "function") updateStats();

          // ✅ Toastify success message
          Toastify({
            text: data.message || "Agent approved successfully!",
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "linear-gradient(to right, #00b09b, #96c93d)",
          }).showToast();
        } else {
          showErrorToast("Failed to approve agent. Please try again.");
          button.disabled = false;
          button.innerHTML = '<i class="bi bi-check-lg"></i>';
        }
      })
      .catch(err => {
        console.error("Error approving agent:", err);
        showErrorToast("An error occurred while approving the agent.");
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check-lg"></i>';
      });
    }
  }

  // ✅ Toastify error helper
  function showErrorToast(message) {
    Toastify({
      text: message,
      duration: 3000,
      gravity: "top",
      position: "right",
      backgroundColor: "linear-gradient(to right, #ff5f6d, #ffc371)",
    }).showToast();
  }

  // ✅ Helper to get CSRF token
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

    function editAgent(userId) {
      alert(`Edit agent with ID: ${userId}`);
      // Implement edit functionality
    }

    function deleteAgent(userId) {
      if (confirm('Are you sure you want to delete this agent? This action cannot be undone.')) {
        // Simulate API call
        const row = document.querySelector(`.delete-btn[data-user-id="${userId}"]`).closest('.agent-row');
        row.style.opacity = '0.5';
        
        setTimeout(() => {
          row.remove();
          updateStats();
          filterAndSortAgents();
          alert('Agent deleted successfully!');
        }, 1000);
      }
    }

    function exportAgents() {
      alert('Exporting agents data...');
      // Implement export functionality
    }
  });


 class AgentsTable {
    constructor() {
        this.rows = Array.from(document.querySelectorAll('.agent-row'));
        this.tableBody = document.getElementById('agentsTableBody');
        this.pagination = document.getElementById('pagination');
        this.searchInput = document.getElementById('searchInput');
        this.statusFilter = document.getElementById('statusFilter');
        this.recordsPerPage = document.getElementById('recordsPerPage');
        this.showingCount = document.getElementById('showingCount');
        this.totalCount = document.getElementById('totalCount');
        
        this.currentPage = 1;
        this.recordsPerPageValue = parseInt(this.recordsPerPage.value);
        this.filteredRows = [...this.rows];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.updateDisplay();
        this.updateStats();
    }
    
    bindEvents() {
        this.searchInput.addEventListener('input', () => this.filterAndSort());
        this.statusFilter.addEventListener('change', () => this.filterAndSort());
        this.recordsPerPage.addEventListener('change', () => {
            this.recordsPerPageValue = parseInt(this.recordsPerPage.value);
            this.currentPage = 1;
            this.filterAndSort();
        });
    }
    
    filterAndSort() {
        const searchTerm = this.searchInput.value.toLowerCase();
        const statusFilter = this.statusFilter.value;
        
        // Filter rows
        this.filteredRows = this.rows.filter(row => {
            const name = row.dataset.name;
            const email = row.dataset.email;
            const phone = row.dataset.phone;
            const status = row.dataset.status;
            
            const matchesSearch = name.includes(searchTerm) || 
                               email.includes(searchTerm) || 
                               phone.includes(searchTerm);
            const matchesStatus = statusFilter === 'all' || status === statusFilter;
            
            return matchesSearch && matchesStatus;
        });
        
        // Sort by newest first (default)
        this.filteredRows.sort((a, b) => {
            return parseInt(b.dataset.date) - parseInt(a.dataset.date);
        });
        
        // Update display
        this.currentPage = 1;
        this.updateDisplay();
        this.updateStats();
    }
    
    updateDisplay() {
        // Hide all rows
        this.rows.forEach(row => row.classList.add('hidden'));
        
        // Calculate pagination
        const totalPages = Math.ceil(this.filteredRows.length / this.recordsPerPageValue);
        const startIndex = (this.currentPage - 1) * this.recordsPerPageValue;
        const endIndex = startIndex + this.recordsPerPageValue;
        const currentRows = this.filteredRows.slice(startIndex, endIndex);
        
        // Show current page rows
        currentRows.forEach(row => row.classList.remove('hidden'));
        
        // Update showing count
        this.showingCount.textContent = currentRows.length;
        this.totalCount.textContent = this.filteredRows.length;
        
        // Generate pagination
        this.generatePagination(totalPages);
        
        // Show/hide no agents row
        const noAgentsRow = document.getElementById('noAgentsRow');
        if (noAgentsRow) {
            noAgentsRow.style.display = this.filteredRows.length === 0 ? '' : 'none';
        }
    }
    
    generatePagination(totalPages) {
        this.pagination.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${this.currentPage === 1 ? 'disabled' : ''}`;
        prevLi.innerHTML = `
            <a class="page-link rounded-3" href="#" aria-label="Previous" ${this.currentPage === 1 ? 'tabindex="-1"' : ''}>
                <span aria-hidden="true">&laquo;</span>
            </a>
        `;
        prevLi.addEventListener('click', (e) => {
            e.preventDefault();
            if (this.currentPage > 1) {
                this.currentPage--;
                this.updateDisplay();
            }
        });
        this.pagination.appendChild(prevLi);
        
        // Page numbers
        const maxVisiblePages = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === this.currentPage ? 'active' : ''}`;
            pageLi.innerHTML = `<a class="page-link rounded-3" href="#">${i}</a>`;
            pageLi.addEventListener('click', (e) => {
                e.preventDefault();
                this.currentPage = i;
                this.updateDisplay();
            });
            this.pagination.appendChild(pageLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${this.currentPage === totalPages ? 'disabled' : ''}`;
        nextLi.innerHTML = `
            <a class="page-link rounded-3" href="#" aria-label="Next" ${this.currentPage === totalPages ? 'tabindex="-1"' : ''}>
                <span aria-hidden="true">&raquo;</span>
            </a>
        `;
        nextLi.addEventListener('click', (e) => {
            e.preventDefault();
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.updateDisplay();
            }
        });
        this.pagination.appendChild(nextLi);
    }
    
    updateStats() {
        // Update total leads in stats card based on filtered results
        const totalLeads = this.filteredRows.reduce((sum, row) => sum + parseInt(row.dataset.leads), 0);
        document.getElementById('totalLeads').textContent = totalLeads.toLocaleString();
        
        // Update approved and pending counts based on filtered results
        const approvedCount = this.filteredRows.filter(row => row.dataset.status === 'approved').length;
        const pendingCount = this.filteredRows.filter(row => row.dataset.status === 'pending').length;
        
        document.getElementById('approvedAgents').textContent = approvedCount;
        document.getElementById('pendingAgents').textContent = pendingCount;
        document.getElementById('totalAgents').textContent = this.filteredRows.length;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new AgentsTable();
    
    // Add export functionality
    document.getElementById('exportBtn').addEventListener('click', function() {
        // Implement export functionality here
        alert('Export functionality will be implemented here');
    });
    
    // Add approve agent functionality
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.dataset.userId;
            if (confirm('Are you sure you want to approve this agent?')) {
                // Implement approve API call here
                fetch(`/api/agents/${userId}/approve/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error approving agent');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error approving agent');
                });
            }
        });
    });
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});