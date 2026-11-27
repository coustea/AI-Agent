import { describe, expect, it } from "vitest";

import {
  classifyFile,
  codeFenceLangOf,
  fileFormatLabel,
  formatBytes,
  previewModeOf,
  validateAttachmentFile,
} from "@/lib/files";

describe("file helpers and attachment validation", () => {
  it("validates supported extensions and size cap", () => {
    const okPdf = new File(["hello"], "notes.pdf", { type: "application/pdf" });
    expect(validateAttachmentFile(okPdf)).toBeNull();

    const badImg = new File(["img"], "photo.png", { type: "image/png" });
    expect(validateAttachmentFile(badImg)).toContain(".pdf");

    const huge = new File([new Uint8Array(6 * 1024 * 1024)], "big.md");
    expect(validateAttachmentFile(huge)).toContain("5 MB");
  });

  it("classifies files, preview modes, and code fence languages from one registry", () => {
    expect(classifyFile("deck.pptx")).toBe("slides");
    expect(classifyFile("flow.excalidraw")).toBe("diagram");
    expect(classifyFile("lesson.mp4")).toBe("video");
    expect(previewModeOf("lesson.mp4")).toBe("video");
    expect(previewModeOf("summary.md")).toBe("markdown");
    expect(previewModeOf("App.tsx")).toBe("text");
    expect(previewModeOf("deck.pptx")).toBe("none");
    expect(codeFenceLangOf("App.tsx")).toBe("tsx");
    expect(codeFenceLangOf("flow.excalidraw")).toBe("json");
    expect(codeFenceLangOf("readme.txt")).toBeUndefined();
    expect(formatBytes(2048)).toBe("2.0 KB");
  });

  it("formats distinct labels for different file types", () => {
    expect(fileFormatLabel("notes.pdf")).toBe("PDF");
    expect(fileFormatLabel("report.docx")).toBe("DOCX");
    expect(fileFormatLabel("guide.md")).toBe("Markdown");
    expect(fileFormatLabel("deck.pptx")).toBe("PPTX");
    expect(fileFormatLabel("benchmark.xlsx")).toBe("XLSX");
    expect(fileFormatLabel("demo.mp4")).toBe("MP4");
    expect(fileFormatLabel("arch.excalidraw")).toBe("Excalidraw");
    expect(fileFormatLabel("diagram.png")).toBe("PNG");
    expect(fileFormatLabel("main.go")).toBe("GO");
    expect(fileFormatLabel("readme.txt")).toBe("TXT");
  });
});
