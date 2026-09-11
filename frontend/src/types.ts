export interface Book {
  id: number;
  title: string;
  source_filename: string;
  total_chapters: number;
  created_at: string;
}

export interface ChapterMeta {
  index_no: number;
  title: string;
  char_count: number;
}

export interface Progress {
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

export interface ChatMessage {
  id: string;
  role: Role;
  text: string;
  /** 是否仍在流式生成中 */
  streaming?: boolean;
  /** 已收到「思考」但正文尚未开始 */
  thinking?: string;
}

export type StreamEvent =
  | { type: "start" }
  | { type: "thinking"; text: string }
  | { type: "title"; text: string }
  | { type: "chunk"; text: string }
  | { type: "footer"; text: string }
  | { type: "done" };