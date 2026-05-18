// const API_BASE = "http://localhost:8000";
const API_BASE = "/api";

async function request(method, path, body = null, auth = true) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = localStorage.getItem("token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_BASE}${path}`, options);

  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    // window.location.href = "/frontend/index.html";
    window.location.href = "/index.html";
    return;
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Невідома помилка" }));
    throw new Error(err.detail || "Помилка запиту");
  }

  if (response.status === 204) return null;
  return response.json();
}

const api = {
  // Auth
  login: (data) => request("POST", "/auth/login", data, false),
  me: () => request("GET", "/auth/me"),

  // Conferences
  getConferences: (isActive) => request("GET", `/conferences/${isActive !== undefined ? `?is_active=${isActive}` : ""}`),
  createConference: (data) => request("POST", "/conferences/", data),
  updateConference: (id, data) => request("PATCH", `/conferences/${id}`, data),
  deleteConference: (id) => request("DELETE", `/conferences/${id}`),
  downloadProgram: (id, sectionsData) => request("POST", `/conferences/${id}/program.pdf`, { sections: sectionsData }),
  downloadCollection: (id) => `${API_BASE}/conferences/${id}/collection.pdf`,

  // Submissions
  getSections: () => request("GET", "/submissions/sections"),
  getSubmissions: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request("GET", `/submissions/${q ? `?${q}` : ""}`);
  },
  createSubmission: (data) => request("POST", "/submissions/", data),
  updateStatus: (id, status) => request("PATCH", `/submissions/${id}/status`, { status }),
  searchSubmissions: (q, conference_id = null) => {
  const params = new URLSearchParams({ q });
  if (conference_id) params.append("conference_id", conference_id);
  return request("GET", `/search/submissions?${params.toString()}`);
},

  // Submission files
  getFiles: (submissionId) => request("GET", `/submissions/${submissionId}/files/`),
  deleteFile: (submissionId, fileId) => request("DELETE", `/submissions/${submissionId}/files/${fileId}`),
  downloadFile: (submissionId, fileId) => `${API_BASE}/submissions/${submissionId}/files/${fileId}/download`,
  uploadFile: async (submissionId, file) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${API_BASE}/submissions/${submissionId}/files/`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Помилка завантаження" }));
      throw new Error(err.detail);
    }
    return response.json();
  },

  // Roles
  getRoles: () => request("GET", "/roles/"),
  getUserRoles: (userId) => request("GET", `/roles/users/${userId}`),
  assignRole: (userId, roleId) => request("POST", "/roles/assign", { user_id: userId, role_id: roleId }),
  revokeRole: (userId, roleId) => request("POST", "/roles/revoke", { user_id: userId, role_id: roleId }),

  // Admin
  getUsers: () => request("GET", "/admin/users"),
  createUser: (data) => request("POST", "/admin/users", data),
  deleteUser: (userId) => request("DELETE", `/admin/users/${userId}`),
};