auth.requireAuth();

let currentUser = null;
let currentSubmissionId = null;

const STATUS_LABELS = {
  draft: { label: "Чернетка", cls: "secondary" },
  submitted: { label: "Подано", cls: "primary" },
  under_review: { label: "На розгляді", cls: "warning" },
  accepted: { label: "Прийнято", cls: "success" },
  rejected: { label: "Відхилено", cls: "danger" },
};

async function init() {
  currentUser = auth.getUser();
  if (!currentUser) {
    currentUser = await api.me();
    localStorage.setItem("user", JSON.stringify(currentUser));
  }
  document.getElementById("userName").textContent = currentUser.full_name || currentUser.email;
  await loadConferences();
  await loadSections();
  await loadSubmissions();
}

async function loadConferences() {
  const conferences = await api.getConferences(true);
  const sel = document.getElementById("conferenceSelect");
  sel.innerHTML = conferences.map(c =>
    `<option value="${c.id}">${c.title}</option>`
  ).join("");
}

async function loadSections() {
  const data = await api.getSections();
  const sel = document.getElementById("sectionSelect");
  sel.innerHTML = `<option value="">Оберіть секцію</option>` +
    data.sections.map(s => `<option value="${s}">${s}</option>`).join("");
}

async function loadSubmissions() {
  const tbody = document.getElementById("submissionsTable");
  try {
    const submissions = await api.getSubmissions();
    if (!submissions.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">Заявок ще немає</td></tr>`;
      return;
    }
    tbody.innerHTML = submissions.map(s => {
      const st = STATUS_LABELS[s.status] || { label: s.status, cls: "secondary" };
      const authors = s.authors.map(a => a.full_name).join(", ") || "—";
      return `
        <tr>
          <td>
            <div class="fw-semibold">${s.title}</div>
            <small class="text-muted">${authors}</small>
          </td>
          <td><small>${s.section || "—"}</small></td>
          <td><span class="badge bg-${st.cls}">${st.label}</span></td>
          <td><small>${new Date(s.created_at).toLocaleDateString("uk-UA")}</small></td>
          <td>
            <button class="btn btn-outline-secondary btn-sm" onclick="openFiles('${s.id}')" title="Файли заявки">
              <i class="bi bi-paperclip"></i>
            </button>
            ${s.status === 'draft' ? `
            <button class="btn btn-outline-primary btn-sm ms-1" onclick="submitSubmission('${s.id}')" title="Подати заявку">
              <i class="bi bi-send"></i>
            </button>` : ''}
          </td>
        </tr>`;
    }).join("");
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">${e.message}</td></tr>`;
  }
}

async function submitSubmission(submissionId) {
  if (!confirm("Подати заявку на розгляд?")) return;
  try {
    await api.updateStatus(submissionId, "submitted");
    await loadSubmissions();
  } catch (e) {
    alert(e.message);
  }
}

let authorCount = 0;
function addAuthorRow() {
  authorCount++;
  const div = document.createElement("div");
  div.className = "row g-2 mb-2 author-row";
  div.innerHTML = `
    <div class="col-md-4">
      <label class="visually-hidden">Прізвище та ініціали</label>
      <input type="text" class="form-control form-control-sm author-name" placeholder="Прізвище І.О." title="Прізвище та ініціали автора">
    </div>
    <div class="col-md-4">
      <label class="visually-hidden">Організація</label>
      <input type="text" class="form-control form-control-sm author-org" placeholder="Організація" title="Організація автора">
    </div>
    <div class="col-md-3">
      <label class="visually-hidden">Email</label>
      <input type="email" class="form-control form-control-sm author-email" placeholder="Email" title="Email автора">
    </div>
    <div class="col-md-1">
      <button class="btn btn-outline-danger btn-sm" title="Видалити автора" onclick="this.closest('.author-row').remove()">
        <i class="bi bi-trash"></i>
      </button>
    </div>`;
  document.getElementById("authorsList").appendChild(div);
}

async function submitNewSubmission() {
  const errEl = document.getElementById("modalError");
  errEl.classList.add("d-none");

  const conference_id = document.getElementById("conferenceSelect").value;
  const title = document.getElementById("subTitle").value.trim();
  const section = document.getElementById("sectionSelect").value;
  const abstract = document.getElementById("subAbstract").value.trim();

  if (!title) {
    errEl.textContent = "Введіть назву доповіді";
    errEl.classList.remove("d-none");
    return;
  }

  const authors = [...document.querySelectorAll(".author-row")].map((row, i) => ({
    full_name: row.querySelector(".author-name").value.trim(),
    organization: row.querySelector(".author-org").value.trim(),
    email: row.querySelector(".author-email").value.trim(),
    is_presenter: i === 0,
    order: i,
  })).filter(a => a.full_name);

  try {
    await api.createSubmission({
      conference_id,
      author_id: currentUser.id,
      title,
      abstract,
      section: section || null,
      authors,
    });
    bootstrap.Modal.getInstance(document.getElementById("newSubmissionModal")).hide();
    await loadSubmissions();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove("d-none");
  }
}

async function openFiles(submissionId) {
  currentSubmissionId = submissionId;
  document.getElementById("uploadResult").innerHTML = "";
  document.getElementById("fileInput").value = "";
  await loadFiles();
  new bootstrap.Modal(document.getElementById("filesModal")).show();
}

async function loadFiles() {
  const list = document.getElementById("filesList");
  try {
    const files = await api.getFiles(currentSubmissionId);
    if (!files.length) {
      list.innerHTML = `<p class="text-muted">Файлів ще немає</p>`;
      return;
    }
    list.innerHTML = files.map(f => `
      <div class="d-flex justify-content-between align-items-center border rounded p-2 mb-2">
        <div>
          <i class="bi bi-file-earmark-word text-primary"></i>
          <span class="ms-2">${f.original_name}</span>
          <small class="text-muted ms-2">${(f.size_bytes / 1024).toFixed(1)} KB</small>
        </div>
        <button class="btn btn-outline-danger btn-sm" title="Видалити файл" onclick="removeFile('${f.id}')">
          <i class="bi bi-trash"></i>
        </button>
      </div>`).join("");
  } catch (e) {
    list.innerHTML = `<p class="text-danger">${e.message}</p>`;
  }
}

async function uploadFile() {
  const fileInput = document.getElementById("fileInput");
  const resultEl = document.getElementById("uploadResult");
  if (!fileInput.files.length) return;

  const file = fileInput.files[0];
  if (file.size === 0) {
    resultEl.innerHTML = `<div class="alert alert-danger">Файл порожній. Оберіть інший файл.</div>`;
    return;
  }

  try {
    const result = await api.uploadFile(currentSubmissionId, file);
    let html = `<div class="alert alert-success">Файл завантажено!</div>`;
    if (result.validation) {
      const v = result.validation;
      if (v.ok === true) {
        html += `<div class="alert alert-success"><i class="bi bi-check-circle"></i> Тези оформлені коректно</div>`;
      } else if (v.ok === false) {
        const errors = v.issues.filter(i => i.severity === "error");
        const warnings = v.issues.filter(i => i.severity === "warning");
        html += `<div class="alert alert-warning">
          <strong>Знайдено проблеми:</strong><br>
          ${errors.map(i => `<div class="text-danger"><i class="bi bi-x-circle"></i> ${i.message}</div>`).join("")}
          ${warnings.map(i => `<div class="text-warning"><i class="bi bi-exclamation-triangle"></i> ${i.message}</div>`).join("")}
        </div>`;
      }
    }
    resultEl.innerHTML = html;
    await loadFiles();
  } catch (e) {
    resultEl.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
  }
}

async function removeFile(fileId) {
  if (!confirm("Видалити файл?")) return;
  try {
    await api.deleteFile(currentSubmissionId, fileId);
    await loadFiles();
  } catch (e) {
    alert(e.message);
  }
}

init();