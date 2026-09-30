(() => {
  const form = document.querySelector('form[data-student-search-url]');
  const rowsContainer = document.querySelector('#payment-request-rows');
  const batchItemsInput = document.querySelector('#batch-items');
  const total = document.querySelector('#request-total');
  const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
  let rowIndex = 0;

  function updateTotal() {
    const amount = [...rowsContainer.querySelectorAll('.payment-request-row')]
      .reduce((sum, row) => {
        const rowAmount = Number(row.querySelector('input[name="amount"]').value) || 0;
        const periodCount = row.querySelectorAll('input[name="payment_period_name"]:checked').length;
        return sum + rowAmount * periodCount;
      }, 0);
    total.textContent = `${new Intl.NumberFormat('vi-VN').format(amount)} VNĐ`;
  }

  function initializeRow(row) {
    const studentInput = row.querySelector('input[name="student_name"]');
    const studentIdInput = row.querySelector('input[name="student_id"]');
    const classroomInput = row.querySelector('input[name="classroom_name"]');
    const enrollmentInput = row.querySelector('input[name="enrollment"]');
    const teacherInput = row.querySelector('input[name="teacher_name"]');
    const teacherChoice = row.querySelector('.teacher-choice');
    const subjectInput = row.querySelector('input[name="subject_name"]');
    const periodInputs = [...row.querySelectorAll('input[name="payment_period_name"]')];
    const amountInput = row.querySelector('input[name="amount"]');
    const suggestions = row.querySelector('.student-suggestions');
    let selectedStudent = null;
    let searchTimer = null;
    let searchController = null;

    function updatePeriods(enrollment) {
      for (const input of periodInputs) {
        const period = Number(input.value.replace('Đợt ', ''));
        input.disabled = !enrollment || !enrollment.unpaid_periods.includes(period);
        if (input.disabled) input.checked = false;
      }
    }

    function chooseEnrollment(enrollment) {
      enrollmentInput.value = enrollment ? enrollment.id : '';
      teacherInput.value = enrollment ? enrollment.teacher : '';
      subjectInput.value = enrollment ? enrollment.subject : '';
      updatePeriods(enrollment);
    }

    function clearStudent() {
      studentIdInput.value = '';
      classroomInput.value = '';
      enrollmentInput.value = '';
      teacherInput.value = '';
      subjectInput.value = '';
      selectedStudent = null;
      teacherChoice.replaceChildren(new Option('Chọn giảng viên', ''));
      teacherChoice.disabled = true;
      updatePeriods(null);
    }

    function chooseStudent(student) {
      selectedStudent = student;
      studentInput.value = student.name;
      studentIdInput.value = student.id;
      classroomInput.value = student.classroom;
      teacherChoice.replaceChildren(new Option('Chọn giảng viên', ''));
      for (const enrollment of student.enrollments) {
        teacherChoice.add(new Option(`${enrollment.teacher} — ${enrollment.subject}`, enrollment.id));
      }
      teacherChoice.disabled = false;
      suggestions.classList.add('d-none');
      if (student.enrollments.length === 1) {
        teacherChoice.value = String(student.enrollments[0].id);
        chooseEnrollment(student.enrollments[0]);
      } else {
        chooseEnrollment(null);
      }
    }

    function showSuggestions(students, message = '') {
      suggestions.replaceChildren();
      for (const student of students) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'list-group-item list-group-item-action';
        const name = document.createElement('strong');
        name.textContent = student.name;
        const classroom = document.createElement('small');
        classroom.className = 'd-block text-secondary';
        classroom.textContent = `${student.classroom} · Hồ sơ #${student.id}`;
        button.append(name, classroom);
        button.addEventListener('mousedown', event => event.preventDefault());
        button.addEventListener('click', () => chooseStudent(student));
        suggestions.append(button);
      }
      if (!students.length) {
        const empty = document.createElement('div');
        empty.className = 'list-group-item text-secondary small';
        empty.textContent = message || 'Không tìm thấy học sinh phù hợp';
        suggestions.append(empty);
      }
      suggestions.classList.remove('d-none');
    }

    async function searchStudents(query) {
      if (searchController) searchController.abort();
      searchController = new AbortController();
      try {
        const response = await fetch(form.dataset.studentSearchUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ query }),
          signal: searchController.signal,
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Không thể tìm kiếm học sinh.');
        if (studentInput.value.trim() === query) showSuggestions(result.students);
      } catch (error) {
        if (error.name !== 'AbortError') showSuggestions([], error.message);
      }
    }

    studentInput.addEventListener('input', () => {
      clearStudent();
      clearTimeout(searchTimer);
      if (searchController) searchController.abort();
      const query = studentInput.value.trim();
      if (!query) {
        suggestions.classList.add('d-none');
        return;
      }
      searchTimer = setTimeout(() => searchStudents(query), 250);
    });
    studentInput.addEventListener('focus', () => {
      const query = studentInput.value.trim();
      if (!studentIdInput.value && query) searchStudents(query);
    });
    studentInput.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !suggestions.classList.contains('d-none')) {
        const firstMatch = suggestions.querySelector('button');
        if (firstMatch) {
          event.preventDefault();
          firstMatch.click();
        }
      }
    });
    studentInput.addEventListener('blur', () => {
      setTimeout(() => suggestions.classList.add('d-none'), 180);
    });
    teacherChoice.addEventListener('change', () => {
      const enrollment = selectedStudent?.enrollments.find(item => item.id === Number(teacherChoice.value));
      chooseEnrollment(enrollment || null);
    });
    amountInput.addEventListener('input', updateTotal);
    for (const periodInput of periodInputs) {
      periodInput.addEventListener('change', updateTotal);
    }
    for (const button of row.querySelectorAll('.quick-amount')) {
      button.addEventListener('click', () => {
        amountInput.value = button.dataset.amount;
        updateTotal();
      });
    }
    updatePeriods(null);
  }

  initializeRow(rowsContainer.querySelector('.payment-request-row'));
  document.querySelector('#add-payment-request-row').addEventListener('click', () => {
    const template = rowsContainer.querySelector('.payment-request-row');
    const row = template.cloneNode(true);
    rowIndex += 1;
    row.dataset.rowIndex = rowIndex;
    row.querySelectorAll('[id]').forEach(element => {
      element.id = `${element.id}-${rowIndex}`;
    });
    row.querySelectorAll('input').forEach(input => {
      if (input.type === 'checkbox' || input.type === 'radio') input.checked = false;
      else input.value = '';
      input.disabled = false;
    });
    row.querySelectorAll('select').forEach(select => {
      select.replaceChildren(new Option('Chọn giảng viên', ''));
      select.value = '';
      select.disabled = true;
    });
    row.querySelector('.student-suggestions').replaceChildren();
    row.querySelector('.student-suggestions').classList.add('d-none');
    row.querySelector('.remove-payment-row').classList.remove('d-none');
    rowsContainer.append(row);
    initializeRow(row);
  });

  rowsContainer.addEventListener('click', event => {
    const removeButton = event.target.closest('.remove-payment-row');
    if (!removeButton) return;
    removeButton.closest('.payment-request-row').remove();
    updateTotal();
  });

  form.addEventListener('submit', () => {
    const paymentMethod = form.querySelector('[name="payment_method"]').value;
    const items = [...rowsContainer.querySelectorAll('.payment-request-row')].map(row => ({
      student_id: row.querySelector('[name="student_id"]').value,
      enrollment: row.querySelector('[name="enrollment"]').value,
      student_name: row.querySelector('[name="student_name"]').value,
      classroom_name: row.querySelector('[name="classroom_name"]').value,
      subject_name: row.querySelector('[name="subject_name"]').value,
      teacher_name: row.querySelector('[name="teacher_name"]').value,
      payment_period_name: [...row.querySelectorAll('[name="payment_period_name"]:checked')].map(input => input.value),
      amount: row.querySelector('[name="amount"]').value,
      payment_method: paymentMethod,
    }));
    batchItemsInput.value = JSON.stringify(items);
  });

  updateTotal();
})();
