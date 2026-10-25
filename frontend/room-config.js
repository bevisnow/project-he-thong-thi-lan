function roomConfigs() {
  try {
    const configs = JSON.parse(localStorage.getItem("examRoomConfigs") || "[]");
    return Array.isArray(configs) ? configs : [];
  } catch {
    return [];
  }
}

function roomForm() {
  const readyExams = state.exams.filter((exam) => exam.status === "ready");
  const configs = roomConfigs();
  const examOptions = readyExams
    .map(
      (exam) => `
    <option value="${exam.exam_id}" ${state.selectedExam === exam.exam_id ? "selected" : ""}>
      ${esc(exam.title)} · ${exam.duration_minutes} phút
    </option>
  `,
    )
    .join("");
  const configOptions = configs
    .map(
      (config, index) =>
        `<option value="${index}">${esc(config.name)}</option>`,
    )
    .join("");

  return `
    <div class="dialog">
      <div class="dialog-head">
        <div><span class="eyebrow">TỔ CHỨC THI</span><h2>Tạo phòng thi</h2></div>
        <button class="mini" data-action="close-modal">✕</button>
      </div>
      <div class="dialog-body">
        <form id="roomForm">
          <label class="field">Dùng cấu hình đã lưu
            <select id="roomConfigSelect">
              <option value="">Cấu hình hiện tại</option>${configOptions}
            </select>
          </label>
          <div class="form-grid two">
            <label class="field">Tên phòng
              <input name="session_name" required placeholder="Ví dụ: Ca sáng 10A1">
            </label>
            <label class="field">Đề thi
              <select name="exam_id" required>
                <option value="">Chọn đề đã lưu</option>${examOptions}
              </select>
            </label>
            <label class="field">Bắt đầu
              <input name="start_time" type="datetime-local">
            </label>
            <label class="field">Kết thúc
              <input name="end_time" type="datetime-local">
            </label>
            <label class="field" style="grid-column:1/-1">
              Mật khẩu phòng (tùy chọn, tối thiểu 8 ký tự)
              <input name="password" type="password" minlength="8" maxlength="128" autocomplete="new-password">
            </label>
          </div>
          <div class="spacer"></div>
          <label class="inline-check">
            <input type="checkbox" name="shuffle_questions" ${state.shuffle.shuffle_questions ? "checked" : ""}>
            Trộn câu hỏi
          </label>
          <div class="spacer"></div>
          <label class="inline-check">
            <input type="checkbox" name="shuffle_options" ${state.shuffle.shuffle_options ? "checked" : ""}>
            Trộn phương án
          </label>
          <div class="spacer"></div>
          <label class="field">Tên cấu hình để lưu
            <input name="room_config_name" maxlength="60" placeholder="Ví dụ: Kiểm tra 45 phút">
          </label>
          <label class="inline-check">
            <input type="checkbox" name="save_room_config">
            Lưu cấu hình này để dùng lần sau
          </label>
          <div id="roomError" class="error"></div>
          <div class="form-actions">
            <button type="button" class="secondary" data-action="close-modal">Hủy</button>
            <button class="primary">Tạo phòng</button>
          </div>
        </form>
      </div>
    </div>`;
}
window.roomForm = roomForm;
document.addEventListener("change", (event) => {
  if (event.target.id !== "roomConfigSelect" || !event.target.value) return;

  const config = roomConfigs()[Number(event.target.value)];
  const form = event.target.closest("form");
  if (!config || !form) return;

  state.shuffle = {
    shuffle_questions: !!config.shuffle_questions,
    shuffle_options: !!config.shuffle_options,
    paper_code_prefix: config.paper_code_prefix || "",
    paper_code_length: Number(config.paper_code_length) || 3,
    paper_variant_count: Number(config.paper_variant_count) || 1,
  };
  form.elements.shuffle_questions.checked = state.shuffle.shuffle_questions;
  form.elements.shuffle_options.checked = state.shuffle.shuffle_options;
});
document.addEventListener(
  "submit",
  (event) => {
    const form = event.target;
    if (form.id !== "roomForm") return;

    const password = form.elements.password.value;
    if (password && password.length < 8) {
      event.preventDefault();
      event.stopImmediatePropagation();
      alert(
        "Mật khẩu phòng cần có ít nhất 8 ký tự. Hãy nhập mật khẩu dài hơn rồi thử lại.",
      );
      form.elements.password.focus();
      return;
    }
    if (!form.elements.save_room_config.checked) return;

    const name = form.elements.room_config_name.value.trim();
    if (!name) {
      event.preventDefault();
      event.stopImmediatePropagation();
      toast("Nhập tên cấu hình trước khi lưu.");
      form.elements.room_config_name.focus();
      return;
    }

    const config = {
      name,
      shuffle_questions: form.elements.shuffle_questions.checked,
      shuffle_options: form.elements.shuffle_options.checked,
      paper_code_prefix: state.shuffle.paper_code_prefix,
      paper_code_length: state.shuffle.paper_code_length,
      paper_variant_count: state.shuffle.paper_variant_count,
    };
    const configs = roomConfigs().filter(
      (item) => item.name.toLocaleLowerCase() !== name.toLocaleLowerCase(),
    );
    configs.push(config);
    localStorage.setItem("examRoomConfigs", JSON.stringify(configs));
    toast("Đã lưu cấu hình phòng thi");
  },
  true,
);

new MutationObserver(() => {
  const passwordInput = document.querySelector(
    '#roomPasswordForm input[name="password"]',
  );
  if (passwordInput) {
    passwordInput.minLength = 8;
    passwordInput.placeholder = "Ít nhất 8 ký tự";
  }

  const roomPasswordInput = document.querySelector(
    '#roomForm input[name="password"]',
  );
  if (roomPasswordInput) roomPasswordInput.minLength = 0;
}).observe(document.getElementById("modal"), {
  childList: true,
  subtree: true,
});
