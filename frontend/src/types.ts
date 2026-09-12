export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuthStatus {
  setup_required: boolean;
  authenticated: boolean;
  user: User | null;
}

export interface Book {
  id: number;
  title: string;
  source_filename: string;
  total_chapters: number;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  created_at: string;
}

export interface ChapterMeta {
  index_no: number;
  title: string;
  char_count: number;
}

export interface Progress {
  user_id: number;
  book_id: number;
  chapter_index: number;
  chapter_offset: number;
  updated_at: string;
}

export interface ImportResult {
  book_id: number;
  title: string;
  total_chapters: number;
  notice?: string | null;
}

export type Role = "user" | "assistant";

export type Theme = "light" | "dark";

/** 阅读列宽度：宽松（中文长阅读，默认）／紧凑（更接近 ChatGPT） */
export type ReadingMode = "wide" | "compact";

export interface ChatMessage {
  id: string;
  role: Role;
  text: string;
  /** 是否仍在流式生成中 */
  streaming?: boolean;
  /** 已收到「思考」但正文尚未开始 */
  thinking?: string;
  /** 正文在 text 中的起始下标（标题 + 空行之后） */
  bodyStart?: number;
  /** 章节正文的起始字符偏移（续读基准） */
  startOffset?: number;
  /** 章节正文总长度 */
  charCount?: number;
  /** 本次消息所属书目（用于防止跨书写进度） */
  bookId?: number;
  /** 本次展示的章节号（用于无障碍播报） */
  chapterIndex?: number;
}

export type StreamEvent =
  | { type: "start" }
  | { type: "book"; id: number }
  | {
      type: "meta";
      chapter_index: number;
      start_offset: number;
      char_count: number;
    }
  | { type: "thinking"; text: string }
  | { type: "title"; text: string }
  | { type: "chunk"; text: string }
  | { type: "footer"; text: string }
  | { type: "done" };