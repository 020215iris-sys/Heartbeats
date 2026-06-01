const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, Header, Footer, PageNumber
} = require('/sessions/determined-awesome-ride/node_modules/docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function heading1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, bold: true })] });
}
function heading2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, bold: true })] });
}
function para(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })] });
}
function gap() {
  return new Paragraph({ children: [new TextRun("")] });
}

function tableRow(cells, isHeader = false) {
  return new TableRow({
    tableHeader: isHeader,
    children: cells.map(({ text, width, shade }) => new TableCell({
      borders,
      width: { size: width, type: WidthType.DXA },
      margins: cellMargins,
      shading: shade ? { fill: shade, type: ShadingType.CLEAR } : undefined,
      children: [new Paragraph({ children: [new TextRun({ text, bold: isHeader })] })]
    }))
  });
}

function apiTable(method, path, auth, desc, body, response) {
  const W = [1200, 8160];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: W,
    rows: [
      tableRow([{ text: "메서드", width: W[0], shade: "E8F0FE" }, { text: method + " " + path, width: W[1] }]),
      tableRow([{ text: "인증", width: W[0], shade: "E8F0FE" }, { text: auth, width: W[1] }]),
      tableRow([{ text: "설명", width: W[0], shade: "E8F0FE" }, { text: desc, width: W[1] }]),
      tableRow([{ text: "요청 Body", width: W[0], shade: "E8F0FE" }, { text: body, width: W[1] }]),
      tableRow([{ text: "응답", width: W[0], shade: "E8F0FE" }, { text: response, width: W[1] }]),
    ]
  });
}

function funcTable(name, file, desc, params, returns) {
  const W = [1400, 7960];
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: W,
    rows: [
      tableRow([{ text: "함수명", width: W[0], shade: "FFF3E0" }, { text: name, width: W[1] }]),
      tableRow([{ text: "파일", width: W[0], shade: "FFF3E0" }, { text: file, width: W[1] }]),
      tableRow([{ text: "역할", width: W[0], shade: "FFF3E0" }, { text: desc, width: W[1] }]),
      tableRow([{ text: "파라미터", width: W[0], shade: "FFF3E0" }, { text: params, width: W[1] }]),
      tableRow([{ text: "반환값", width: W[0], shade: "FFF3E0" }, { text: returns, width: W[1] }]),
    ]
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Malgun Gothic", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Malgun Gothic", color: "1a3a6b" },
        paragraph: { spacing: { before: 360, after: 180 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Malgun Gothic", color: "2e5fa3" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "Heartbeats Backend API 함수 레퍼런스", size: 18, color: "888888" })]
      })]})
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 18, color: "888888" }), new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })]
      })]})
    },
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 480, after: 240 }, children: [new TextRun({ text: "Heartbeats Backend", bold: true, size: 52, color: "1a3a6b", font: "Malgun Gothic" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 }, children: [new TextRun({ text: "API 함수 레퍼런스 문서", bold: true, size: 40, color: "2e5fa3", font: "Malgun Gothic" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [new TextRun({ text: "프론트엔드 연동 가이드 | 2026-06-01", size: 20, color: "888888" })] }),

      heading1("0. 현재 상황 및 연동 흐름 설명"),
      para("현재 상태", { bold: true }),
      para("• /chat API는 AI 응답은 동작하지만, DB 저장 코드가 주석처리된 상태입니다."),
      para("• 이유: 프론트에서 session_id를 임의로 생성해서 보내면 DB에 해당 세션이 없어 오류 발생."),
      para("• 해결책: 채팅 전에 반드시 /counseling/sessions를 먼저 호출해서 세션을 생성해야 합니다."),
      gap(),
      para("올바른 상담 흐름 (프론트 기준)", { bold: true }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [720, 2800, 5840],
        rows: [
          tableRow([{ text: "단계", width: 720, shade: "D5E8F0" }, { text: "API 호출", width: 2800, shade: "D5E8F0" }, { text: "설명", width: 5840, shade: "D5E8F0" }], true),
          tableRow([{ text: "1", width: 720 }, { text: "POST /auth/login", width: 2800 }, { text: "로그인 → access_token 발급", width: 5840 }]),
          tableRow([{ text: "2★", width: 720 }, { text: "POST /counseling/sessions", width: 2800 }, { text: "상담 세션 생성 → session_id 발급 (핵심!)", width: 5840 }]),
          tableRow([{ text: "3", width: 720 }, { text: "POST /chat", width: 2800 }, { text: "발급받은 session_id로 AI 채팅 (반복)", width: 5840 }]),
          tableRow([{ text: "4★", width: 720 }, { text: "PATCH /counseling/sessions/{id}/end", width: 2800 }, { text: "상담 종료 → 요약 자동 생성 및 DB 저장", width: 5840 }]),
        ]
      }),
      gap(),
      para("\"종료 부분만 생기면 한바퀴 돈다\"의 의미", { bold: true }),
      para("백엔드에는 세션 시작/메시지 저장/세션 종료+요약 API가 모두 구현되어 있습니다. 프론트에서 ①상담 시작 시 /counseling/sessions 호출, ②상담 종료 시 /counseling/sessions/{id}/end 호출만 추가하면 전체 흐름(시작→대화→요약 저장)이 완성됩니다."),
      gap(),

      heading1("1. 인증 (routers/auth.py)"),
      heading2("1-1. POST /auth/signup — 회원가입"),
      apiTable("POST", "/auth/signup", "불필요 (공개)", "신규 사용자를 등록하고 access_token을 즉시 발급합니다.", "email (str), password (str), role (str), nickname (str), phone_number (str), gender (str, 선택), birth_date (date YYYY-MM-DD, 선택)", "id, email, nickname, role, needs_guardian_link (bool), access_token (JWT)"),
      gap(),
      heading2("1-2. POST /auth/login — 로그인"),
      apiTable("POST", "/auth/login", "불필요 (공개)", "이메일/비밀번호/역할로 로그인하고 access_token을 반환합니다.", "email (str), password (str), role (str)", "id, email, nickname, role, needs_guardian_link (bool), access_token (JWT)"),
      gap(),
      para("※ 이후 모든 API 헤더에 Authorization: Bearer {access_token} 필수", { bold: true, color: "c0392b" }),
      gap(),

      heading1("2. 상담 (routers/counseling.py)"),
      heading2("2-1. POST /counseling/sessions — 상담 세션 시작 ★"),
      apiTable("POST", "/counseling/sessions", "Authorization: Bearer {token}", "상담 세션을 생성하고 session_id를 발급합니다. 채팅(/chat) 호출 전에 반드시 먼저 실행해야 합니다.", "classification_id (str UUID, 선택), persona_type (str 선택: empathy | coaching | neutral, 기본 empathy)", "session_id (UUID), user_id, persona_type, started_at, is_active: true"),
      gap(),
      heading2("2-2. GET /counseling/sessions/{session_id} — 세션 조회"),
      apiTable("GET", "/counseling/sessions/{session_id}", "Authorization: Bearer {token}", "session_id로 상담 세션 정보를 조회합니다. 자신의 세션만 가능.", "없음 (Path: session_id)", "session_id, user_id, classification_id, persona_type, started_at, ended_at, is_active"),
      gap(),
      heading2("2-3. POST /counseling/sessions/{session_id}/messages — 메시지 저장"),
      apiTable("POST", "/counseling/sessions/{session_id}/messages", "Authorization: Bearer {token}", "대화 메시지를 conversations 테이블에 저장합니다. crisis_score >= 0.7이면 crisis_events도 자동 생성됩니다.", "role (str: user | assistant), message_type (str, 기본 text), encrypted_content (str), crisis_score (float 0.0~1.0, 선택)", "message_id, session_id, role, message_type, crisis_score, created_at"),
      gap(),
      heading2("2-4. GET /counseling/sessions/{session_id}/messages — 대화 내역 조회"),
      apiTable("GET", "/counseling/sessions/{session_id}/messages", "Authorization: Bearer {token}", "세션의 전체 대화 내역을 시간 순서대로 반환합니다.", "없음 (Path: session_id)", "session_id, messages: [{message_id, role, message_type, content, crisis_score, created_at}, ...]"),
      gap(),
      heading2("2-5. PATCH /counseling/sessions/{session_id}/end — 상담 종료 + 요약 ★"),
      apiTable("PATCH", "/counseling/sessions/{session_id}/end", "Authorization: Bearer {token}", "상담을 종료하고 자동으로 요약을 생성·저장합니다. ①is_active=false ②LoRA 모델로 대화 요약 ③summaries 테이블 저장. 상담 한바퀴의 마지막 단계.", "없음 (Path: session_id)", "session_id, ended_at, is_active: false, summary_id (생성된 요약 UUID)"),
      gap(),

      heading1("3. AI 채팅 (backend_main.py)"),
      heading2("3-1. POST /chat — AI 채팅"),
      apiTable("POST", "/chat", "Authorization: Bearer {token}", "Groq (llama-3.3-70b) AI에 메시지를 보내고 응답을 받습니다. 현재 DB 저장 코드 주석처리 상태. session_id는 반드시 /counseling/sessions에서 발급받은 값 사용.", "message (str), session_id (str UUID)", '{"reply": "AI 응답 텍스트"}'),
      gap(),

      heading1("4. 내부 함수 목록 (프론트 직접 호출 없음)"),
      para("아래 함수들은 백엔드 내부에서만 사용됩니다."),
      gap(),
      funcTable("create_access_token(user_id, role)", "routers/auth.py", "JWT access_token 생성. 만료 60분.", "user_id (str), role (str)", "JWT 토큰 문자열"),
      gap(),
      funcTable("verify_access_token(token)", "routers/auth.py", "JWT 검증 후 payload 반환. 실패 시 HTTP 401.", "token (str)", "dict: {user_id, role, exp}"),
      gap(),
      funcTable("get_current_user(authorization)", "routers/counseling.py", "헤더 토큰을 verify_access_token으로 검증하는 공통 의존성 함수. FastAPI Depends()로 사용.", "authorization (str, Header)", "dict: {user_id, role, exp}"),
      gap(),
      funcTable("request_summary(transcript)", "summary_service.py", "LoRA 요약 API 서버에 POST. end_session 내부에서 자동 호출됨.", "transcript (str) — '내담자: ...\\n상담사: ...' 형식의 전체 대화", 'dict: {"output": "yaml 형식 요약 텍스트"}'),
      gap(),
      funcTable("get_db_general / get_db_sensitive / get_db_audit", "database.py", "FastAPI 의존성 주입용 DB 세션 생성 함수. 일반(5432) / 민감(5433) / 감사(5434) DB.", "없음", "AsyncSession (yield)"),
      gap(),
      funcTable("require_profile_complete(authorization)", "database.py", "설문 진입 전 birth_date, gender 입력 여부 검사. 미입력 시 HTTP 400 반환.", "authorization (str, Header)", "None (통과) | HTTP 400 (미완성)"),
      gap(),

      heading1("5. 주요 DB 테이블 구조"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2000, 2000, 5360],
        rows: [
          tableRow([{ text: "테이블명", width: 2000, shade: "D5E8F0" }, { text: "DB", width: 2000, shade: "D5E8F0" }, { text: "주요 컬럼", width: 5360, shade: "D5E8F0" }], true),
          tableRow([{ text: "users", width: 2000 }, { text: "general (5432)", width: 2000 }, { text: "id, email, nickname, hashed_password, role, gender, birth_date", width: 5360 }]),
          tableRow([{ text: "counseling_sessions", width: 2000 }, { text: "sensitive (5433)", width: 2000 }, { text: "id, user_id, persona_type, started_at, ended_at, is_active", width: 5360 }]),
          tableRow([{ text: "conversations", width: 2000 }, { text: "sensitive (5433)", width: 2000 }, { text: "id, session_id, user_id, role, encrypted_content, crisis_score", width: 5360 }]),
          tableRow([{ text: "summaries", width: 2000 }, { text: "sensitive (5433)", width: 2000 }, { text: "id, session_id, main_complaint, risk_level, suicidal_mentioned, core_topics, next_session_notes", width: 5360 }]),
          tableRow([{ text: "crisis_events", width: 2000 }, { text: "sensitive (5433)", width: 2000 }, { text: "id, user_id, conversation_id, crisis_score, severity, guardian_notified", width: 5360 }]),
          tableRow([{ text: "audit_logs_general", width: 2000 }, { text: "audit (5434)", width: 2000 }, { text: "id, user_id, action, resource_type, created_at", width: 5360 }]),
          tableRow([{ text: "audit_logs_sensitive", width: 2000 }, { text: "audit (5434)", width: 2000 }, { text: "id, user_id, action, resource_type, resource_id, created_at", width: 5360 }]),
        ]
      }),
      gap(),
      new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "— END OF DOCUMENT —", size: 18, color: "aaaaaa" })] })
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("/sessions/determined-awesome-ride/mnt/Heartbeats/Heartbeats_Backend_API_함수레퍼런스.docx", buf);
  console.log("Done");
});