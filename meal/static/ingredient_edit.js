// ingredient_edit.js

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('ingredient-modal');
    const closeModal = document.getElementById('close-modal');
    const addBtn = document.getElementById('add-ingredient-btn');
    const editBtns = document.getElementsByClassName('edit-btn');
    const deleteBtns = document.getElementsByClassName('delete-btn');
    const form = document.getElementById('ingredient-form');
    const modalTitle = document.getElementById('modal-title');
    let editingRow = null;

    // Open modal for add
    addBtn.onclick = function() {
        modalTitle.textContent = 'Add Ingredient';
        form.reset();
        editingRow = null;
        modal.style.display = 'block';
    };
    // Open modal for edit
    Array.from(editBtns).forEach(function(btn) {
        btn.onclick = function(e) {
            const row = e.target.closest('tr');
            editingRow = row;
            modalTitle.textContent = 'Edit Ingredient';
            document.getElementById('ingredient-name').value = row.children[0].textContent;
            document.getElementById('ingredient-quantity').value = row.children[1].textContent;
            document.getElementById('ingredient-unit').value = row.children[2].textContent;
            document.getElementById('ingredient-expiry').value = row.children[3].textContent;
            modal.style.display = 'block';
        };
    });
    // Delete ingredient
    Array.from(deleteBtns).forEach(function(btn) {
        btn.onclick = function(e) {
            const row = e.target.closest('tr');
            const name = row.children[0].textContent;
            if (confirm('Delete ingredient ' + name + '?')) {
                fetch('/api/pantry/ingredient/' + encodeURIComponent(name), {
                    method: 'DELETE'
                }).then(res => {
                    if (res.ok) row.remove();
                    else alert('Delete failed');
                });
            }
        };
    });
    // Close modal
    closeModal.onclick = function() {
        modal.style.display = 'none';
    };
    // Save (add/edit) ingredient
    form.onsubmit = function(e) {
        e.preventDefault();
        const data = {
            name: document.getElementById('ingredient-name').value,
            default_quantity: document.getElementById('ingredient-quantity').value,
            unit: document.getElementById('ingredient-unit').value,
            data_expirare: document.getElementById('ingredient-expiry').value
        };
        let method = editingRow ? 'PUT' : 'POST';
        let url = '/api/pantry/ingredient';
        if (editingRow) url += '/' + encodeURIComponent(editingRow.children[0].textContent);
        fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        }).then(res => res.json()).then(result => {
            if (result.success) {
                location.reload();
            } else {
                alert('Save failed: ' + (result.error || 'Unknown error'));
            }
        });
    };
});

