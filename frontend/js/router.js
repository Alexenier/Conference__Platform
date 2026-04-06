async function redirectByRole() {
  try {
    const user = await api.me();
    const roles = await api.getUserRoles(user.id);
    const roleIds = roles.roles.map(r => r.id);

    auth.saveSession(auth.getToken(), user);

    if (roleIds.includes(3)) {
      window.location.href = "/pages/admin.html";
    } else if (roleIds.includes(2)) {
      window.location.href = "/pages/review.html";
    } else {
      window.location.href = "/pages/submissions.html";
    }
  } catch (e) {
    auth.logout();
  }
}