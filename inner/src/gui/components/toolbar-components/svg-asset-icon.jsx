/**
 * Renders a trusted raw svg asset at toolbar icon size.
 */
export function SvgAssetIcon({ source, size = 16 }) {
  return (
    <span
      className="editor-svg-icon"
      style={{ width: size, height: size }}
      dangerouslySetInnerHTML={{ __html: source }}
    />
  );
}
