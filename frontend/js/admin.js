auth.requireAuth();

const ROLE_LABELS = {
  1: { label: "Учасник", cls: "secondary" },
  2: { label: "Орг. комітет", cls: "info" },
  3: { label: "Адміністратор", cls: "danger" },
};

async function init() {
  const user = auth.getUser() || await api.me();
  document.getElementById("userName").textContent = user.full_name || user.email;
  await loadUsers();
  await loadConferences();
}

function showTab(tab) {
  document.getElementById("tab-users").classList.toggle("d-none", tab !== "users");
  document.getElementById("tab-conferences").classList.toggle("d-none", tab !== "conferences");
  document.querySelectorAll("#adminTabs .nav-link").forEach((el, i) => {
    el.classList.toggle("active", (i === 0 && tab === "users") || (i === 1 && tab === "conferences"));
  });
}

async function loadUsers() {
  const tbody = document.getElementById("usersTable");
  try {
    const users = await api.getUsers();
    if (!users.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Користувачів немає</td></tr>`;
      return;
    }
    tbody.innerHTML = users.map(u => {
      const roles = u.role_ids.map(id => {
        const r = ROLE_LABELS[id] || { label: id, cls: "secondary" };
        return `<span class="badge bg-${r.cls} me-1">${r.label}</span>`;
      }).join("");
      return `
        <tr>
          <td>${u.full_name || "—"}</td>
          <td>${u.email}</td>
          <td>${roles}</td>
          <td class="text-end">
            <button class="btn btn-outline-danger btn-sm" title="Видалити користувача" onclick="deleteUser('${u.id}', '${u.email}')">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>`;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">${e.message}</td></tr>`;
  }
}

async function createUser() {
  const errEl = document.getElementById("createUserError");
  errEl.classList.add("d-none");

  const full_name = document.getElementById("newUserName").value.trim();
  const email = document.getElementById("newUserEmail").value.trim();
  const password = document.getElementById("newUserPassword").value.trim();
  const role_id = parseInt(document.getElementById("newUserRole").value);

  if (!email || !password) {
    errEl.textContent = "Email та пароль обов'язкові";
    errEl.classList.remove("d-none");
    return;
  }

  try {
    await api.createUser({ full_name, email, password, role_id });
    bootstrap.Modal.getInstance(document.getElementById("createUserModal")).hide();
    document.getElementById("newUserName").value = "";
    document.getElementById("newUserEmail").value = "";
    document.getElementById("newUserPassword").value = "";
    await loadUsers();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("d-none");
  }
}

async function deleteUser(userId, email) {
  if (!confirm(`Видалити користувача ${email}?`)) return;
  try {
    await api.deleteUser(userId);
    await loadUsers();
  } catch (e) {
    alert(e.message);
  }
}

async function loadConferences() {
  const tbody = document.getElementById("conferencesTable");
  try {
    const conferences = await api.getConferences();
    if (!conferences.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">Конференцій ще немає</td></tr>`;
      return;
    }
    tbody.innerHTML = conferences.map(c => `
      <tr>
        <td>
          <div class="fw-semibold">${c.title}</div>
          <small class="text-muted">${c.description || ""}</small>
        </td>
        <td><small>${new Date(c.submission_deadline).toLocaleDateString("uk-UA")}</small></td>
        <td>
          <span class="badge bg-${c.is_active ? "success" : "secondary"}">
            ${c.is_active ? "Активна" : "Завершена"}
          </span>
        </td>
        <td class="text-end d-flex gap-1 justify-content-end">
          <button class="btn btn-outline-warning btn-sm" title="Редагувати конференцію" onclick="openEditConference('${c.id}', '${c.title}', '${c.description || ""}', '${c.submission_deadline}', ${c.is_active})">
            <i class="bi bi-pencil"></i>
          </button>
          <button class="btn btn-outline-danger btn-sm" title="Видалити конференцію" onclick="deleteConference('${c.id}', '${c.title}')">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>`).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger py-4">${e.message}</td></tr>`;
  }
}

async function createConference() {
  const errEl = document.getElementById("createConfError");
  errEl.classList.add("d-none");

  const title = document.getElementById("confTitle").value.trim();
  const description = document.getElementById("confDescription").value.trim();
  const deadline = document.getElementById("confDeadline").value;

  if (!title || !deadline) {
    errEl.textContent = "Назва та дедлайн обов'язкові";
    errEl.classList.remove("d-none");
    return;
  }

  try {
    await api.createConference({
      title,
      description: description || null,
      submission_deadline: new Date(deadline).toISOString(),
    });
    bootstrap.Modal.getInstance(document.getElementById("createConferenceModal")).hide();
    document.getElementById("confTitle").value = "";
    document.getElementById("confDescription").value = "";
    document.getElementById("confDeadline").value = "";
    await loadConferences();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("d-none");
  }
}

function openEditConference(id, title, description, deadline, isActive) {
  document.getElementById("editConfId").value = id;
  document.getElementById("editConfTitle").value = title;
  document.getElementById("editConfDescription").value = description;
  document.getElementById("editConfDeadline").value = deadline.slice(0, 16);
  document.getElementById("editConfActive").checked = isActive;
  document.getElementById("editConfError").classList.add("d-none");
  new bootstrap.Modal(document.getElementById("editConferenceModal")).show();
}

async function saveEditConference() {
  const errEl = document.getElementById("editConfError");
  errEl.classList.add("d-none");

  const id = document.getElementById("editConfId").value;
  const title = document.getElementById("editConfTitle").value.trim();
  const description = document.getElementById("editConfDescription").value.trim();
  const deadline = document.getElementById("editConfDeadline").value;
  const is_active = document.getElementById("editConfActive").checked;

  if (!title || !deadline) {
    errEl.textContent = "Назва та дедлайн обов'язкові";
    errEl.classList.remove("d-none");
    return;
  }

  try {
    await api.updateConference(id, {
      title,
      description: description || null,
      submission_deadline: new Date(deadline).toISOString(),
      is_active,
    });
    bootstrap.Modal.getInstance(document.getElementById("editConferenceModal")).hide();
    await loadConferences();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("d-none");
  }
}

async function deleteConference(id, title) {
  if (!confirm(`Видалити конференцію "${title}"?`)) return;
  try {
    await api.deleteConference(id);
    await loadConferences();
  } catch (e) {
    alert(e.message);
  }
}

init();