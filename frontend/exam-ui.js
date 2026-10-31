function examFlagKey() {
  try {
    const tokenPart = state.studentToken
      .split(".")[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/");
    return "examFlags:" + JSON.parse(atob(tokenPart)).sub;
  } catch {
    return "examFlags:current";
  }
}

function examFlags() {
  try {
    return JSON.parse(sessionStorage.getItem(examFlagKey()) || "{}");
  } catch {
    return {};
  }
}

function saveExamFlags(flags) {
  sessionStorage.setItem(examFlagKey(), JSON.stringify(flags));
}

function readExamAnswer(question) {
  const id = question.question.question_id;
  const card = document.getElementById("exam-question-" + id);
  if (!card) return "";

  if (question.question.question_type === "multiple_choice") {
    return card.querySelector("input[type=radio]:checked")?.value || "";
  }

  if (question.question.question_type === "true_false") {
    const answers = {};
    for (const option of question.options) {
      const value = card.querySelector(
        'input[name="tf_' + option.option_key + "_" + id + '"]:checked',
      )?.value;
      if (value !== undefined) answers[option.option_key] = value === "true";
    }
    return Object.keys(answers).length ? JSON.stringify(answers) : "";
  }

  return card.querySelector("textarea")?.value.trim() || "";
}

async function saveOneAnswer(question) {
  const id = question.question.question_id;
  const answer = readExamAnswer(question);

  if (answer) {
    await api(
      "/api/exam/answers",
      {
        method: "PUT",
        body: JSON.stringify({ question_id: id, answer_text: answer }),
      },
      state.studentToken,
    );
    state.answers[id] = answer;
  } else if (state.answers[id] !== undefined) {
    await api(
      "/api/exam/answers",
      {
        method: "PUT",
        body: JSON.stringify({ question_id: id, answer_text: "" }),
      },
      state.studentToken,
    );
    delete state.answers[id];
  }

  document
    .querySelector('.exam-qnav[data-question-id="' + id + '"]')
    ?.classList.toggle("answered", !!state.answers[id]);

  const total = state.exam.questions.length;
  const count = state.exam.questions.filter(
    (item) => state.answers[item.question.question_id],
  ).length;
  const percent = Math.round((count / total) * 100);
  const progressBar = document.getElementById("examProgressBar");
  const progressLabel = document.getElementById("examProgressLabel");

  if (progressBar) progressBar.style.width = percent + "%";
  if (progressLabel)
    progressLabel.textContent = percent + "% · " + count + "/" + total + " câu";
}

window.saveCurrentAnswer = async function () {
  for (const timer of Object.values(state.answerSaveTimers || {}))
    clearTimeout(timer);
  state.answerSaveTimers = {};
  await Promise.all((state.exam?.questions || []).map(saveOneAnswer));
};

window.startExam = async function () {
  const exam = await api("/api/exam/me", {}, state.studentToken);
  if (!exam.question_ids?.length) {
    throw Error(
      "Đề thi của phòng này đang trống. Nhờ giáo viên tạo phòng mới từ đề đã lưu.",
    );
  }

  const questions = await Promise.all(
    exam.question_ids.map((_, index) =>
      api("/api/exam/questions/" + (index + 1), {}, state.studentToken),
    ),
  );

  state.exam = { me: exam, questions };
  state.answers = exam.answers || {};
  state.student = {
    full_name: exam.full_name,
    class_name: exam.class_name,
    student_code: exam.student_code,
  };
  state.page = "exam";
  render();
  startTimer(exam.remaining_seconds);
};
function examPage() {
  if (!state.exam) {
    return '<main class="student-stage"><div class="student-box"><div class="panel question-card">Đang tải bài thi…</div></div></main>';
  }

  const { me, questions } = state.exam;
  const flags = examFlags();
  const grouped = !!state.exam.grouped;
  const answeredCount = questions.filter(
    (question) => state.answers[question.question.question_id],
  ).length;
  const progress = Math.round((answeredCount / questions.length) * 100);

  function questionButton(id, index) {
    const answered = state.answers[id] ? "answered " : "";
    const flagged = flags[id] ? "flagged" : "";
    return (
      '<button class="exam-qnav ' +
      answered +
      flagged +
      '" data-jump-index="' +
      (index + 1) +
      '" data-question-id="' +
      id +
      '" aria-label="Câu ' +
      (index + 1) +
      '">' +
      (index + 1) +
      "</button>"
    );
  }

  const nav = grouped
    ? [...new Set(questions.map((q) => q.question.question_type))]
        .map((type) => {
          const buttons = questions
            .map((question, index) =>
              question.question.question_type === type
                ? questionButton(question.question.question_id, index)
                : "",
            )
            .join("");
          return (
            '<div class="exam-nav-group"><b>' +
            esc(typeName[type] || type) +
            '</b><div class="exam-question-list">' +
            buttons +
            "</div></div>"
          );
        })
        .join("")
    : '<div class="exam-question-list">' +
      me.question_ids.map(questionButton).join("") +
      "</div>";

  const cards = questions
    .map((item, index) => {
      const question = item.question;
      const id = question.question_id;
      const answer = state.answers[id] || "";
      const flagged = !!flags[id];
      let trueFalseAnswers = {};
      try {
        trueFalseAnswers = JSON.parse(answer || "{}");
      } catch {}

      let answerMarkup = "";
      if (question.question_type === "multiple_choice") {
        answerMarkup = item.options
          .map(
            (option) =>
              '<label class="answer-option"><input type="radio" name="answer_' +
              id +
              '" value="' +
              esc(option.option_key) +
              '" ' +
              (answer === option.option_key ? "checked" : "") +
              "><span><b>" +
              esc(option.option_key) +
              ".</b> " +
              esc(option.option_text) +
              "</span></label>",
          )
          .join("");
      } else if (question.question_type === "true_false") {
        answerMarkup = item.options
          .map(
            (option) =>
              '<div class="tf-statement"><div class="tf-text"><b>' +
              esc(option.option_key) +
              ".</b> " +
              esc(option.option_text) +
              '</div><div class="tf-choices"><label><input type="radio" name="tf_' +
              esc(option.option_key) +
              "_" +
              id +
              '" value="true" ' +
              (trueFalseAnswers[option.option_key] === true ? "checked" : "") +
              '> Đúng</label><label><input type="radio" name="tf_' +
              esc(option.option_key) +
              "_" +
              id +
              '" value="false" ' +
              (trueFalseAnswers[option.option_key] === false ? "checked" : "") +
              "> Sai</label></div></div>",
          )
          .join("");
      } else {
        answerMarkup =
          '<label class="field">Câu trả lời<textarea maxlength="500" ' +
          'placeholder="Nhập câu trả lời…">' +
          esc(answer) +
          "</textarea></label>";
      }

      const media = (item.media || [])
        .filter((file) => file.image_url)
        .map(
          (file) =>
            '<img class="exam-media" src="' +
            esc(state.base + file.image_url) +
            '" alt="Hình minh họa câu hỏi">',
        )
        .join("");

      return (
        '<article id="exam-question-' +
        id +
        '" class="panel exam-question-card ' +
        (flagged ? "question-flagged" : "") +
        '"><div class="exam-meta"><span>Câu ' +
        (index + 1) +
        " / " +
        questions.length +
        " · " +
        esc(typeName[question.question_type] || "") +
        '</span><button class="exam-flag ' +
        (flagged ? "is-flagged" : "") +
        '" data-action="toggle-flag" data-question-id="' +
        id +
        '" aria-pressed="' +
        flagged +
        '">' +
        (flagged ? "⚑ Bỏ đánh dấu" : "⚑ Đánh dấu câu") +
        "</button></div><h2>" +
        window.questionTextHtml(question.question_text) +
        "</h2>" +
        media +
        '<div class="exam-answer-area">' +
        answerMarkup +
        "</div></article>"
      );
    })
    .join("");

  return (
    '<main class="exam-shell"><aside class="exam-nav panel">' +
    '<div class="exam-nav-title">Câu hỏi <span>' +
    questions.length +
    " câu</span></div>" +
    '<label class="exam-group-toggle"><input type="checkbox" ' +
    'data-action="toggle-question-groups" ' +
    (grouped ? "checked" : "") +
    '> Phân nhóm</label><div class="exam-nav-items">' +
    nav +
    '</div><div class="exam-legend"><span><i class="answered-dot"></i> Đã làm</span>' +
    '<span><i class="flagged-dot"></i> Đánh dấu</span></div>' +
    '<button class="danger exam-submit" data-action="submit-exam">Nộp bài</button></aside>' +
    '<section class="exam-main"><header class="panel exam-candidate"><div class="exam-heading">' +
    "<h1>" +
    esc(me.exam_title || "Bài thi") +
    "</h1><span>" +
    esc(me.subject_name || "") +
    ' · còn <b id="timer">--:--</b></span>' +
    '<div class="exam-progress"><div class="exam-progress-track"><i id="examProgressBar" ' +
    'style="width:' +
    progress +
    '%"></i></div><span id="examProgressLabel">' +
    progress +
    "% · " +
    answeredCount +
    "/" +
    questions.length +
    " câu</span></div></div>" +
    '<div class="exam-identity"><b>' +
    esc(me.full_name) +
    "</b><span>SBD: " +
    esc(me.student_code) +
    "</span><span>Mã đề: " +
    esc(me.paper_code || "—") +
    "</span></div></header>" +
    cards +
    '<button class="danger exam-submit exam-submit-bottom" data-action="submit-exam">Nộp bài</button>' +
    "</section></main>"
  );
}
window.examPage = examPage;
document.addEventListener(
  "click",
  async (event) => {
    const flagButton = event.target.closest('[data-action="toggle-flag"]');
    if (flagButton && state.page === "exam") {
      event.preventDefault();
      event.stopImmediatePropagation();
      try {
        const id = flagButton.dataset.questionId;
        const question = state.exam.questions.find(
          (item) => item.question.question_id === Number(id),
        );
        await saveOneAnswer(question);

        const flags = examFlags();
        flags[id] = !flags[id];
        saveExamFlags(flags);
        flagButton.classList.toggle("is-flagged", flags[id]);
        flagButton.setAttribute("aria-pressed", String(flags[id]));
        flagButton.textContent = flags[id] ? "⚑ Bỏ đánh dấu" : "⚑ Đánh dấu câu";
        document
          .querySelector('.exam-qnav[data-question-id="' + id + '"]')
          ?.classList.toggle("flagged", flags[id]);
        document
          .getElementById("exam-question-" + id)
          ?.classList.toggle("question-flagged", flags[id]);
      } catch (error) {
        toast(error.message);
      }
      return;
    }

    const questionButton = event.target.closest("[data-jump-index]");
    if (questionButton && state.page === "exam") {
      event.preventDefault();
      event.stopImmediatePropagation();
      document
        .getElementById("exam-question-" + questionButton.dataset.questionId)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  },
  true,
);

document.addEventListener("change", (event) => {
  if (state.page !== "exam" || !event.target.matches('input[type="radio"]'))
    return;
  const card = event.target.closest(".exam-question-card");
  const id = Number(card?.id.replace("exam-question-", ""));
  const question = state.exam.questions.find(
    (item) => item.question.question_id === id,
  );
  if (question) saveOneAnswer(question).catch((error) => toast(error.message));
});

document.addEventListener("input", (event) => {
  if (
    state.page !== "exam" ||
    !event.target.matches(".exam-question-card textarea")
  )
    return;
  const card = event.target.closest(".exam-question-card");
  const id = Number(card.id.replace("exam-question-", ""));
  const question = state.exam.questions.find(
    (item) => item.question.question_id === id,
  );
  state.answerSaveTimers ??= {};
  clearTimeout(state.answerSaveTimers[id]);
  state.answerSaveTimers[id] = setTimeout(
    () => saveOneAnswer(question).catch((error) => toast(error.message)),
    400,
  );
});

let lastTabViolation = 0;
let disqualifiedNotice = false;

function exitExamWithNotice(count) {
  clearInterval(state.timer);
  state.page = "home";
  state.studentToken = "";
  sessionStorage.removeItem("studentToken");
  state.student = null;
  state.exam = null;
  render();
  openModal(
    '<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">BÀI THI ĐÃ BỊ HỦY</span><h2>Vi phạm quy chế</h2></div></div><div class="dialog-body"><p>Bạn đã đổi tab hoặc rời trang thi ' +
      count +
      ' lần. Kết quả bài thi đã bị hủy.</p><button class="primary" ' +
      'data-action="close-modal">Đã hiểu</button></div></div>',
  );
}

function showViolationWarning(count) {
  openModal(
    '<div class="dialog"><div class="dialog-head"><div><span class="eyebrow">CẢNH CÁO LẦN ' +
      count +
      '</span><h2>Không rời trang thi</h2></div></div><div class="dialog-body"><p>' +
      "Hệ thống đã ghi nhận " +
      count +
      " lần đổi tab/rời trang. Đến lần thứ ba, kết quả thi sẽ bị hủy.</p>" +
      '<button class="primary" data-action="close-modal">Tiếp tục làm bài</button>' +
      "</div></div>",
  );
}

const examReloadIntentKey = "examReloadIntentUntil";
let examReloadPending = false;

document.addEventListener("keydown", async (event) => {
  const reloadKey = event.key === "F5" ||
    ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r");
  if (state.page !== "exam" || !reloadKey) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  if (examReloadPending) return;
  examReloadPending = true;
  try {
    await window.saveCurrentAnswer();
    sessionStorage.setItem(examReloadIntentKey, String(Date.now() + 5000));
    location.reload();
  } catch (error) {
    examReloadPending = false;
    toast("Chưa tải lại trang vì chưa lưu được đáp án: " + error.message);
  }
}, true);

function isExamReloadIntent() {
  const expiry = Number(sessionStorage.getItem(examReloadIntentKey) || 0);
  if (expiry > Date.now()) return true;
  sessionStorage.removeItem(examReloadIntentKey);
  return false;
}

async function reportTabViolation(pageExit = false) {
  if (state.page !== "exam" || !state.studentToken || isExamReloadIntent()) return;
  if (pageExit && Date.now() - lastTabViolation < 3000) return;
  lastTabViolation = Date.now();

  try {
    const response = await fetch(state.base + "/api/exam/violations", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + state.studentToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        violation_type: "tab_hidden",
        description: "Học sinh rời trang thi hoặc đổi tab",
      }),
      keepalive: true,
    });
    if (!response.ok) return;

    const result = await response.json();
    if (result.disqualified) {
      disqualifiedNotice = true;
      if (!document.hidden) exitExamWithNotice(result.violation_count);
    } else if (document.hidden) {
      state.pendingViolationWarning = result.violation_count;
    } else {
      showViolationWarning(result.violation_count);
    }
  } catch {}
}
document.addEventListener(
  "click",
  (event) => {
    const toggle = event.target.closest(
      '[data-action="toggle-question-groups"]',
    );
    if (!toggle || state.page !== "exam") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    state.exam.grouped = toggle.checked;
    render();
  },
  true,
);

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    reportTabViolation();
  } else if (disqualifiedNotice) {
    disqualifiedNotice = false;
    exitExamWithNotice(3);
  } else if (state.pendingViolationWarning) {
    const count = state.pendingViolationWarning;
    state.pendingViolationWarning = 0;
    showViolationWarning(count);
  }
});

window.addEventListener("pagehide", () => reportTabViolation(true));
