(() => {
  const form = document.querySelector('form[data-student-search-url]');
  const studentInput = document.getElementById('id_student_name');
  const studentIdInput = document.getElementById('id_student_id');
  const classroomInput = document.getElementById('id_classroom_name');
  const enrollmentInput = document.getElementById('id_enrollment');
  const teacherInput = document.getElementById('id_teacher_name');
  const teacherChoice = document.getElementById('teacher-choice');
  const subjectInput = document.getElementById('id_subject_name');
  const periodInputs = [...document.querySelectorAll('input[name="payment_period_name"]')];
  const amountInput = document.getElementById('id_amount');
  const total = document.getElementById('request-total');
  const suggestions = document.getElementById('student-suggestions');
  const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
  let selectedStudent = null;
  let searchTimer = null;
  let searchController = null;
  let restoredPeriod = periodInputs.find(input => input.checked)?.value || '';

  function updatePeriods(enrollment) {
    for (const input of periodInputs) {
      const period = Number(input.value.replace('Đợt ', ''));
      input.disabled = !enrollment || !enrollment.unpaid_periods.includes(period);
      if (input.disabled) input.checked = false;
    }
    if (enrollment && restoredPeriod) {
      const restoredInput = periodInputs.find(input => input.value === restoredPeriod);
      if (restoredInput && !restoredInput.disabled) restoredInput.checked = true;
      restoredPeriod = '';
    }
  }

  function clearEnrollment() {
    enrollmentInput.value = '';
    teacherInput.value = '';
    subjectInput.value = '';
    teacherChoice.replaceChildren(new Option('Chọn giảng viên', ''));
    teacherChoice.disabled = true;
    updatePeriods(null);
  }

  function clearStudent() {
    studentIdInput.value = '';
    classroomInput.value = '';
    selectedStudent = null;
    restoredPeriod = '';
    clearEnrollment();
  }

  function chooseEnrollment(enrollment) {
    enrollmentInput.value = enrollment ? enrollment.id : '';
    teacherInput.value = enrollment ? enrollment.teacher : '';
    subjectInput.value = enrollment ? enrollment.subject : '';
    updatePeriods(enrollment);
  }

  function chooseStudent(student, previousEnrollmentId = null) {
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
    const previous = student.enrollments.find(item => item.id === Number(previousEnrollmentId));
    const enrollment = previous || (student.enrollments.length === 1 ? student.enrollments[0] : null);
    if (enrollment) teacherChoice.value = String(enrollment.id);
    chooseEnrollment(enrollment);
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

  async function searchStudents(query, restoreStudentId = null, restoreEnrollmentId = null) {
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
      if (restoreStudentId) {
        const match = result.students.find(item => item.id === Number(restoreStudentId));
        if (match) chooseStudent(match, restoreEnrollmentId);
      } else if (studentInput.value.trim() === query) {
        showSuggestions(result.students);
      }
    } catch (error) {
      if (error.name !== 'AbortError') showSuggestions([], error.message);
    }
  }

  studentInput.addEventListener('input', () => {
    clearStudent();
    clearTimeout(searchTimer);
    if (searchController) searchController.abort();
    const query = studentInput.value.trim();
    if (query.length < 3) {
      suggestions.classList.add('d-none');
      return;
    }
    searchTimer = setTimeout(() => searchStudents(query), 250);
  });
  studentInput.addEventListener('focus', () => {
    const query = studentInput.value.trim();
    if (!studentIdInput.value && query.length >= 3) searchStudents(query);
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

  function updateTotal() {
    const amount = Number(amountInput.value);
    total.textContent = `${new Intl.NumberFormat('vi-VN').format(Number.isFinite(amount) && amount > 0 ? amount : 0)} VNĐ`;
  }
  for (const button of document.querySelectorAll('.quick-amount')) {
    button.addEventListener('click', () => {
      amountInput.value = button.dataset.amount;
      updateTotal();
    });
  }
  amountInput.addEventListener('input', updateTotal);

  updatePeriods(null);
  if (studentIdInput.value && enrollmentInput.value && studentInput.value.trim().length >= 3) {
    searchStudents(studentInput.value.trim(), studentIdInput.value, enrollmentInput.value);
  }
  updateTotal();
})();
