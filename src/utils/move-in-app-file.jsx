// Helpers for moving a Symphony-managed file by absolute path, used by the
// drop handlers when the drag originated inside the app. The browser drag in
// pywebview/WebView2 exposes no real File object, so we cannot rely on
// dataTransfer.files; instead we trust the source path captured at dragstart.

const VALID_EXTS = [".symphony", ".wav", ".mid", ".mp3", ".flac", ".musicxml"];

const normalizeForwardSlashes = (value) =>
  typeof value === "string" ? value.replace(/\\/g, "/") : "";

export const getFileName = (filePath) => {
  const normalized = normalizeForwardSlashes(filePath);
  const idx = normalized.lastIndexOf("/");
  return idx >= 0 ? normalized.slice(idx + 1) : normalized;
};

export const isSupportedDropExtension = (fileName) => {
  const lower = (fileName || "").toLowerCase();
  return VALID_EXTS.some((ext) => lower.endsWith(ext));
};

/**
 * Moves a file already on disk into ``destinationDir`` using path-based
 * operations exposed by the desktop bridge. Returns ``{ status, destPath }``
 * where ``status`` is one of ``"moved"``, ``"same-location"``, ``"invalid"``,
 * or ``"error"``.
 */
export const moveInAppFileToDirectory = async (
  sourceFilePath,
  destinationDir,
) => {
  const api = typeof window !== "undefined" ? window.electronAPI : null;
  if (!api || !sourceFilePath || !destinationDir) {
    return { status: "error", error: "missing-arguments" };
  }

  const src = normalizeForwardSlashes(sourceFilePath);
  const destDir = normalizeForwardSlashes(destinationDir).replace(/\/$/, "");
  const fileName = getFileName(src);

  if (!isSupportedDropExtension(fileName)) {
    return { status: "invalid", fileName };
  }

  const destPath = `${destDir}/${fileName}`;
  if (destPath.toLowerCase() === src.toLowerCase()) {
    return { status: "same-location", destPath };
  }

  try {
    if (await api.fileExists(destPath)) {
      return { status: "exists", destPath };
    }

    await api.copyFile(src, destPath);
    const deleteResult = await api.deleteFile(src);
    if (deleteResult && deleteResult.success === false) {
      return {
        status: "error",
        error: deleteResult.error || "delete-failed",
        destPath,
      };
    }
    return { status: "moved", destPath };
  } catch (err) {
    console.error("moveInAppFileToDirectory failed:", err);
    return { status: "error", error: err?.message || String(err) };
  }
};
