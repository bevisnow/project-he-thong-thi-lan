const loginForm = document.getElementById("loginForm");

if (loginForm) {
  const baseInput = loginForm.elements.base;
  baseInput.value = localStorage.getItem("examBase") || location.origin;

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("loginError");
    const base = baseInput.value.trim().replace(/\/$/, "");
    error.textContent = "";

    try {
      const response = await fetch(`${base}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: loginForm.elements.username.value,
          password: loginForm.elements.password.value,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Không đăng nhập được.");

      localStorage.setItem("examBase", base);
      sessionStorage.setItem("examToken", data.access_token);
      sessionStorage.setItem("examUser", JSON.stringify(data.user));
      sessionStorage.setItem("appLastPage", "dashboard");
      location.href = "/index.html";
    } catch (err) {
      error.textContent = err instanceof TypeError
        ? "Không kết nối được máy chủ. Kiểm tra địa chỉ và mạng LAN."
        : err.message;
    }
  });
}

const joinForm = document.getElementById("joinForm");

if (joinForm) {
  joinForm.elements.base.value = localStorage.getItem("examBase") || location.origin;
  joinForm.elements.access_code.value = new URLSearchParams(location.search).get("code") || "";

  joinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = document.getElementById("joinError");
    const base = joinForm.elements.base.value.trim().replace(/\/$/, "");
    error.textContent = "";

    try {
      const response = await fetch(`${base}/api/exam/join`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access_code: joinForm.elements.access_code.value.trim(),
          student_code: joinForm.elements.student_code.value.trim(),
          password: joinForm.elements.password.value || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Không vào được phòng thi.");

      localStorage.setItem("examBase", base);
      sessionStorage.setItem("studentToken", data.access_token);
      sessionStorage.setItem("appLastPage", "exam");
      location.href = "/lam-bai.html";
    } catch (err) {
      error.textContent = err instanceof TypeError
        ? "Không kết nối được máy chủ. Kiểm tra địa chỉ và mạng LAN."
        : err.message;
    }
  });
}
