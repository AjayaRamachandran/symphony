const getPlatform = () => {
  if (typeof window !== "undefined" && window.electronAPI?.platform) {
    return window.electronAPI.platform;
  }

  if (typeof navigator !== "undefined" && navigator.platform) {
    return navigator.platform;
  }

  return "";
};

export const normalizePath = (inputPath) => {
  if (typeof inputPath !== "string") {
    return "";
  }

  const platform = String(getPlatform()).toLowerCase();

  // path-browserify parses POSIX separators, so normalize Windows paths.
  if (platform.startsWith("win")) {
    return inputPath.replace(/\\/g, "/");
  }

  return inputPath;
};
