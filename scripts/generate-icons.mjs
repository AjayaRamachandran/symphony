import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import png2icons from "png2icons";

const PROJECT_ROOT = process.cwd();
const SOURCE_PNG = path.join(PROJECT_ROOT, "src", "assets", "icon-dark-512.png");
const BUILD_DIR = path.join(PROJECT_ROOT, "build");
const ICO_OUTPUT = path.join(BUILD_DIR, "icon.ico");
const ICNS_OUTPUT = path.join(BUILD_DIR, "icon.icns");

const BASE_SIZE = 1024;
const MAC_ZOOM_OUT_PERCENT = 20;
const PNG2ICONS_SCALING_ALGORITHM = png2icons.BICUBIC2;

function ensureBuffer(result, outputName) {
  if (!result || result instanceof Error || result.length === 0) {
    throw new Error(`Failed to generate ${outputName}.`);
  }

  return Buffer.from(result);
}

async function renderPngFromSource({ size, scalePercent }) {
  const scaledSize = Math.min(size, Math.round(size * (scalePercent / 100)));
  const extraPadding = size - scaledSize;
  const paddingTop = Math.floor(extraPadding / 2);
  const paddingBottom = extraPadding - paddingTop;
  const paddingLeft = Math.floor(extraPadding / 2);
  const paddingRight = extraPadding - paddingLeft;

  const scaledPng = await sharp(SOURCE_PNG)
    .resize(scaledSize, scaledSize, {
      fit: "contain",
      kernel: sharp.kernel.lanczos3
    })
    .png()
    .toBuffer();

  return sharp(scaledPng)
    .extend({
      top: paddingTop,
      bottom: paddingBottom,
      left: paddingLeft,
      right: paddingRight,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .png()
    .toBuffer();
}

async function main() {
  await mkdir(BUILD_DIR, { recursive: true });

  const windowsPng = await renderPngFromSource({ size: BASE_SIZE, scalePercent: 100 });
  const macPng = await renderPngFromSource({
    size: BASE_SIZE,
    scalePercent: 100 - MAC_ZOOM_OUT_PERCENT
  });

  const icoBuffer = ensureBuffer(
    png2icons.createICO(windowsPng, PNG2ICONS_SCALING_ALGORITHM, 0, false),
    "build/icon.ico"
  );
  const icnsBuffer = ensureBuffer(
    png2icons.createICNS(macPng, PNG2ICONS_SCALING_ALGORITHM, 0),
    "build/icon.icns"
  );

  await writeFile(ICO_OUTPUT, icoBuffer);
  await writeFile(ICNS_OUTPUT, icnsBuffer);

  console.log(`Generated ${path.relative(PROJECT_ROOT, ICO_OUTPUT)} (full bounds).`);
  console.log(
    `Generated ${path.relative(PROJECT_ROOT, ICNS_OUTPUT)} (${MAC_ZOOM_OUT_PERCENT}% zoom-out).`
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
