auth.requireAuth();

const STATUS_LABELS = {
  draft:        { label: "Чернетка",    cls: "secondary" },
  submitted:    { label: "Подано",      cls: "primary" },
  under_review: { label: "На розгляді", cls: "warning" },
  accepted:     { label: "Прийнято",    cls: "success" },
  rejected:     { label: "Відхилено",   cls: "danger" },
};

const STATUS_TRANSITIONS = {
  draft:        [],
  submitted:    ["under_review", "draft"],
  under_review: ["accepted", "rejected"],
  accepted:     [],
  rejected:     ["draft"],
};

const STATUS_TRANSITION_LABELS = {
  under_review: "Взяти на розгляд",
  accepted:     "Прийняти",
  rejected:     "Відхилити",
  draft:        "Повернути в чернетку",
};

let allConferences = [];
let currentSubmission = null;
let searchTimeout = null;

async function init() {
  const user = auth.getUser() || await api.me();
  document.getElementById("userName").textContent = user.full_name || user.email;
  await loadConferences();
  await loadSections();
  await loadSubmissions();

  document.getElementById("searchInput").addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadSubmissions(), 400);
  });
}

async function loadConferences() {
  try {
    allConferences = await api.getConferences();
    const sel = document.getElementById("filterConference");
    allConferences.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.title;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error(e);
  }
}

async function loadSections() {
  try {
    const data = await api.getSections();
    const sel = document.getElementById("filterSection");
    data.sections.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error(e);
  }
}

async function loadSubmissions() {
  const tbody = document.getElementById("submissionsTable");
  const searchQuery = document.getElementById("searchInput").value.trim();
  const conf = document.getElementById("filterConference").value;
  const status = document.getElementById("filterStatus").value;
  const section = document.getElementById("filterSection").value;

  try {
    let submissions;

    if (searchQuery) {
      submissions = await api.searchSubmissions(searchQuery, conf || null);
      if (status) submissions = submissions.filter(s => s.status === status);
      if (section) submissions = submissions.filter(s => s.section === section);
    } else {
      const params = {};
      if (conf) params.conference_id = conf;
      if (status) params.status = status;
      if (section) params.section = section;
      submissions = await api.getSubmissions(params);
    }

    document.getElementById("submissionsCount").textContent = `(${submissions.length})`;

    if (!submissions.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">Заявок не знайдено</td></tr>`;
      return;
    }

    tbody.innerHTML = submissions.map(s => {
      const st = STATUS_LABELS[s.status] || { label: s.status, cls: "secondary" };
      const authors = s.authors.map(a => a.full_name).join(", ") || "—";
      const conf = allConferences.find(c => c.id === s.conference_id);
      const confTitle = conf ? conf.title : "—";

      return `
        <tr>
          <td>
            <div class="fw-semibold">${s.title}</div>
            <small class="text-muted">${authors}</small>
          </td>
          <td><small>${s.section || "—"}</small></td>
          <td><small>${confTitle}</small></td>
          <td><span class="badge bg-${st.cls}">${st.label}</span></td>
          <td><small>${new Date(s.created_at).toLocaleDateString("uk-UA")}</small></td>
          <td>
            <button class="btn btn-outline-secondary btn-sm" title="Переглянути деталі" onclick="openDetail('${s.id}')">
              <i class="bi bi-eye"></i>
            </button>
          </td>
        </tr>`;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">${e.message}</td></tr>`;
  }
}

async function openDetail(submissionId) {
  try {
    const submissions = await api.getSubmissions();
    const s = submissions.find(x => x.id === submissionId);
    if (!s) return;
    currentSubmission = s;

    const st = STATUS_LABELS[s.status] || { label: s.status, cls: "secondary" };
    const conf = allConferences.find(c => c.id === s.conference_id);
    const authors = s.authors.map(a => `
      <div class="d-flex gap-3 mb-1">
        <span class="fw-semibold">${a.full_name}</span>
        <span class="text-muted">${a.organization || ""}</span>
        <span class="text-muted">${a.email || ""}</span>
        ${a.is_presenter ? '<span class="badge bg-primary">Доповідач</span>' : ""}
      </div>`).join("") || "—";

    const files = await api.getFiles(submissionId);
    const filesList = files.length ? files.map(f => `
      <div class="d-flex align-items-center justify-content-between mb-2 border rounded p-2">
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-file-earmark-word text-primary"></i>
          <span>${f.original_name}</span>
          <small class="text-muted">${(f.size_bytes / 1024).toFixed(1)} KB</small>
        </div>
        <button class="btn btn-outline-primary btn-sm"
                onclick="downloadFile('${submissionId}', '${f.id}', '${f.original_name}')"
                title="Завантажити файл">
          <i class="bi bi-download"></i>
        </button>
      </div>`).join("") : '<p class="text-muted">Файлів немає</p>';

    document.getElementById("detailModalLabel").textContent = s.title;
    document.getElementById("detailModalBody").innerHTML = `
      <div class="mb-3">
        <span class="badge bg-${st.cls} mb-2">${st.label}</span>
        <p class="text-muted mb-1"><strong>Конференція:</strong> ${conf ? conf.title : "—"}</p>
        <p class="text-muted mb-1"><strong>Секція:</strong> ${s.section || "—"}</p>
        <p class="text-muted mb-0"><strong>Дата подачі:</strong> ${new Date(s.created_at).toLocaleDateString("uk-UA")}</p>
      </div>
      ${s.abstract ? `<div class="mb-3"><strong>Анотація:</strong><p class="text-muted mt-1">${s.abstract}</p></div>` : ""}
      <div class="mb-3"><strong>Автори:</strong><div class="mt-1">${authors}</div></div>
      <div><strong>Файли:</strong><div class="mt-1">${filesList}</div></div>
    `;

    const transitions = STATUS_TRANSITIONS[s.status] || [];
    const footer = document.getElementById("detailModalFooter");
    footer.innerHTML = `<button class="btn btn-secondary" data-bs-dismiss="modal">Закрити</button>`;
    transitions.forEach(newStatus => {
      const label = STATUS_TRANSITION_LABELS[newStatus] || newStatus;
      const cls = newStatus === "accepted" ? "success" : newStatus === "rejected" ? "danger" : "primary";
      footer.innerHTML += `
        <button class="btn btn-${cls}" onclick="changeStatus('${s.id}', '${newStatus}')" title="${label}">
          ${label}
        </button>`;
    });

    new bootstrap.Modal(document.getElementById("detailModal")).show();
  } catch (e) {
    alert(e.message);
  }
}

async function changeStatus(submissionId, newStatus) {
  try {
    await api.updateStatus(submissionId, newStatus);
    bootstrap.Modal.getInstance(document.getElementById("detailModal")).hide();
    await loadSubmissions();
  } catch (e) {
    alert(e.message);
  }
}

function resetFilters() {
  document.getElementById("filterConference").value = "";
  document.getElementById("filterStatus").value = "";
  document.getElementById("filterSection").value = "";
  document.getElementById("searchInput").value = "";
  loadSubmissions();
}

async function downloadProgram() {
  const confId = document.getElementById("filterConference").value;
  if (!confId) {
    alert("Оберіть конференцію для завантаження програми");
    return;
  }
  const token = localStorage.getItem("token");
  const response = await fetch(api.downloadProgram(confId), {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!response.ok) {
    alert("Помилка завантаження програми");
    return;
  }
  const blob = await response.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `програма.pdf`;
  a.click();
  URL.revokeObjectURL(a.href);
}

async function downloadFile(submissionId, fileId, fileName) {
  const token = localStorage.getItem("token");
  const response = await fetch(api.downloadFile(submissionId, fileId), {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!response.ok) {
    alert("Помилка завантаження файлу");
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

init();