// Shared helpers for opening a .symphony file in the editor.

export const NEWER_VERSION_EVENT = "symphony:newer-version-file";

// True when the editor refused to open a file because it was saved by a
// newer version of Symphony.
export const isNewerVersionError = (result) =>
  result?.status === "error" && result?.message === "NewerVersionError";

// Opens a file from inside the Project Manager. If the file is from a newer
// version, the in-app notice (NewerVersionNotice) is shown instead.
export const openInEditor = async (filePath) => {
  const result = await window.electronAPI.doProcessCommand(filePath, "open", {});
  if (isNewerVersionError(result)) {
    window.dispatchEvent(new CustomEvent(NEWER_VERSION_EVENT));
  }
  return result;
};
