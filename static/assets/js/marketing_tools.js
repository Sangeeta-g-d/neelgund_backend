document.addEventListener('DOMContentLoaded', () => {
  // Tab switching
  const tabButtons = document.querySelectorAll('#marketingTabs .nav-link');
  const panes = document.querySelectorAll('.tab-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetSelector = btn.getAttribute('data-target');
      if (!targetSelector) return;
      const targetPane = document.querySelector(targetSelector);
      if (!targetPane) return;

      tabButtons.forEach(b => b.classList.remove('active'));
      panes.forEach(p => {
        p.classList.remove('show', 'active');
      });

      btn.classList.add('active');
      targetPane.classList.add('show', 'active');
    });
  });

  // Delete brochure
  document.querySelectorAll('.delete-brochure-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const projectId = btn.dataset.projectId;
      if (!projectId) return;
      if (!window.confirm('Delete this brochure? This action cannot be undone.')) return;

      btn.disabled = true;
      btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

      fetch(`/projects/${projectId}/delete-brochure/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            // Reload page after successful delete
            window.location.reload();
          } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash-fill"></i>';

            if (data.message && window.Toastify) {
              Toastify({
                text: data.message,
                duration: 3000,
                gravity: 'top',
                position: 'right',
                backgroundColor: 'linear-gradient(to right, #ff5f6d, #ffc371)'
              }).showToast();
            } else if (data.message) {
              window.alert(data.message);
            }
          }
        })
        .catch(err => {
          console.error('Error deleting brochure:', err);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-trash-fill"></i>';
          if (window.Toastify) {
            Toastify({
              text: 'Failed to delete brochure.',
              duration: 3000,
              gravity: 'top',
              position: 'right',
              backgroundColor: 'linear-gradient(to right, #ff5f6d, #ffc371)'
            }).showToast();
          } else {
            window.alert('Failed to delete brochure.');
          }
        });
    });
  });

  // Delete map layout
  document.querySelectorAll('.delete-map-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const projectId = btn.dataset.projectId;
      if (!projectId) return;
      if (!window.confirm('Delete this map layout? This action cannot be undone.')) return;

      btn.disabled = true;
      btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

      fetch(`/projects/${projectId}/delete-map-layout/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            // Reload page after successful delete
            window.location.reload();
          } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-trash-fill"></i>';

            if (data.message && window.Toastify) {
              Toastify({
                text: data.message,
                duration: 3000,
                gravity: 'top',
                position: 'right',
                backgroundColor: 'linear-gradient(to right, #ff5f6d, #ffc371)'
              }).showToast();
            } else if (data.message) {
              window.alert(data.message);
            }
          }
        })
        .catch(err => {
          console.error('Error deleting map layout:', err);
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-trash-fill"></i>';
          if (window.Toastify) {
            Toastify({
              text: 'Failed to delete map layout.',
              duration: 3000,
              gravity: 'top',
              position: 'right',
              backgroundColor: 'linear-gradient(to right, #ff5f6d, #ffc371)'
            }).showToast();
          } else {
            window.alert('Failed to delete map layout.');
          }
        });
    });
  });
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



