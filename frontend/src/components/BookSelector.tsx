import { useRef } from "react";
import type { Book } from "../types";

interface Props {
  books: Book[];
  currentId: number | null;
  onSelect: (id: number) => void;
  onImport: (file: File) => void;
  onDelete: (id: number) => void;
  busy?: boolean;
}

export function BookSelector({
  books,
  currentId,
  onSelect,
  onImport,
  onDelete,
  busy,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div className="book-selector">
      <select
        value={currentId ?? ""}
        onChange={(e) => {
          const v = e.target.value;
          if (v) onSelect(Number(v));
        }}
      >
        <option value="">— 选择一本书 —</option>
        {books.map((b) => (
          <option key={b.id} value={b.id}>
            {b.title}（{b.total_chapters} 章）
          </option>
        ))}
      </select>
      <input
        ref={fileRef}
        type="file"
        accept=".txt,text/plain"
        style={{ display: "none" }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onImport(file);
          e.target.value = "";
        }}
      />
      <button className="btn ghost" disabled={busy} onClick={() => fileRef.current?.click()}>
        导入 TXT
      </button>
      {currentId != null && (
        <button
          className="btn ghost danger"
          onClick={() => {
            if (confirm("确定删除这本书吗？")) onDelete(currentId);
          }}
        >
          删除
        </button>
      )}
    </div>
  );
}