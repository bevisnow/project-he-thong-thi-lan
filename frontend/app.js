const $ = (s, root = document) => root.querySelector(s);
const esc = (x) =>
  String(x ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function questionTextHtml(text) {
  return esc(text).replace(
    /!\[\]\(\/media\/([a-f0-9]{16}\.(?:png|jpe?g|gif|webp))\)/gi,
    (_, file) =>
      `<img class="question-inline-image" src="${esc(state.base.replace(/\/$/, ""))}/media/${file}" alt="Hình minh họa câu hỏi">`,
  );
}
window.questionTextHtml = questionTextHtml;

const state = {
  base: localStorage.getItem("examBase") || location.origin,
  token: sessionStorage.getItem("examToken") || "",
  user: JSON.parse(sessionStorage.getItem("examUser") || "null"),
  page: sessionStorage.getItem("appLastPage") || "home",
  subjects: [],
  grades: [],
  topics: [],
  lessons: [],
  exams: [],
  sessions: [],
  questions: [],
  classes: [],
  users: [],
  questionTotal: 0,
  editing: null,
  selectedExam: null,
  selectedSession: null,
  shuffle: {
    shuffle_questions: true,
    shuffle_options: true,
    paper_code_prefix: "M",
    paper_code_length: 2,
    paper_variant_count: 4,
  },
  studentToken: sessionStorage.getItem("studentToken") || "",
  student: null,
  exam: null,
  questionIndex: 1,
  timer: null,
  remaining: 0,
  answers: {},
};
const typeName = {
  multiple_choice: "Trắc nghiệm",
  true_false: "Đúng / Sai",
  short_answer: "Trả lời ngắn",
};
const diffName = {
  NB: "Nhận biết",
  TH: "Thông hiểu",
  VD: "Vận dụng",
  VDC: "Vận dụng cao",
};
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2800);
}
async function api(path, options = {}, token = state.token) {
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(state.base.replace(/\/$/, "") + path, {
      ...options,
      headers,
    });
  } catch {
    throw Error(
      "Không kết nối được máy chủ. Kiểm tra địa chỉ backend và mạng LAN.",
    );
  }
  const data = await ((res.headers.get("content-type") || "").includes("json")
    ? res.json()
    : res.text());
  const expired = res.status === 401 && !!token && token === state.token;
  if (expired) {
    state.token = "";
    state.user = null;
    sessionStorage.removeItem("examToken");
    sessionStorage.removeItem("examUser");
    state.page = "login";
    render();
  }
  if (expired)
    throw Error("Phiên đăng nhập đã hết hạn. Đăng nhập lại để tiếp tục.");
  if (!res.ok)
    throw Error(
      typeof data?.detail === "string"
        ? data.detail
        : JSON.stringify(data?.detail || data || `HTTP ${res.status}`),
    );
  return data;
}
function fileNameFrom(header, fallback) {
  const m = String(header || "").match(/filename\*?=(?:UTF-8''|"?)([^";]+)/i);
  return m ? decodeURIComponent(m[1].replace(/"/g, "")) : fallback;
}
async function downloadFile(path, fallbackName) {
  let res;
  try {
    res = await fetch(state.base.replace(/\/$/, "") + path, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
  } catch {
    throw Error(
      "Không kết nối được máy chủ. Kiểm tra địa chỉ backend và mạng LAN.",
    );
  }
  if (!res.ok) {
    const data = await ((res.headers.get("content-type") || "").includes("json")
      ? res.json()
      : res.text());
    throw Error(
      typeof data?.detail === "string"
        ? data.detail
        : JSON.stringify(data?.detail || data || `HTTP ${res.status}`),
    );
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileNameFrom(
    res.headers.get("Content-Disposition"),
    fallbackName,
  );
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
function fmtDate(value) {
  if (!value) return "Chưa đặt lịch";

  // Các thời điểm DB lưu không kèm múi giờ luôn được hiểu là UTC.
  const hasTimezone = /([zZ]|[+-]\d\d:\d\d)$/.test(value);
  const dateValue = hasTimezone ? value : value.replace(" ", "T") + "Z";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString("vi-VN", { timeZone: "Asia/Bangkok" });
}
function pageTitle() {
  return (
    {
      dashboard: "Tổng quan",
      questions: "Ngân hàng câu hỏi",
      createExam: "Tạo đề",
      exams: "Đề thi đã tạo",
      shuffle: "Trộn đề",
      rooms: "Phòng thi",
      classes: "Lớp học",
      users: "Tài khoản giáo viên",
    }[state.page] || "LanExam"
  );
}
function appShell(body) {
  const nav = [
    ["dashboard", "⌂", "Tổng quan"],
    ["questions", "▦", "Ngân hàng câu hỏi"],
    ["createExam", "＋", "Tạo đề"],
    ["exams", "▣", "Đề đã tạo"],
    ["shuffle", "⤨", "Trộn đề"],
    ["rooms", "▣", "Phòng thi"],
    ["classes", "▤", "Lớp học"],
    ...(state.user?.role === "admin" ? [["users", "♙", "Tài khoản giáo viên"]] : []),
  ];
  return `<div class="shell"><aside class="sidebar"><div class="brand"><b>◈ LanExam</b><small>HỆ THỐNG THI TRỰC TUYẾN</small></div><p class="nav-label">KHÔNG GIAN GIÁO VIÊN</p>${nav.map(([id, ic, label]) => `<button class="nav ${state.page === id ? "active" : ""}" data-page="${id}"><span class="ico">${ic}</span>${label}</button>`).join("")}<div class="profile"><div class="avatar">${esc((state.user?.full_name || "GV").slice(0, 2).toUpperCase())}</div><div><strong>${esc(state.user?.full_name || "Giáo viên")}</strong><small>${esc(state.user?.username || "")}</small></div><button class="link-button" data-action="logout" title="Đăng xuất">↗</button></div></aside><main class="main"><header class="topbar"><span>Không gian giáo viên　/　<b>${pageTitle()}</b></span></header><section class="content">${body}</section></main></div>`;
}
function landing() {
  return `<main class="landing"><section class="hero"><div class="hero-mark">◈</div><span class="eyebrow">LANEXAM · HỆ THỐNG THI</span><h1>Tạo đề dễ dàng.<br>Thi cử gọn gàng.</h1><p>Nền tảng quản lý câu hỏi, tạo đề và tổ chức các kỳ thi trên mạng nội bộ của trường.</p><small class="hero-foot">Dữ liệu được lưu tại hệ thống của trường.</small></section><section class="entry-side"><span class="eyebrow">BẮT ĐẦU</span><h2>Bạn đang sử dụng hệ thống với vai trò nào?</h2><p>Chọn không gian phù hợp để tiếp tục.</p><button class="choice-card" data-action="teacher"><span class="module-icon">♙</span><span><strong>Giáo viên</strong><small>Quản lý câu hỏi, đề thi và phòng thi</small></span></button><button class="choice-card" data-page="join"><span class="module-icon">✎</span><span><strong>Học sinh</strong><small>Nhập mã phòng và mã học sinh để vào thi</small></span></button></section></main>`;
}
function login() {
  return `<main class="login-wrap"><section class="hero"><div class="hero-mark">◈</div><span class="eyebrow">KHÔNG GIAN GIÁO VIÊN</span><h1>Chào mừng trở lại.</h1><p>Đăng nhập để tiếp tục quản lý ngân hàng câu hỏi, đề thi và phòng thi.</p></section><section class="entry-side"><div class="login-card"><button class="back-link" data-page="home">←　Trang chủ</button><h1>Giáo viên</h1><p>Dùng tài khoản được cấp bởi quản trị viên.</p><form id="loginForm"><label class="field">Địa chỉ máy chủ<input name="base" value="${esc(state.base)}" required placeholder="http://192.168.1.10:8000"></label><label class="field">Tên đăng nhập<input name="username" autocomplete="username" required></label><label class="field">Mật khẩu<input name="password" type="password" autocomplete="current-password" required></label><div id="loginError" class="error"></div><button class="primary" type="submit">Đăng nhập</button></form></div></section></main>`;
}
function heading(kicker, title, desc, action = "") {
  return `<div class="heading"><div><span class="eyebrow">${kicker}</span><h1>${title}</h1><p>${desc}</p></div>${action}</div>`;
}
function dashboard() {
  return `${heading("TỔNG QUAN", "Xin chào, " + esc(state.user?.full_name || "giáo viên"), "Chọn một công việc để bắt đầu.")}<div class="cards"><div class="stat"><small>Câu hỏi đang dùng</small><strong>${state.questionTotal || "—"}</strong><p>Trong ngân hàng câu hỏi</p></div><div class="stat"><small>Đề đã tạo</small><strong>${state.exams.length || "—"}</strong><p>Sẵn sàng mở phòng thi</p></div><div class="stat"><small>Phòng đang thi</small><strong>${state.sessions.filter((x) => x.status === "ongoing").length || 0}</strong><p>Có thể theo dõi trực tiếp</p></div></div><div class="module-grid">${[
    [
      "questions",
      "▦",
      "Ngân hàng câu hỏi",
      "Tìm kiếm, thêm và chỉnh sửa câu hỏi theo môn, khối, chủ đề.",
    ],
    [
      "createExam",
      "＋",
      "Tạo đề",
      "Lập ma trận, sinh đề gốc và xem trước nội dung.",
    ],
    [
      "shuffle",
      "⤨",
      "Trộn đề",
      "Thiết lập trộn câu hỏi và lựa chọn cho phòng thi.",
    ],
    [
      "rooms",
      "▣",
      "Phòng thi",
      "Tạo mã phòng, nhập danh sách học sinh và quản lý ca thi.",
    ],
    ["classes", "▤", "Lớp học", "Tạo lớp học và xem khối, năm học đã khai báo."],
  ]
    .map(
      ([id, icon, title, desc]) =>
        `<button class="module-card" data-page="${id}"><span class="module-icon">${icon}</span><h2>${title}</h2><p>${desc}</p><span class="arrow">Mở mục này　→</span></button>`,
    )
    .join("")}</div>`;
}
async function loadCatalog() {
  const [s, g] = await Promise.all([api("/api/subjects"), api("/api/grades")]);
  state.subjects = s.subjects || [];
  state.grades = g.grades || [];
}
async function loadQuestions() {
  const p = new URLSearchParams();
  for (const [key, param] of [
    ["qSubject", "subject_id"],
    ["qGrade", "grade_id"],
    ["qTopic", "topic_id"],
    ["qLesson", "lesson_id"],
    ["qType", "question_type"],
    ["qDiff", "difficulty"],
  ]) {
    const v = $("#" + key)?.value;
    if (v) p.set(param, v);
  }
  const term = $("#qSearch")?.value.trim();
  if (term) p.set("q", term);
  p.set("limit", "100");
  const d = await api("/api/questions?" + p);
  state.questions = d.questions || [];
  state.questionTotal = d.total || 0;
  renderQuestionsTable();
}
async function selectTopics(subjectId, gradeId, topicEl, lessonEl) {
  if (!subjectId || !gradeId) {
    topicEl.innerHTML = '<option value="">Chọn chủ đề</option>';
    lessonEl.innerHTML = '<option value="">Không chọn bài học</option>';
    return [];
  }
  const d = await api(
    `/api/topics?subject_id=${subjectId}&grade_id=${gradeId}`,
  );
  const list = d.topics || [];
  topicEl.innerHTML =
    '<option value="">Chọn chủ đề</option>' +
    list
      .map((x) => `<option value="${x.topic_id}">${esc(x.topic_name)}</option>`)
      .join("");
  lessonEl.innerHTML = '<option value="">Không chọn bài học</option>';
  return list;
}
async function selectLessons(topicId, lessonEl) {
  if (!topicId) {
    lessonEl.innerHTML = '<option value="">Không chọn bài học</option>';
    return;
  }
  const d = await api(`/api/lessons?topic_id=${topicId}`);
  lessonEl.innerHTML =
    '<option value="">Tất cả bài học</option>' +
    (d.lessons || [])
      .map(
        (x) => `<option value="${x.lesson_id}">${esc(x.lesson_name)}</option>`,
      )
      .join("");
}
function classPage() {
  return `${heading("DANH SÁCH LỚP", "Lớp học", "Tạo lớp để phân loại học sinh khi import danh sách vào phòng thi.")}<div class="panel"><div class="panel-head"><div><h2>Tạo lớp mới</h2><p>Giáo viên chỉ quản lý các lớp do mình tạo.</p></div></div><div class="panel-body"><form id="classForm" class="form-grid two"><label class="field">Tên lớp<input name="class_name" required maxlength="50" placeholder="Ví dụ: 10A1"></label><label class="field">Khối lớp<select name="grade_id" required>${state.grades.map((g) => `<option value="${g.grade_id}">${esc(g.grade_name)}</option>`).join("")}</select></label><label class="field">Năm học<input name="school_year" maxlength="20" placeholder="Ví dụ: 2026-2027"></label><div id="classError" class="error"></div><div class="form-actions"><button class="primary" type="submit">Tạo lớp</button></div></form></div></div><div class="panel"><div class="panel-head"><div><h2>Lớp đã tạo</h2><p>${state.classes.length} lớp</p></div></div><div class="table-wrap"><table><thead><tr><th>TÊN LỚP</th><th>KHỐI</th><th>NĂM HỌC</th><th>TRẠNG THÁI</th></tr></thead><tbody>${state.classes.length ? state.classes.map((c) => `<tr><td>${esc(c.class_name)}</td><td>${esc(state.grades.find((g) => g.grade_id === c.grade_id)?.grade_name || "—")}</td><td>${esc(c.school_year || "—")}</td><td>${c.is_active ? "Đang dùng" : "Đã tắt"}</td></tr>`).join("") : '<tr><td colspan="4" class="empty">Chưa có lớp học.</td></tr>'}</tbody></table></div></div>`;
}

function usersPage() {
  return `${heading("QUẢN TRỊ", "Tài khoản giáo viên", "Tạo tài khoản đăng nhập cho giáo viên.")}<div class="panel"><div class="panel-head"><div><h2>Tạo tài khoản mới</h2><p>Mật khẩu tối thiểu 8 ký tự. Hệ thống chỉ cho phép tạo tài khoản giáo viên.</p></div></div><div class="panel-body"><form id="userForm" class="form-grid two"><label class="field">Tên đăng nhập<input name="username" minlength="3" maxlength="50" required autocomplete="username" placeholder="Ví dụ: gv_toan"></label><label class="field">Họ và tên<input name="full_name" minlength="1" maxlength="100" required placeholder="Tên giáo viên"></label><label class="field">Mật khẩu<input name="password" type="password" minlength="8" maxlength="128" required autocomplete="new-password"></label><div id="userError" class="error"></div><div class="form-actions"><button class="primary" type="submit">Tạo tài khoản</button></div></form></div></div><div class="panel"><div class="panel-head"><div><h2>Tài khoản hiện có</h2><p>${state.users.length} tài khoản</p></div></div><div class="table-wrap"><table><thead><tr><th>TÊN ĐĂNG NHẬP</th><th>HỌ VÀ TÊN</th><th>VAI TRÒ</th><th>TRẠNG THÁI</th><th>NGÀY TẠO</th></tr></thead><tbody>${state.users.length ? state.users.map((u) => `<tr><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td><td>${u.role === "admin" ? "Quản trị viên" : "Giáo viên"}</td><td>${u.is_active ? "Đang hoạt động" : "Đã khóa"}</td><td>${esc(u.created_at)}</td></tr>`).join("") : '<tr><td colspan="5" class="empty">Chưa có tài khoản.</td></tr>'}</tbody></table></div></div>`;
}

function questionsPage() {
  return `${heading("THƯ VIỆN HỌC LIỆU", "Ngân hàng câu hỏi", "Tìm câu hỏi theo phạm vi kiến thức, sau đó xem hoặc cập nhật nội dung.", '<button class="primary" data-action="new-question">＋ Thêm câu hỏi</button>')}<div class="panel"><div class="panel-head"><div><h2>Phạm vi kiến thức</h2><p>Chọn môn và khối trước khi lọc chủ đề, bài học.</p></div><span class="pill">BƯỚC 1</span></div><div class="panel-body filters"><label class="field">Môn học<select id="qSubject"><option value="">Tất cả môn</option>${state.subjects.map((x) => `<option value="${x.subject_id}">${esc(x.subject_name)}</option>`).join("")}</select></label><label class="field">Khối lớp<select id="qGrade"><option value="">Tất cả khối</option>${state.grades.map((x) => `<option value="${x.grade_id}">${esc(x.grade_name)}</option>`).join("")}</select></label><label class="field">Chủ đề<select id="qTopic"><option value="">Tất cả chủ đề</option></select></label><label class="field">Bài học<select id="qLesson"><option value="">Tất cả bài học</option></select></label></div></div><div class="panel"><div class="panel-head"><div><h2>Danh sách câu hỏi</h2><p id="questionCount">Đang tải...</p></div><span class="muted">File nhập câu hỏi: Word (.docx)</span></div><div class="toolbar"><input id="qSearch" placeholder="⌕　Tìm nội dung câu hỏi..."><select id="qType"><option value="">Tất cả dạng câu</option>${Object.entries(
    typeName,
  )
    .map(([v, n]) => `<option value="${v}">${n}</option>`)
    .join(
      "",
    )}</select><select id="qDiff"><option value="">Mọi mức độ</option>${Object.entries(
    diffName,
  )
    .map(([v, n]) => `<option value="${v}">${v} · ${n}</option>`)
    .join(
      "",
    )}</select><button class="secondary" data-action="import-questions">Import Word (.docx)</button></div><div class="table-wrap"><table><thead><tr><th>NỘI DUNG</th><th>MÔN / KHỐI</th><th>DẠNG CÂU</th><th>MỨC ĐỘ</th><th>CHIA SẺ</th><th>TRẠNG THÁI</th><th></th></tr></thead><tbody id="questionRows"><tr><td colspan="7" class="empty">Đang tải...</td></tr></tbody></table></div><div class="panel-foot" id="questionFoot"></div></div>`;
}
function renderQuestionsTable() {
  const rows = $("#questionRows");
  if (!rows) return;
  $("#questionCount").textContent = `${state.questionTotal} câu hỏi`;
  $("#questionFoot").textContent = `Hiển thị ${state.questions.length} câu hỏi`;
  rows.innerHTML = state.questions.length
    ? state.questions.map((q) => `<tr><td><div class="qtext">${questionTextHtml(q.question_text)}</div><span class="sub">Q-${q.question_id}</span></td><td>${esc(state.subjects.find((x) => x.subject_id === q.subject_id)?.subject_name || "—")}<span class="sub">${esc(state.grades.find((x) => x.grade_id === q.grade_id)?.grade_name || "—")}</span></td><td><span class="pill">${typeName[q.question_type] || q.question_type}</span></td><td><span class="pill gray">${diffName[q.difficulty] || q.difficulty}</span></td><td><span class="pill ${q.is_public ? "green" : "gray"}">${q.is_public ? "Công khai" : "Riêng tư"}</span></td><td><span class="pill ${q.is_active ? "green" : "gray"}">${q.is_active ? "Đang dùng" : "Đã tắt"}</span></td><td><div class="row-actions">${q.can_manage ? `<button class="mini" data-action="edit-question" data-id="${q.question_id}">Sửa</button><button class="mini" data-action="toggle-question-visibility" data-id="${q.question_id}" data-public="${q.is_public ? 0 : 1}">${q.is_public ? "Chuyển riêng tư" : "Chuyển công khai"}</button><button class="mini" data-action="toggle-question" data-id="${q.question_id}" data-active="${q.is_active ? 0 : 1}">${q.is_active ? "Tắt" : "Bật"}</button>` : `<button class="mini" data-action="edit-question" data-id="${q.question_id}">Xem</button>`}</div></td></tr>`).join("")
    : '<tr><td colspan="7" class="empty">Không có câu hỏi phù hợp. Thử thay đổi bộ lọc hoặc thêm câu mới.</td></tr>';
}
function publicQuestionView(q) {
  const question = q.question;
  const answers = [...(q.options || []).filter((o) => o.is_correct).map((o) => `${o.option_key}. ${o.option_text}`), ...(q.accepted_answers || []).map((a) => a.answer_text)];
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">CÂU HỎI CÔNG KHAI</span><h2>Chỉ xem</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><p>${questionTextHtml(question.question_text)}</p><div>${(q.options || []).map((o) => `<p>${esc(o.option_key)}. ${esc(o.option_text)}${o.is_correct ? " ✓" : ""}</p>`).join("")}</div>${answers.length ? `<p><b>Đáp án:</b> ${answers.map(esc).join("; ")}</p>` : ""}<p class="muted">Câu hỏi này do giáo viên khác chia sẻ. Bạn có thể dùng trong đề của mình nhưng không thể sửa hoặc đổi quyền chia sẻ.</p></div></div>`;
}

function questionForm(q = null) {
  const opts = q?.options || [];
  const accepted = (q?.accepted_answers || [])
    .map((x) => x.answer_text)
    .join("; ");
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">NGÂN HÀNG CÂU HỎI</span><h2>${q ? "Sửa câu hỏi" : "Thêm câu hỏi"}</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><form id="questionForm" data-id="${q?.question?.question_id || ""}"><div class="form-grid two"><label class="field">Khối lớp<select name="grade_id" required>${state.grades.map((x) => `<option value="${x.grade_id}" ${x.grade_id === q?.question?.grade_id ? "selected" : ""}>${esc(x.grade_name)}</option>`).join("")}</select></label><label class="field">Môn học<select name="subject_id" required>${state.subjects.map((x) => `<option value="${x.subject_id}" ${x.subject_id === q?.question?.subject_id ? "selected" : ""}>${esc(x.subject_name)}</option>`).join("")}</select><button type="button" class="mini catalog-add" data-action="add-subject">＋ Thêm môn học</button></label><label class="field">Chủ đề<select name="topic_id" id="formTopic" required><option value="">Chọn chủ đề</option></select><button type="button" class="mini catalog-add" data-action="add-topic">＋ Thêm chủ đề</button></label><label class="field">Bài học<select name="lesson_id" id="formLesson"><option value="">Không chọn bài học</option></select></label><label class="field">Dạng câu<select name="question_type" id="formType">${Object.entries(
    typeName,
  )
    .map(
      ([v, n]) =>
        `<option value="${v}" ${v === q?.question?.question_type ? "selected" : ""}>${n}</option>`,
    )
    .join(
      "",
    )}</select></label><label class="field">Mức độ<select name="difficulty">${Object.entries(
    diffName,
  )
    .map(
      ([v, n]) =>
        `<option value="${v}" ${v === q?.question?.difficulty ? "selected" : ""}>${v} · ${n}</option>`,
    )
    .join(
      "",
    )}</select></label><label class="field" style="grid-column:1/-1">Nội dung<textarea name="question_text" required>${esc(q?.question?.question_text || "")}</textarea></label><label class="field" style="grid-column:1/-1">Giải thích / lời giải<textarea name="explanation">${esc(q?.question?.explanation || "")}</textarea></label></div><div class="spacer"></div><label class="inline-check"><input name="is_public" type="checkbox" ${q?.question?.is_public ? "checked" : ""}> Công khai câu hỏi với các giáo viên khác</label><p class="muted">Câu riêng tư chỉ bạn và admin xem được.</p><div id="answerFields"></div><div id="formError" class="error"></div><div class="form-actions"><button type="button" class="secondary" data-action="close-modal">Hủy</button><button class="primary" type="submit">${q ? "Lưu thay đổi" : "Tạo câu hỏi"}</button></div></form></div></div>`;
}
function paintAnswerFields(type, opts = [], accepted = "") {
  const el = $("#answerFields");
  if (!el) return;
  if (type === "short_answer") {
    el.innerHTML = `<label class="field">Đáp án được chấp nhận <small class="muted">Ngăn cách nhiều đáp án bằng dấu chấm phẩy</small><input name="accepted_answers" value="${esc(accepted)}" placeholder="Hà Nội; Ha Noi"></label>`;
    return;
  }
  el.innerHTML = `<div class="spacer"></div><div class="panel-head" style="padding:0 0 8px"><div><h2>${type === "true_false" ? "Các mệnh đề đúng / sai" : "Các phương án trả lời"}</h2><p>${type === "true_false" ? "Đánh dấu đúng cho từng mệnh đề." : "Chọn một đáp án đúng."}</p></div></div>${[
    "A",
    "B",
    "C",
    "D",
  ]
    .map((k, i) => {
      const o = opts.find((x) => x.option_key === k);
      const selected = Boolean(o);
      const controls =
        type === "true_false"
          ? '<div class="truth-options"><label><input type="radio" name="truth_' + k + '" value="true" ' + (selected && o.is_correct ? "checked" : "") + ' required> Mệnh đề đúng</label><label><input type="radio" name="truth_' + k + '" value="false" ' + (selected && !o.is_correct ? "checked" : "") + ' required> Mệnh đề sai</label></div>'
          : '<label class="inline-check" style="align-self:end;padding:11px"><input type="radio" name="correct" value="' + k + '" ' + (o?.is_correct ? "checked" : "") + '> Đáp án đúng</label>';
      return '<div class="form-grid two" style="margin:8px 0"><label class="field">Lựa chọn ' + k + '<input name="option_' + k + '" value="' + esc(o?.option_text || "") + '" ' + (type === "true_false" ? "required" : "") + '></label>' + controls + '</div>';
    })
    .join("")}`;
}
function examForm() {
  return `${heading("THIẾT KẾ ĐỀ", "Tạo đề", "Lập ma trận từ ngân hàng câu hỏi, sinh đề gốc rồi kiểm tra trước khi lưu.")}<div class="panel exam-builder"><div class="panel-head"><div><h2>Thông tin đề</h2><p>Nhập thông tin đơn vị, môn, khối và thời lượng.</p></div><span class="pill">BƯỚC 1</span></div><div class="panel-body"><form id="examForm"><div class="form-grid two"><label class="field">Cơ quan chủ quản<input name="supervising_authority" maxlength="255" placeholder="Ví dụ: Sở Giáo dục và Đào tạo"></label><label class="field">Tên trường<input name="school_name" maxlength="255" placeholder="Ví dụ: Trường THPT ..."></label><label class="field">Tên đề<input name="title" required maxlength="255" placeholder="Ví dụ: Kiểm tra giữa kỳ II"></label><label class="field">Thời lượng (phút)<input name="duration_minutes" type="number" min="1" value="45" required></label><label class="field">Môn học<select name="subject_id" required>${state.subjects.map((x) => `<option value="${x.subject_id}">${esc(x.subject_name)}</option>`).join("")}</select></label><label class="field">Khối lớp<select name="grade_id" required>${state.grades.map((x) => `<option value="${x.grade_id}">${esc(x.grade_name)}</option>`).join("")}</select></label></div><div class="panel-head" style="padding:20px 0 10px"><div><h2>Ma trận câu hỏi</h2><p>Mỗi dòng chọn chủ đề, độ khó, dạng câu và số lượng.</p></div><button type="button" class="secondary" data-action="add-matrix">＋ Thêm dòng</button></div><div id="matrixRows"></div><div id="examError" class="error"></div><div class="form-actions"><button class="primary" type="submit">Tạo đề và sinh đề gốc</button></div></form></div></div><div id="examPreview" class="exam-builder"></div>`;
}
function matrixRow() {
  return `<div class="matrix-row"><label class="field wide-cell">Chủ đề<select class="mTopic" required><option value="">Chọn chủ đề</option></select></label><label class="field">Bài học<select class="mLesson"><option value="">Tất cả bài</option></select></label><label class="field">Mức độ<select class="mDiff"><option>NB</option><option>TH</option><option>VD</option><option>VDC</option></select></label><label class="field">Dạng câu<select class="mType">${Object.entries(
    typeName,
  )
    .map(([v, n]) => `<option value="${v}">${n}</option>`)
    .join(
      "",
    )}</select></label><label class="field">Số câu<input class="mCount" type="number" min="1" value="1"></label><button type="button" class="mini" data-action="remove-matrix">Xóa</button></div>`;
}
function examList() {
  return `${heading("THIẾT KẾ ĐỀ", "Đề đã tạo", "Theo dõi đề nháp và đề đã sẵn sàng sử dụng.", '<button class="primary" data-page="createExam">＋ Tạo đề</button>')}<div class="panel"><div class="table-wrap"><table><thead><tr><th>TÊN ĐỀ</th><th>MÔN / KHỐI</th><th>THỜI LƯỢNG</th><th>TRẠNG THÁI</th><th></th></tr></thead><tbody>${state.exams.length ? state.exams.map((e) => `<tr><td><b>${esc(e.title)}</b><span class="sub">Mã đề ${e.exam_id}</span></td><td>${esc(state.subjects.find((x) => x.subject_id === e.subject_id)?.subject_name || "—")} · ${esc(state.grades.find((x) => x.grade_id === e.grade_id)?.grade_name || "—")}</td><td>${e.duration_minutes} phút</td><td><span class="pill ${e.status === "ready" ? "green" : "gray"}">${e.status === "ready" ? "Sẵn sàng" : "Bản nháp"}</span></td><td><div class="row-actions"><button class="mini" data-action="preview-exam" data-id="${e.exam_id}">Xem đề</button><button class="mini" data-action="download-exam" data-id="${e.exam_id}">Tải đề gốc</button></div></td></tr>`).join("") : '<tr><td colspan="5" class="empty">Chưa có đề. Bắt đầu bằng cách tạo đề mới.</td></tr>'}</tbody></table></div></div>`;
}
function shufflePage() {
  const ready = state.exams.filter((x) => x.status === "ready");
  return `${heading("MÃ ĐỀ VÀ TRỘN", "Trộn đề", "Chọn đề gốc, số lượng phiên bản và cách xáo câu hỏi, phương án.")}<div class="panel shuffle-settings"><div class="panel-head"><div><h2>Thiết lập mã đề</h2><p>Mỗi học sinh được chia vào một mã trong số phiên bản đã chọn.</p></div><span class="pill">CẤU HÌNH PHÒNG</span></div><div class="panel-body"><div class="form-grid two"><label class="field">Tiền tố mã đề<input id="paperCodePrefix" maxlength="8" value="${esc(state.shuffle.paper_code_prefix)}" placeholder="VD: M"></label><label class="field">Độ dài phần số<input id="paperCodeLength" type="number" min="1" max="8" value="${state.shuffle.paper_code_length}"></label><label class="field">Số đề muốn trộn<input id="paperVariantCount" type="number" min="1" max="100" value="${state.shuffle.paper_variant_count}"></label></div><div class="spacer"></div><label class="field">Đề thi<select id="shuffleExam"><option value="">Chọn đề đã sẵn sàng</option>${ready.map((e) => `<option value="${e.exam_id}">${esc(e.title)} · ${e.duration_minutes} phút</option>`).join("")}</select></label><div class="spacer"></div><label class="inline-check"><input type="checkbox" id="shuffleQuestions" ${state.shuffle.shuffle_questions ? "checked" : ""}> Trộn thứ tự câu hỏi</label><div class="spacer"></div><label class="inline-check"><input type="checkbox" id="shuffleOptions" ${state.shuffle.shuffle_options ? "checked" : ""}> Trộn thứ tự phương án trắc nghiệm</label><div class="spacer"></div><div class="notice">Mã đề được gán lần lượt theo danh sách học sinh nhập vào phòng. Hệ thống giữ đề gốc để đối chiếu kết quả.</div><button class="primary" data-action="use-shuffle">Dùng cấu hình này khi tạo phòng</button><div id="shuffleInfo" class="muted" style="margin-top:12px"></div></div></div>`;
}
function roomsPage() {
  return `${heading("TỔ CHỨC THI", "Phòng thi", "Tạo mã vào thi, thêm học sinh và theo dõi trạng thái các ca thi.", '<button class="primary" data-action="new-room">＋ Tạo phòng thi</button>')}<div class="panel"><div class="table-wrap"><table><thead><tr><th>PHÒNG THI</th><th>ĐỀ</th><th>MÃ PHÒNG</th><th>LỊCH THI</th><th>TRẠNG THÁI</th><th>THAO TÁC</th></tr></thead><tbody>${state.sessions.length ? state.sessions.map((s) => `<tr><td><b>${esc(s.session_name)}</b><span class="sub">Phòng #${s.session_id}</span></td><td>${esc(state.exams.find((x) => x.exam_id === s.exam_id)?.title || "Đề #" + s.exam_id)}</td><td><b>${esc(s.access_code || "—")}</b></td><td>${esc(fmtDate(s.start_time))}</td><td><span class="pill ${s.status === "ongoing" ? "green" : "gray"}">${{ scheduled: "Đã lên lịch", ongoing: "Đang thi", completed: "Đã kết thúc", cancelled: "Đã hủy" }[s.status] || s.status}</span></td><td><button class="mini" data-action="manage-room" data-id="${s.session_id}">Quản lý</button> ${s.status === "scheduled" ? `<button class="mini" data-action="room-status" data-id="${s.session_id}" data-status="ongoing">Mở phòng</button>` : s.status === "ongoing" ? `<button class="mini" data-action="room-status" data-id="${s.session_id}" data-status="completed">Kết thúc</button>` : s.status === "completed" ? `<button class="mini" data-action="download-results" data-id="${s.session_id}">Lấy file kết quả</button>` : ""}</td></tr>`).join("") : '<tr><td colspan="6" class="empty">Chưa có phòng thi nào.</td></tr>'}</tbody></table></div></div>`;
}
function roomForm() {
  const ready = state.exams.filter((x) => x.status === "ready");
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">TỔ CHỨC THI</span><h2>Tạo phòng thi</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><form id="roomForm"><div class="form-grid two"><label class="field">Tên phòng<input name="session_name" required placeholder="Ví dụ: Ca sáng 10A1"></label><label class="field">Đề thi<select name="exam_id" required><option value="">Chọn đề đã lưu</option>${ready.map((e) => `<option value="${e.exam_id}" ${state.selectedExam === e.exam_id ? "selected" : ""}>${esc(e.title)} · ${e.duration_minutes} phút</option>`).join("")}</select></label><label class="field">Bắt đầu<input name="start_time" type="datetime-local"></label><label class="field">Kết thúc<input name="end_time" type="datetime-local"></label><p class="muted" style="grid-column:1/-1">Đặt giờ bắt đầu để phòng tự mở đúng lịch; bỏ trống nếu muốn mở thủ công.</p><label class="field" style="grid-column:1/-1">Mật khẩu phòng (nếu cần)<input name="password" type="password" minlength="4"></label></div><div class="spacer"></div><label class="inline-check"><input type="checkbox" name="shuffle_questions" ${state.shuffle.shuffle_questions ? "checked" : ""}> Trộn câu hỏi</label><div class="spacer"></div><label class="inline-check"><input type="checkbox" name="shuffle_options" ${state.shuffle.shuffle_options ? "checked" : ""}> Trộn phương án</label><div id="roomError" class="error"></div><div class="form-actions"><button type="button" class="secondary" data-action="close-modal">Hủy</button><button class="primary">Tạo phòng</button></div></form></div></div>`;
}
function roomManage(s, roster = []) {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">QUẢN LÝ CA THI</span><h2>${esc(s.session_name)}</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><div class="notice">Mã phòng dành cho học sinh</div><div class="join-code">${esc(s.access_code || "—")}</div><p class="muted">${esc(s.join_url || "")}</p><p class="muted">Trạng thái: <b>${esc(s.status)}</b></p><div class="room-qr"><img src="${esc(s.qr_data_url || "")}" alt="QR vào phòng thi"><a class="secondary" href="${esc(s.qr_data_url || "")}" download="qr-phong-${s.session_id}.png">Tải QR dạng ảnh</a><p class="muted">QR chỉ cho phép vào trong 15 phút từ giờ bắt đầu. Học sinh đã vào tiếp tục làm bài bình thường.</p></div><section class="panel-body"><h3>Mật khẩu phòng</h3><p class="muted">${s.has_password ? "Phòng đang có mật khẩu. Mật khẩu cũ được mã hóa nên không xem lại được; bạn có thể đặt mật khẩu mới." : "Phòng hiện không có mật khẩu."}</p><form id="roomPasswordForm" data-id="${s.session_id}" class="form-grid two"><label class="field">Mật khẩu mới<input name="password" type="password" minlength="8" maxlength="128" required placeholder="Ít nhất 8 ký tự"></label><button class="secondary" style="align-self:end">Đặt mật khẩu mới</button><div id="passwordError" class="error"></div></form></section><div class="form-actions"><a class="secondary" href="${esc(state.base)}/api/templates/students.docx" target="_blank" rel="noreferrer">Tải mẫu danh sách</a><button class="primary" data-action="import-students" data-id="${s.session_id}">Import học sinh</button>${s.status === "completed" || s.status === "ongoing" ? `<button class="secondary" data-action="download-results" data-id="${s.session_id}">Lấy file kết quả</button>` : ""}</div><section class="panel-body"><h3>Danh sách học sinh (${roster.length})</h3>${roster.length ? `<div class="table-wrap"><table><thead><tr><th>MÃ HỌC SINH</th><th>HỌ VÀ TÊN</th><th>LỚP</th><th>TRẠNG THÁI</th></tr></thead><tbody>${roster.map((x) => `<tr><td>${esc(x.student_code)}</td><td>${esc(x.full_name)}</td><td>${esc(x.class_name || "—")}</td><td>${esc({ registered: "Chưa vào thi", in_progress: "Đang làm bài", submitted: "Đã nộp", absent: "Vắng", disqualified: "Bị loại" }[x.status] || x.status)}</td></tr>`).join("")}</tbody></table></div>` : '<p class="muted">Chưa có học sinh trong phòng. Hãy import danh sách.</p>'}</section><div id="rosterResult"></div></div></div>`;
}
function joinPage() {
  return `<main class="student-stage"><div class="student-box"><button class="back-link" data-page="home">←　Trang chủ</button><div class="login-card"><h1>Vào phòng thi</h1><p>Nhập địa chỉ máy chủ, mã phòng và mã học sinh được giáo viên cung cấp.</p><form id="joinForm"><label class="field">Máy chủ<select name="serverPreset" id="serverPreset"><option value="custom">Nhập địa chỉ</option><option value="current">Máy chủ hiện tại (${esc(state.base)})</option></select></label><label class="field">Địa chỉ backend<input name="base" id="joinBase" value="${esc(state.base)}" required placeholder="http://192.168.1.10:8000"></label><div class="form-grid two"><label class="field">Mã phòng<input name="access_code" required autocomplete="off" value="${esc(new URLSearchParams(location.search).get("code") || "")}" placeholder="VD: A1B2C3D4E5F60708"></label><label class="field">Mã học sinh / SBD<input name="student_code" required autocomplete="off"></label></div><label class="field">Mật khẩu phòng<input name="password" type="password" placeholder="Nếu phòng có mật khẩu"></label><div id="joinError" class="error"></div><button class="primary">Vào thi</button></form></div></div></main>`;
}
function examPage() {
  if (!state.exam)
    return `<main class="student-stage"><div class="student-box"><div class="panel question-card">Đang tải bài thi…</div></div></main>`;
  const q = state.exam.current;
  const ans = state.answers[q?.question?.question_id] ?? "";
  let answer = "";
  if (q) {
    if (q.question.question_type === "multiple_choice")
      answer = q.options
        .map(
          (o) =>
            `<label class="answer-option"><input type="radio" name="answer" value="${esc(o.option_key)}" ${ans === o.option_key ? "checked" : ""}><span><b>${esc(o.option_key)}.</b> ${esc(o.option_text)}</span></label>`,
        )
        .join("");
    else if (q.question.question_type === "true_false") {
      let obj = {};
      try {
        obj = JSON.parse(ans || "{}");
      } catch {}
      answer = q.options
        .map(
          (o) =>
            `<div class="answer-option"><b>${esc(o.option_key)}. ${esc(o.option_text)}</b><label><input type="radio" name="tf_${esc(o.option_key)}" value="true" ${obj[o.option_key] === true ? "checked" : ""}> Đúng</label><label><input type="radio" name="tf_${esc(o.option_key)}" value="false" ${obj[o.option_key] === false ? "checked" : ""}> Sai</label></div>`,
        )
        .join("");
    } else
      answer = `<label class="field">Câu trả lời<textarea id="shortAnswer" maxlength="500">${esc(ans)}</textarea></label>`;
  }
  return `<main class="student-stage"><div class="student-box"><div class="topbar" style="border:1px solid var(--line);border-radius:10px;margin-bottom:14px"><b>${esc(state.student?.full_name || "Bài thi")}</b><span>Mã đề ${esc(state.exam.me?.paper_code || "—")}</span></div><div class="exam-layout"><section class="panel question-card"><div class="eyebrow">CÂU ${state.questionIndex} / ${state.exam.me.question_ids.length} · ${typeName[q?.question?.question_type] || ""}</div><h2>${questionTextHtml(q?.question?.question_text || "")}</h2>${(
    q?.media || []
  )
    .filter((m) => m.image_url)
    .map(
      (m) =>
        `<img src="${esc(state.base + m.image_url)}" alt="Hình câu hỏi" style="max-width:100%;max-height:360px">`,
    )
    .join(
      "",
    )}<div id="answerArea">${answer}</div><div class="form-actions"><button class="secondary" data-action="previous-question" ${state.questionIndex <= 1 ? "disabled" : ""}>← Câu trước</button><button class="primary" data-action="next-question">${state.questionIndex >= state.exam.me.question_ids.length ? "Kiểm tra bài" : "Câu tiếp"} →</button></div></section><aside><div class="panel"><div class="panel-head"><div><span class="muted">THỜI GIAN CÒN LẠI</span><div class="timer" id="timer">--:--</div></div></div><div class="panel-body"><div class="progress"><span style="width:${Math.round((state.questionIndex / state.exam.me.question_ids.length) * 100)}%"></span></div><p class="muted">${Object.keys(state.answers).length} câu đã trả lời</p></div></div><div class="panel"><div class="panel-head"><div><h2>Danh sách câu</h2><p>Chọn số câu để di chuyển.</p></div></div><div class="panel-body"><div class="question-nav">${state.exam.me.question_ids.map((id, i) => `<button class="${state.questionIndex === i + 1 ? "current" : ""} ${state.answers[id] !== undefined ? "answered" : ""}" data-action="go-question" data-index="${i + 1}">${i + 1}</button>`).join("")}</div><div class="form-actions"><button class="danger" data-action="submit-exam">Nộp bài</button></div></div></div></aside></div></div></main>`;
}
function render() {
  const app = $("#app");
  if (state.page === "exam" && !state.studentToken) state.page = "join";
  sessionStorage.setItem("appLastPage", state.page);
  if (state.page === "users" && state.user?.role !== "admin") state.page = "dashboard";
  if (
    !state.token &&
    [
      "dashboard",
      "questions",
      "createExam",
      "exams",
      "shuffle",
      "rooms",
      "classes",
      "users",
    ].includes(state.page)
  ) {
    state.page = "login";
  }
  app.innerHTML =
    state.page === "home"
      ? landing()
      : state.page === "login"
        ? login()
        : state.page === "join"
          ? joinPage()
          : state.page === "exam"
            ? examPage()
            : appShell(
                {
                  dashboard,
                  dashboard: dashboard,
                  questions: questionsPage,
                  createExam: examForm,
                  exams: examList,
                  shuffle: shufflePage,
                  rooms: roomsPage,
                  classes: classPage,
                  users: usersPage,
                }[state.page]?.() || dashboard(),
              );
}
function openModal(html) {
  const m = $("#modal");
  m.innerHTML = html;
  m.classList.remove("hidden");
}
function closeModal() {
  $("#modal").classList.add("hidden");
  $("#modal").innerHTML = "";
}
async function refreshLists() {
  try {
    const [e, s] = await Promise.all([api("/api/exams"), api("/api/sessions")]);
    state.exams = e.exams || [];
    state.sessions = s.sessions || [];
  } catch (err) {
    toast(err.message);
  }
}
async function refreshDashboard() {
  try {
    const d = await api("/api/questions?limit=1");
    state.questionTotal = d.total || 0;
    await refreshLists();
  } catch (err) {
    toast(err.message);
  }
}
async function go(page) {
  state.page = page;
  render();
  if (page === "questions") {
    await loadQuestions();
  }
  if (page === "classes") {
    const d = await api("/api/classes");
    state.classes = d.classes || [];
    render();
  }
  if (page === "users" && state.user?.role === "admin") {
    const d = await api("/api/users");
    state.users = d.users || [];
    render();
  }
  if (page === "exams" || page === "shuffle" || page === "rooms") {
    await refreshLists();
    render();
  }
  if (page === "shuffle" && state.selectedExam) {
    const el = $("#shuffleExam");
    if (el) el.value = state.selectedExam;
  }
  if (page === "rooms" && state.selectedExam && state.prefillRoom) {
    state.prefillRoom = false;
    openModal(roomForm());
  }
  if (page === "dashboard") await refreshDashboard();
  if (page === "createExam") {
    const box = document.createElement("div");
    box.innerHTML = matrixRow();
    const row = box.firstElementChild;
    $("#matrixRows").append(row);
    await initMatrixRow(row);
  }
}
function formDataObject(form) {
  return Object.fromEntries(new FormData(form).entries());
}
async function startExam() {
  const d = await api("/api/exam/me", {}, state.studentToken);
  state.exam = { me: d, current: null };
  state.answers = d.answers || {};
  state.questionIndex = 1;
  state.page = "exam";
  await loadExamQuestion();
  render();
  startTimer(d.remaining_seconds);
}
async function loadExamQuestion() {
  const d = await api(
    `/api/exam/questions/${state.questionIndex}`,
    {},
    state.studentToken,
  );
  state.exam.current = d;
  render();
}
function startTimer(seconds) {
  clearInterval(state.timer);
  state.remaining = Math.max(0, seconds | 0);
  const tick = () => {
    const el = $("#timer");
    if (el) {
      const m = Math.floor(state.remaining / 60),
        s = state.remaining % 60;
      el.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
      if (state.remaining <= 60) el.style.color = "var(--red)";
    }
    if (state.remaining <= 0) {
      clearInterval(state.timer);
      submitExam(true);
    }
    state.remaining--;
  };
  tick();
  state.timer = setInterval(tick, 1000);
}
async function saveCurrentAnswer() {
  const q = state.exam?.current;
  if (!q) return;
  let answer = "";
  if (q.question.question_type === "multiple_choice")
    answer = $("input[name=answer]:checked")?.value || "";
  else if (q.question.question_type === "true_false") {
    const obj = {};
    for (const o of q.options) {
      const v = $(`input[name="tf_${o.option_key}"]:checked`)?.value;
      if (v !== undefined) obj[o.option_key] = v === "true";
    }
    answer = JSON.stringify(obj);
  } else answer = $("#shortAnswer")?.value.trim() || "";
  if (answer) {
    await api(
      "/api/exam/answers",
      {
        method: "PUT",
        body: JSON.stringify({
          question_id: q.question.question_id,
          answer_text: answer,
        }),
      },
      state.studentToken,
    );
    state.answers[q.question.question_id] = answer;
  } else if (state.answers[q.question.question_id] !== undefined) {
    await api(
      "/api/exam/answers",
      {
        method: "PUT",
        body: JSON.stringify({
          question_id: q.question.question_id,
          answer_text: "",
        }),
      },
      state.studentToken,
    );
    delete state.answers[q.question.question_id];
  }
}
async function submitExam(auto = false) {
  if (
    !auto &&
    !confirm("Nộp bài thi? Bạn sẽ không thể chỉnh sửa câu trả lời sau đó.")
  )
    return;
  try {
    await saveCurrentAnswer();
    await api("/api/exam/submit", { method: "POST" }, state.studentToken);
    clearInterval(state.timer);
    state.page = "home";
    state.studentToken = "";
    sessionStorage.removeItem("studentToken");
    state.student = null;
    state.exam = null;
    render();
    openModal(
      `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">ĐÃ NỘP BÀI</span><h2>${auto ? "Bài thi đã được tự động nộp" : "Bài thi đã được ghi nhận"}</h2></div></div><div class="dialog-body"><p>Câu trả lời của bạn đã được lưu.</p><div class="form-actions"><button class="primary" data-action="close-modal">Hoàn tất</button></div></div></div>`,
    );
  } catch (err) {
    toast(err.message);
  }
}
function attachPageEvents() {
  const app = $("#app"),
    modalEl = $("#modal");
  const click = async (e) => {
    const b = e.target.closest("[data-page],[data-action]");
    if (!b) return;
    const page = b.dataset.page,
      act = b.dataset.action;
    if (page) {
      await go(page);
      return;
    }
    try {
      if (act === "teacher") {
        state.page = "login";
        render();
      } else if (act === "logout") {
        state.token = "";
        state.user = null;
        sessionStorage.removeItem("examToken");
        sessionStorage.removeItem("examUser");
        state.page = "home";
        render();
      } else if (act === "close-modal") closeModal();
      else if (act === "new-question") {
        state.editing = null;
        openModal(questionForm());
        await initQuestionForm();
      } else if (act === "edit-question") {
        const q = await api(`/api/questions/${b.dataset.id}`);
        if (q.can_manage) {
          state.editing = q;
          openModal(questionForm(q));
          await initQuestionForm(q);
        } else {
          openModal(publicQuestionView(q));
        }
      } else if (act === "add-subject") {
        const name = prompt("Tên môn học mới:")?.trim();
        if (name) {
          const created = await api("/api/subjects", {
              method: "POST",
              body: JSON.stringify({ subject_name: name }),
            }),
            form = $("#questionForm"),
            select = form.elements.subject_id;
          state.subjects.push({
            subject_id: created.subject_id,
            subject_name: name,
          });
          select.insertAdjacentHTML(
            "beforeend",
            `<option value="${created.subject_id}">${esc(name)}</option>`,
          );
          const filter = $("#qSubject");
          if (filter)
            filter.insertAdjacentHTML(
              "beforeend",
              `<option value="${created.subject_id}">${esc(name)}</option>`,
            );
          select.value = created.subject_id;
          await selectTopics(
            select.value,
            form.elements.grade_id.value,
            $("#formTopic"),
            $("#formLesson"),
          );
          toast("Đã thêm môn học");
        }
      } else if (act === "add-topic") {
        const form = $("#questionForm"),
          name = prompt("Tên chủ đề mới:")?.trim();
        if (!name) return;
        if (!form.elements.subject_id.value || !form.elements.grade_id.value)
          throw Error("Chọn môn học và khối lớp trước khi thêm chủ đề.");
        const created = await api("/api/topics", {
            method: "POST",
            body: JSON.stringify({
              subject_id: Number(form.elements.subject_id.value),
              grade_id: Number(form.elements.grade_id.value),
              topic_name: name,
            }),
          }),
          topic = $("#formTopic");
        topic.insertAdjacentHTML(
          "beforeend",
          `<option value="${created.topic_id}">${esc(created.topic_name)}</option>`,
        );
        topic.value = created.topic_id;
        await selectLessons(topic.value, $("#formLesson"));
        toast("Đã thêm chủ đề");
      } else if (act === "add-lesson") {
        const topic = $("#formTopic");
        if (!topic.value) throw Error("Chọn chủ đề trước khi thêm bài học.");
        const name = prompt("Tên bài học mới:")?.trim();
        if (!name) return;
        const list = await api(`/api/lessons?topic_id=${topic.value}`),
          order =
            Math.max(0, ...(list.lessons || []).map((x) => x.lesson_order)) + 1,
          created = await api("/api/lessons", {
            method: "POST",
            body: JSON.stringify({
              topic_id: Number(topic.value),
              lesson_name: name,
              lesson_order: order,
            }),
          }),
          lesson = $("#formLesson");
        lesson.insertAdjacentHTML(
          "beforeend",
          `<option value="${created.lesson_id}">${esc(created.lesson_name)}</option>`,
        );
        lesson.value = created.lesson_id;
        toast("Đã thêm bài học");
      } else if (act === "toggle-question-visibility") {
        const isPublic = !!+b.dataset.public;
        await api(`/api/questions/${b.dataset.id}/visibility`, {
          method: "PATCH",
          body: JSON.stringify({ is_public: isPublic }),
        });
        await loadQuestions();
        toast(isPublic ? "Đã công khai câu hỏi" : "Đã chuyển câu hỏi sang riêng tư");
      } else if (act === "toggle-question") {
        await api(`/api/questions/${b.dataset.id}/active`, {
          method: "PATCH",
          body: JSON.stringify({ is_active: !!+b.dataset.active }),
        });
        await loadQuestions();
        toast("Đã cập nhật trạng thái");
      } else if (act === "import-questions") {
        openModal(importQuestionsForm());
        await initImportQuestionsForm();
      } else if (act === "download-question-template") {
        await downloadFile("/api/templates/questions.docx", "mau_cau_hoi.docx");
      } else if (act === "add-matrix") {
        const box = document.createElement("div");
        box.innerHTML = matrixRow();
        const row = box.firstElementChild;
        $("#matrixRows").append(row);
        await initMatrixRow(row);
      } else if (act === "remove-matrix") b.closest(".matrix-row").remove();
      else if (act === "preview-exam") {
        const d = await api(`/api/exams/${b.dataset.id}`);
        openModal(previewExam(d));
      } else if (act === "save-exam") {
        await saveExamReady(Number(b.dataset.id));
        toast("Đã lưu đề, sẵn sàng mở phòng thi");
      } else if (act === "download-exam") {
        await saveExamReady(Number(b.dataset.id));
        await downloadFile(
          `/api/exams/${b.dataset.id}/export.docx`,
          `de_goc_${b.dataset.id}.docx`,
        );
        toast("Đã tải file đề gốc");
      } else if (act === "download-results") {
        await downloadFile(
          `/api/sessions/${b.dataset.id}/results.xlsx`,
          `ket_qua_phong_${b.dataset.id}.xlsx`,
        );
        toast("Đã tải file kết quả");
      } else if (act === "open-shuffle") {
        await saveExamReady(Number(b.dataset.id));
        state.selectedExam = Number(b.dataset.id);
        closeModal();
        await go("shuffle");
      } else if (act === "use-shuffle") {
        state.selectedExam = Number($("#shuffleExam").value) || null;
        const prefix = $("#paperCodePrefix").value.trim().toUpperCase(),
          length = Number($("#paperCodeLength").value),
          count = Number($("#paperVariantCount").value),
          shuffleQuestions = $("#shuffleQuestions").checked,
          shuffleOptions = $("#shuffleOptions").checked;
        if (!state.selectedExam) return toast("Chọn một đề đã lưu trước.");
        if (prefix && !/^[A-Z0-9]+$/.test(prefix))
          throw Error("Tiền tố mã đề chỉ gồm chữ cái không dấu và chữ số.");
        if (
          !Number.isInteger(length) ||
          length < 1 ||
          length > 8 ||
          !Number.isInteger(count) ||
          count < 1 ||
          count > 100 ||
          count > 10 ** length
        )
          throw Error("Kiểm tra độ dài mã đề và số đề muốn trộn.");
        if (count > 1 && !shuffleQuestions && !shuffleOptions)
          throw Error(
            "Bật trộn câu hỏi hoặc phương án để tạo nhiều mã đề khác nhau.",
          );
        state.shuffle = {
          shuffle_questions: shuffleQuestions,
          shuffle_options: shuffleOptions,
          paper_code_prefix: prefix,
          paper_code_length: length,
          paper_variant_count: count,
        };
        state.prefillRoom = true;
        await go("rooms");
      } else if (act === "new-room") {
        state.selectedExam = null;
        openModal(roomForm());
      } else if (act === "manage-room") {
        const [d, r] = await Promise.all([
          api(`/api/sessions/${b.dataset.id}`),
          api(`/api/sessions/${b.dataset.id}/students`),
        ]);
        state.selectedSession = d;
        openModal(roomManage(d, r.students || []));
      } else if (act === "room-status") {
        await api(`/api/sessions/${b.dataset.id}/status`, {
          method: "POST",
          body: JSON.stringify({ status: b.dataset.status }),
        });
        await refreshLists();
        render();
        if (b.dataset.status === "completed") {
          openModal(resultsReadyDialog(Number(b.dataset.id)));
          toast("Đã chấm bài. Tải file kết quả về máy.");
        } else toast("Đã cập nhật phòng thi");
      } else if (act === "import-students")
        await importStudentsFormFor(Number(b.dataset.id));
      else if (act === "previous-question" || act === "next-question") {
        await saveCurrentAnswer();
        if (
          act === "next-question" &&
          state.questionIndex === state.exam.me.question_ids.length
        )
          return openModal(confirmSubmitForm());
        state.questionIndex = Math.max(
          1,
          Math.min(
            state.exam.me.question_ids.length,
            state.questionIndex + (act === "next-question" ? 1 : -1),
          ),
        );
        await loadExamQuestion();
      } else if (act === "go-question") {
        await saveCurrentAnswer();
        state.questionIndex = Number(b.dataset.index);
        await loadExamQuestion();
      } else if (act === "submit-exam") await submitExam();
      else if (act === "confirm-submit") {
        closeModal();
        await submitExam();
      }
    } catch (err) {
      const target = $("#examError") || $("#roomError") || $("#formError");
      if (target) target.textContent = err.message;
      else toast(err.message);
    }
  };
  const change = async (e) => {
    try {
      if (e.target.id === "qSubject" || e.target.id === "qGrade") {
        const topic = $("#qTopic"),
          lesson = $("#qLesson"),
          list = await selectTopics(
            $("#qSubject").value,
            $("#qGrade").value,
            topic,
            lesson,
          );
        topic.innerHTML =
          '<option value="">Tất cả chủ đề</option>' +
          list
            .map(
              (x) =>
                `<option value="${x.topic_id}">${esc(x.topic_name)}</option>`,
            )
            .join("");
        await loadQuestions();
      } else if (e.target.id === "qTopic") {
        await selectLessons(e.target.value, $("#qLesson"));
        await loadQuestions();
      } else if (["qLesson", "qType", "qDiff"].includes(e.target.id))
        await loadQuestions();
      else if (e.target.id === "formType")
        paintAnswerFields(
          e.target.value,
          state.editing?.options || [],
          (state.editing?.accepted_answers || [])
            .map((x) => x.answer_text)
            .join("; "),
        );
      else if (e.target.id === "serverPreset")
        $("#joinBase").disabled = e.target.value === "current";
      else if (e.target.id === "importTopic")
        await selectLessons(e.target.value, $("#importLesson"));
    } catch (err) {
      toast(err.message);
    }
  };
  const submit = async (e) => {
    e.preventDefault();
    const form = e.target;
    try {
      if (form.id === "loginForm") {
        const d = formDataObject(form);
        state.base = d.base.replace(/\/$/, "");
        localStorage.setItem("examBase", state.base);
        const login = await api(
          "/api/login",
          {
            method: "POST",
            body: JSON.stringify({
              username: d.username,
              password: d.password,
            }),
          },
          "",
        );
        state.token = login.access_token;
        state.user = login.user;
        sessionStorage.setItem("examToken", state.token);
        sessionStorage.setItem("examUser", JSON.stringify(state.user));
        await loadCatalog();
        await go("dashboard");
      } else if (form.id === "userForm") {
        const d = formDataObject(form);
        await api("/api/users", {
          method: "POST",
          body: JSON.stringify({ username: d.username.trim(), full_name: d.full_name.trim(), password: d.password, role: "teacher" }),
        });
        const list = await api("/api/users");
        state.users = list.users || [];
        render();
        toast("Đã tạo tài khoản giáo viên");
      } else if (form.id === "classForm") {
        const d = formDataObject(form);
        await api("/api/classes", {
          method: "POST",
          body: JSON.stringify({ class_name: d.class_name.trim(), grade_id: Number(d.grade_id), school_year: d.school_year.trim() || null }),
        });
        const list = await api("/api/classes");
        state.classes = list.classes || [];
        render();
        toast("Đã tạo lớp học");
      } else if (form.id === "questionForm") {
        await saveQuestion(form);
        closeModal();
        await loadQuestions();
        toast("Đã lưu câu hỏi");
      } else if (form.id === "examForm") await createExam(form);
      else if (form.id === "roomForm") await createRoom(form);
      else if (form.id === "roomPasswordForm") {
        await api(`/api/sessions/${form.dataset.id}/password`, {
          method: "PUT",
          body: JSON.stringify({ password: form.elements.password.value }),
        });
        toast("Đã cập nhật mật khẩu phòng thi");
        form.reset();
        state.selectedSession.has_password = true;
        const note = form.previousElementSibling;
        if (note)
          note.textContent =
            "Đã đặt mật khẩu mới. Mật khẩu cũ không thể khôi phục.";
      } else if (form.id === "joinForm") {
        const d = formDataObject(form);
        state.base = (
          d.serverPreset === "current" ? state.base : d.base
        ).replace(/\/$/, "");
        localStorage.setItem("examBase", state.base);
        const joined = await api(
          "/api/exam/join",
          {
            method: "POST",
            body: JSON.stringify({
              access_code: d.access_code,
              student_code: d.student_code,
              password: d.password || null,
            }),
          },
          "",
        );
        state.studentToken = joined.access_token;
        state.student = {
          full_name: joined.full_name,
          class_name: joined.class_name,
        };
        sessionStorage.setItem("studentToken", state.studentToken);
        await startExam();
      } else if (form.id === "importStudentsForm")
        await previewStudentImport(form);
      else if (form.id === "importQuestionsForm")
        await previewQuestionImport(form);
    } catch (err) {
      const el =
        $("#loginError") ||
        $("#joinError") ||
        $("#formError") ||
        $("#examError") ||
        $("#roomError") ||
        $("#passwordError") ||
        $("#classError") ||
        $("#userError");
      if (el) el.textContent = err.message;
      else toast(err.message);
    }
  };
  app.onclick = click;
  modalEl.onclick = click;
  app.onchange = change;
  modalEl.onchange = change;
  app.oninput = (e) => {
    if (e.target.id === "qSearch") {
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(
        () => loadQuestions().catch((x) => toast(x.message)),
        250,
      );
    }
  };
  app.onsubmit = submit;
  modalEl.onsubmit = submit;
}
async function initQuestionForm(q = null) {
  const form = $("#questionForm"),
    grade = form.elements.grade_id.value,
    subject = form.elements.subject_id.value,
    topic = $("#formTopic"),
    lesson = $("#formLesson");
  if (!$("[data-action=add-lesson]", lesson.parentElement)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mini catalog-add";
    button.dataset.action = "add-lesson";
    button.textContent = "＋ Thêm bài học";
    lesson.insertAdjacentElement("afterend", button);
  }
  await selectTopics(subject, grade, topic, lesson);
  if (q?.question) {
    topic.value = q.question.topic_id;
    await selectLessons(topic.value, lesson);
    lesson.value = q.question.lesson_id || "";
  }
  form.elements.subject_id.onchange = async () =>
    selectTopics(
      form.elements.subject_id.value,
      form.elements.grade_id.value,
      topic,
      lesson,
    );
  form.elements.grade_id.onchange = form.elements.subject_id.onchange;
  topic.onchange = () => selectLessons(topic.value, lesson);
  paintAnswerFields(
    form.elements.question_type.value,
    q?.options || [],
    (q?.accepted_answers || []).map((x) => x.answer_text).join("; "),
  );
}
function saveQuestion(form) {
  const fd = new FormData(form),
    type = fd.get("question_type"),
    opts = [],
    accepted = [];
  if (type === "short_answer") {
    for (const a of (fd.get("accepted_answers") || "")
      .split(";")
      .map((x) => x.trim())
      .filter(Boolean))
      accepted.push({ answer_text: a, is_case_sensitive: false });
  } else
    for (const [i, k] of ["A", "B", "C", "D"].entries()) {
      const text = (fd.get(`option_${k}`) || "").trim();
      if (!text) continue;
      opts.push({
        option_key: k,
        option_text: text,
        is_correct:
          type === "true_false"
            ? fd.get("truth_" + k) === "true"
            : fd.get("correct") === k,
        sort_order: i + 1,
      });
    }
  const d = {
    subject_id: Number(fd.get("subject_id")),
    grade_id: Number(fd.get("grade_id")),
    topic_id: Number(fd.get("topic_id")),
    lesson_id: fd.get("lesson_id") ? Number(fd.get("lesson_id")) : null,
    question_type: type,
    difficulty: fd.get("difficulty"),
    question_text: fd.get("question_text").trim(),
    explanation: fd.get("explanation").trim() || null,
    is_active: state.editing ? !!state.editing.question.is_active : true,
    is_public: Boolean(fd.get("is_public")),
    options,
    accepted_answers: accepted,
    media: state.editing?.media || [],
  };
  const id = form.dataset.id;
  return api(id ? `/api/questions/${id}` : "/api/questions", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(d),
  });
}
async function initMatrixRow(row) {
  const form = $("#examForm"),
    topic = row.querySelector(".mTopic"),
    lesson = row.querySelector(".mLesson");
  await selectTopics(
    form.elements.subject_id.value,
    form.elements.grade_id.value,
    topic,
    lesson,
  );
  topic.onchange = () => selectLessons(topic.value, lesson);
  form.elements.subject_id.onchange = form.elements.grade_id.onchange =
    async () => {
      for (const r of document.querySelectorAll(".matrix-row")) {
        await selectTopics(
          form.elements.subject_id.value,
          form.elements.grade_id.value,
          r.querySelector(".mTopic"),
          r.querySelector(".mLesson"),
        );
        r.querySelector(".mLesson").innerHTML =
          '<option value="">Tất cả bài</option>';
      }
    };
}
async function saveExamReady(examId) {
  const exam = state.exams.find((x) => x.exam_id === examId);
  if (exam?.status === "ready") return;
  try {
    await api(`/api/exams/${examId}/save`, { method: "POST" });
    const e = await api("/api/exams");
    state.exams = e.exams || [];
  } catch (err) {
    if (/đã lưu|không sửa được/i.test(String(err.message || ""))) return;
    throw err;
  }
}
function afterCreateExamChoices(id, title) {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">ĐỀ GỐC ĐÃ TẠO</span><h2>${esc(title || "Đề thi")}</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><p>Chọn bước tiếp theo. Nếu không chọn, đề đã được lưu trên máy chủ.</p><button class="choice-card" type="button" data-action="download-exam" data-id="${id}"><span class="module-icon">↓</span><span><strong>Lưu file đề về máy</strong><small>Tải file Word đề gốc kèm đáp án</small></span></button><button class="choice-card" type="button" data-action="open-shuffle" data-id="${id}"><span class="module-icon">⤨</span><span><strong>Sinh đề</strong><small>Trộn câu hỏi, phương án và tạo mã đề cho phòng thi</small></span></button><div class="form-actions"><button class="secondary" data-action="close-modal">Để sau</button></div></div></div>`;
}
function resultsReadyDialog(sid) {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">ĐÃ CHẤM ĐIỂM</span><h2>File kết quả đã sẵn sàng</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><p>Học sinh đã nộp bài và hệ thống đã chấm điểm. Giáo viên chỉ cần lấy file kết quả về máy.</p><div class="form-actions"><button class="secondary" data-action="close-modal">Để sau</button><button class="primary" data-action="download-results" data-id="${sid}">Lấy file kết quả</button></div></div></div>`;
}
async function createExam(form) {
  const d = formDataObject(form),
    matrix = [...document.querySelectorAll(".matrix-row")].map((r) => ({
      topic_id: Number(r.querySelector(".mTopic").value),
      lesson_id: r.querySelector(".mLesson").value
        ? Number(r.querySelector(".mLesson").value)
        : null,
      difficulty: r.querySelector(".mDiff").value,
      question_type: r.querySelector(".mType").value,
      question_count: Number(r.querySelector(".mCount").value),
    }));
  if (!matrix.length || matrix.some((x) => !x.topic_id || !x.question_count))
    throw Error("Hoàn tất các dòng ma trận trước khi tạo đề.");
  const created = await api("/api/exams", {
    method: "POST",
    body: JSON.stringify({
      title: d.title,
      supervising_authority: d.supervising_authority,
      school_name: d.school_name,
      subject_id: Number(d.subject_id),
      grade_id: Number(d.grade_id),
      duration_minutes: Number(d.duration_minutes),
      matrix,
    }),
  });
  state.selectedExam = created.exam_id;
  const generated = await api(`/api/exams/${created.exam_id}/generate`, {
    method: "POST",
  });
  try {
    await saveExamReady(created.exam_id);
    generated.exam.status = "ready";
  } catch (err) {
    toast(err.message);
  }
  $("#examPreview").innerHTML = previewMarkup(generated, false);
  await refreshLists();
  openModal(afterCreateExamChoices(created.exam_id, generated.exam.title));
  toast("Đề gốc đã được lưu trên hệ thống.");
}
function previewMarkup(d, canSave = false) {
  return `<div class="panel"><div class="panel-head"><div><h2>${esc(d.exam.title)} · Đề gốc</h2><p>${esc(d.exam.supervising_authority || "")} · ${esc(d.exam.school_name || "")} · ${d.questions?.length || 0} câu · ${d.exam.duration_minutes} phút</p></div><span class="pill ${d.exam.status === "ready" ? "green" : ""}">${d.exam.status === "ready" ? "Đã lưu" : "Bản nháp"}</span></div><div class="panel-body">${(d.questions || []).map((q, i) => `<div style="padding:12px 0;border-bottom:1px solid var(--line)"><b>Câu ${i + 1} · ${typeName[q.question_type]} · ${diffName[q.difficulty]}</b><p>${questionTextHtml(q.question_text)}</p></div>`).join("")}<div class="form-actions"><button class="secondary" data-action="download-exam" data-id="${d.exam.exam_id}">Tải đề gốc</button>${canSave ? '<button class="primary" data-action="save-exam" data-id="' + d.exam.exam_id + '">Lưu đề để mở phòng</button>' : `<button class="primary" data-action="open-shuffle" data-id="${d.exam.exam_id}">Sinh đề</button>`}</div></div></div>`;
}
function previewExam(d) {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">XEM TRƯỚC</span><h2>${esc(d.exam.title)}</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body">${previewMarkup(d, d.exam.status !== "ready")}</div></div>`;
}
function confirmSubmitForm() {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">HOÀN THÀNH BÀI THI</span><h2>Đã đến câu cuối</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><p>Bạn đã trả lời ${Object.keys(state.answers).length} câu. Nộp bài ngay?</p><div class="form-actions"><button class="secondary" data-action="close-modal">Kiểm tra lại</button><button class="danger" data-action="confirm-submit">Nộp bài</button></div></div></div>`;
}
function importStudentsForm(sid) {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">DANH SÁCH THÍ SINH</span><h2>Import học sinh</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><form id="importStudentsForm" data-id="${sid}"><div class="notice"><b>Hướng dẫn file danh sách Word (.docx)</b><br>Bảng cần có các cột theo thứ tự: STT · Mã học sinh/SBD · Họ và tên · Lớp · Ngày sinh. Mã học sinh, họ tên và lớp là bắt buộc; tên lớp phải trùng với lớp đã tạo trong hệ thống. Ngày sinh có thể để trống; nhập theo DD/MM/YYYY hoặc YYYY-MM-DD. Mỗi học sinh một dòng. Điền dữ liệu vào dòng trống trong file mẫu, xem trước lỗi rồi mới xác nhận nhập.</div><a href="${esc(state.base)}/api/templates/students.docx" target="_blank" rel="noreferrer">↓ Tải file Word mẫu danh sách học sinh</a><div class="spacer"></div><label class="field">File danh sách (.docx)<input name="file" type="file" accept=".docx" required></label><div id="studentPreview"></div><div id="importError" class="error"></div><div class="form-actions"><button class="secondary" type="button" data-action="close-modal">Đóng</button><button class="primary">Xem trước</button></div></form></div></div>`;
}
async function importStudentsFormFor(sid) {
  openModal(importStudentsForm(sid));
}
function importQuestionsForm() {
  return `<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">NGÂN HÀNG CÂU HỎI</span><h2>Import từ Word</h2></div><button class="mini" data-action="close-modal">✕</button></div><div class="dialog-body"><form id="importQuestionsForm"><div class="form-grid two"><label class="field">Môn<select name="subject_id">${state.subjects.map((x) => `<option value="${x.subject_id}">${esc(x.subject_name)}</option>`).join("")}</select></label><label class="field">Khối<select name="grade_id">${state.grades.map((x) => `<option value="${x.grade_id}">${esc(x.grade_name)}</option>`).join("")}</select></label><label class="field">Chủ đề<select name="topic_id" id="importTopic"></select></label><label class="field">Bài học<select name="lesson_id" id="importLesson"><option value="">Không chọn bài học</option></select></label></div><label class="inline-check"><input name="is_public" type="checkbox"> Công khai các câu hỏi import với giáo viên khác</label><p class="muted">Bỏ chọn thì chỉ bạn và admin xem được.</p><div class="notice"><b>Hướng dẫn file Word (.docx)</b><br>File cần có một bảng với các cột theo thứ tự: STT · Mã · Nội dung · Đáp án · Loại câu · Mức độ.<ul><li><b>TN:</b> nội dung gồm câu hỏi và bốn lựa chọn ghi A., B., C., D.; đáp án là A/B/C/D.</li><li><b>ĐS:</b> nội dung gồm bốn ý ghi a), b), c), d); đáp án gồm bốn ký tự Đ/S, ví dụ ĐSĐS.</li><li><b>ĐT:</b> nội dung câu hỏi; đáp án là câu trả lời. Mức độ ghi NB/TH/VD/VDC hoặc 1/2/3/4.</li></ul>Mỗi dòng trong bảng là một câu hỏi. Chọn đúng môn, khối, chủ đề và bài cho toàn bộ file.</div><button type="button" class="secondary" data-action="download-question-template">↓ Tải file Word mẫu câu hỏi</button><div class="spacer"></div><label class="field">File câu hỏi (.docx)<input name="file" type="file" accept=".docx" required></label><div id="questionImportPreview"></div><div class="form-actions"><button type="button" class="secondary" data-action="close-modal">Đóng</button><button class="primary">Xem trước file</button></div></form></div></div>`;
}
async function initImportQuestionsForm() {
  const f = $("#importQuestionsForm"),
    topic = $("#importTopic"),
    lesson = $("#importLesson"),
    load = async () =>
      selectTopics(
        f.elements.subject_id.value,
        f.elements.grade_id.value,
        topic,
        lesson,
      );
  await load();
  f.elements.subject_id.onchange = load;
  f.elements.grade_id.onchange = load;
  topic.onchange = () => selectLessons(topic.value, lesson);
}
async function previewStudentImport(form) {
  const fd = new FormData();
  fd.append("file", form.elements.file.files[0]);
  const r = await api(
    `/api/sessions/${form.dataset.id}/students/import?commit=false`,
    { method: "POST", body: fd },
  );
  $("#studentPreview").innerHTML =
    `<div class="notice">${r.count} dòng · ${r.error_count} lỗi</div>` +
    (r.rows || [])
      .map(
        (x) =>
          `<p>Dòng ${x.row}: ${esc(x.student_code || "")} · ${esc(x.full_name || "")} · ${esc(x.date_of_birth || "Chưa có ngày sinh")} · ${esc(x.error || "Hợp lệ")}</p>`,
      )
      .join("");
  if (!r.error_count && r.count) {
    $("#studentPreview").insertAdjacentHTML(
      "beforeend",
      '<button class="primary" type="button" id="confirmRoster">Xác nhận nhập danh sách</button>',
    );
    $("#confirmRoster").onclick = async () => {
      try {
        const f = new FormData();
        f.append("file", form.elements.file.files[0]);
        const done = await api(
          `/api/sessions/${form.dataset.id}/students/import?commit=true`,
          { method: "POST", body: f },
        );
        toast(`Đã nhập ${done.imported} học sinh`);
        closeModal();
      } catch (e) {
        $("#importError").textContent = e.message;
      }
    };
  }
}
async function previewQuestionImport(form) {
  const d = formDataObject(form),
    fd = new FormData();
  fd.append("file", form.elements.file.files[0]);
  const p = new URLSearchParams({
    subject_id: d.subject_id,
    grade_id: d.grade_id,
    topic_id: d.topic_id,
  });
  if (d.lesson_id) p.set("lesson_id", d.lesson_id);
  p.set("is_public", form.elements.is_public.checked ? "true" : "false");
  const r = await api("/api/questions/import?" + p, {
    method: "POST",
    body: fd,
  });
  $("#questionImportPreview").innerHTML =
    `<div class="notice">${r.count} dòng · ${r.error_count} lỗi</div>` +
    (r.rows || [])
      .map(
        (x) =>
          `<p>Dòng ${x.row}: ${esc(x.text)} · ${esc(x.error || "Hợp lệ")}</p>`,
      )
      .join("");
  if (!r.error_count && r.count) {
    $("#questionImportPreview").insertAdjacentHTML(
      "beforeend",
      '<button class="primary" type="button" id="confirmQuestionImport">Xác nhận lưu</button>',
    );
    $("#confirmQuestionImport").onclick = async () => {
      try {
        const f = new FormData();
        f.append("file", form.elements.file.files[0]);
        const done = await api("/api/questions/import?" + p + "&commit=true", {
          method: "POST",
          body: f,
        });
        closeModal();
        await loadQuestions();
        toast(`Đã nhập ${done.imported} câu hỏi`);
      } catch (e) {
        $("#questionImportPreview").insertAdjacentHTML(
          "beforeend",
          `<p class="error">${esc(e.message)}</p>`,
        );
      }
    };
  }
}
async function createRoom(form) {
  const data = formDataObject(form);
  const toUtc = (value) => {
    if (!value) return null;

    const [day, time] = value.split("T");
    const [year, month, date] = day.split("-").map(Number);
    const [hour, minute] = time.split(":").map(Number);
    return new Date(
      Date.UTC(year, month - 1, date, hour - 7, minute),
    ).toISOString();
  };

  const created = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      exam_id: Number(data.exam_id),
      session_name: data.session_name,
      start_time: toUtc(data.start_time),
      end_time: toUtc(data.end_time),
      password: data.password || null,
      shuffle_questions: form.elements.shuffle_questions.checked,
      shuffle_options: form.elements.shuffle_options.checked,
      paper_code_prefix: state.shuffle.paper_code_prefix,
      paper_code_length: state.shuffle.paper_code_length,
      paper_variant_count: state.shuffle.paper_variant_count,
    }),
  });

  closeModal();
  await refreshLists();
  state.selectedSession = await api(`/api/sessions/${created.session_id}`);
  openModal(`
    <div class="dialog">
      <div class="dialog-head">
        <div><span class="eyebrow">PHÒNG THI ĐÃ TẠO</span><h2>${esc(data.session_name)}</h2></div>
        <button class="mini" data-action="close-modal">✕</button>
      </div>
      <div class="dialog-body">
        <div class="notice">Gửi mã này cho học sinh sau khi đã nhập danh sách và mở phòng.</div>
        <div class="join-code">${esc(created.access_code)}</div>
        <p class="muted">Mã đề: ${esc(state.shuffle.paper_code_prefix)} + ${state.shuffle.paper_code_length} chữ số · ${state.shuffle.paper_variant_count} phiên bản</p>
        <p class="muted">${esc(created.join_url)}</p>
        <div class="room-qr"><img src="${esc(created.qr_data_url || "")}" alt="QR vào phòng thi"><a class="secondary" href="${esc(created.qr_data_url || "")}" download="qr-phong-${created.session_id}.png">Tải QR dạng ảnh</a><p class="muted">QR chỉ cho phép vào trong 15 phút từ giờ bắt đầu. Học sinh đã vào tiếp tục làm bài bình thường.</p></div>
        <div class="form-actions">
          <button class="secondary" data-action="import-students" data-id="${created.session_id}">Import học sinh</button>
          <button class="primary" data-action="close-modal">Xong</button>
        </div>
      </div>
    </div>`);
  render();
}
attachPageEvents();
render();
if (state.token) {
  state.studentToken = "";
  sessionStorage.removeItem("studentToken");
  sessionStorage.removeItem("examReloadIntentUntil");
  state.page = "dashboard";
  render();
  loadCatalog()
    .then(() => go("dashboard"))
    .catch(() => {
      state.token = "";
      sessionStorage.removeItem("examToken");
      state.page = "home";
      render();
    });
} else if (
  state.studentToken &&
  (state.page === "exam" || Number(sessionStorage.getItem("examReloadIntentUntil") || 0) > Date.now())
) {
  sessionStorage.removeItem("examReloadIntentUntil");
  document.addEventListener("DOMContentLoaded", () => {
    state.page = "exam";
    render();
    window.startExam().catch((error) => {
      state.studentToken = "";
      sessionStorage.removeItem("studentToken");
      state.page = "join";
      render();
      toast(error.message);
    });
  }, { once: true });
} else if (state.studentToken || state.page === "exam") {
  state.studentToken = "";
  sessionStorage.removeItem("studentToken");
  sessionStorage.removeItem("examReloadIntentUntil");
  state.page = "join";
  render();
}
