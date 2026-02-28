import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import png2icons from "png2icons";

const PROJECT_ROOT = process.cwd();
const SOURCE_SVG = path.join(PROJECT_ROOT, "src", "assets", "icon-dark.svg");
const BUILD_DIR = path.join(PROJECT_ROOT, "build");
const ICO_OUTPUT = path.join(BUILD_DIR, "icon.ico");
const ICNS_OUTPUT = path.join(BUILD_DIR, "icon.icns");

const BASE_SIZE = 1024;
const MAC_ZOOM_OUT_PERCENT = 20;

function ensureBuffer(result, outputName) {
  if (!result || result instanceof Error || result.length === 0) {
    throw new Error(`Failed to generate ${outputName}.`);
  }

  return Buffer.from(result);
}

async function renderPngFromSvg({ size, scalePercent }) {
  const scaledSize = Math.round(size * (scalePercent / 100));
  const margin = Math.floor((size - scaledSize) / 2);

  const scaledSvgPng = await sharp(SOURCE_SVG)
    .resize(scaledSize, scaledSize, { fit: "contain" })
    .png()
    .toBuffer();

  return sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    }
  })
    .composite([{ input: scaledSvgPng, left: margin, top: margin }])
    .png()
    .toBuffer();
}

async function main() {
  await mkdir(BUILD_DIR, { recursive: true });

  const windowsPng = await renderPngFromSvg({ size: BASE_SIZE, scalePercent: 100 });
  const macPng = await renderPngFromSvg({
    size: BASE_SIZE,
    scalePercent: 100 - MAC_ZOOM_OUT_PERCENT
  });

  const icoBuffer = ensureBuffer(
    png2icons.createICO(windowsPng, png2icons.BILINEAR, 0, false),
    "build/icon.ico"
  );
  const icnsBuffer = ensureBuffer(
    png2icons.createICNS(macPng, png2icons.BILINEAR, 0),
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
