document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Get all agent rows
    const agentRows = document.querySelectorAll('.agent-row');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const recordsPerPage = document.getElementById('recordsPerPage');
    const showingCount = document.getElementById('showingCount');
    const totalCount = document.getElementById('totalCount');
    const pagination = document.getElementById('pagination');
    
    // Pagination variables
    let rowsPerPage = parseInt(recordsPerPage.value);
    let currentPage = 1;
    let filteredRows = Array.from(agentRows);

    // Initialize
    updateStats();
    filterAndSortAgents();
    setupPagination();

    // Event listeners
    searchInput.addEventListener('input', filterAndSortAgents);
    statusFilter.addEventListener('change', filterAndSortAgents);
    recordsPerPage.addEventListener('change', function() {
        rowsPerPage = parseInt(this.value);
        currentPage = 1;
        filterAndSortAgents();
    });

    // Approve button functionality
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            approveAgent(userId, this);
        });
    });

    // Delete button functionality
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            deleteAgent(userId);
        });
    });

    // Filter function
    function filterAndSortAgents() {
        const searchTerm = searchInput.value.toLowerCase();
        const statusFilterValue = statusFilter.value;

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

        // Sort by newest first (default)
        filteredRows.sort((a, b) => {
            return parseInt(b.getAttribute('data-date')) - parseInt(a.getAttribute('data-date'));
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
        totalCount.textContent = filteredRows.length;

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
        
        // Update total leads
        const totalLeads = filteredRows.reduce((sum, row) => {
            return sum + parseInt(row.getAttribute('data-leads') || 0);
        }, 0);
        document.getElementById('totalLeads').textContent = totalLeads;
    }

    // Approve agent function
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
                    // Update the row visually
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

                    // Update stats
                    updateStats();

                    // Show success message
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

    // Error toast helper
    function showErrorToast(message) {
        Toastify({
            text: message,
            duration: 3000,
            gravity: "top",
            position: "right",
            backgroundColor: "linear-gradient(to right, #ff5f6d, #ffc371)",
        }).showToast();
    }

    // Helper to get CSRF token
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

    // Delete agent function
    function deleteAgent(userId) {
        if (confirm('Are you sure you want to delete this agent? This action cannot be undone.')) {
            // You can implement the actual delete functionality here
            console.log('Delete agent with ID:', userId);
            alert('Delete functionality would be implemented here');
        }
    }
});