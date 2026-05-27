import { Eraser, MousePointer2, Pencil, Piano, Speech } from "lucide-react";
import flatIcon from "@/assets/editor-icons/flat.svg?raw";
import sharpIcon from "@/assets/editor-icons/sharp.svg?raw";
import squareWaveIcon from "@/assets/editor-icons/square-wave.svg?raw";
import triangleWaveIcon from "@/assets/editor-icons/triangle-wave.svg?raw";
import sawtoothWaveIcon from "@/assets/editor-icons/sawtooth-wave.svg?raw";
import { SvgAssetIcon } from "./ui-elements.jsx";

export const HELP_URL = "https://docs.nimbial.com/symphony/4";

export const CHANNELS = [
  { name: "orange", label: "Orange", color: "#eb904a" },
  { name: "purple", label: "Purple", color: "#b87de3" },
  { name: "cyan", label: "Cyan", color: "#6ccfc6" },
  { name: "lime", label: "Lime", color: "#9ade8a" },
  { name: "blue", label: "Blue", color: "#6a7ad6" },
  { name: "pink", label: "Pink", color: "#d66a9b" },
  {
    name: "all",
    label: "All",
    color:
      "linear-gradient(135deg, hsl(0 80% 50%),hsl(50 80% 50%),hsl(90 80% 50%),hsl(210 80% 50%),hsl(300 80% 50%))",
  },
];

export const BRUSHES = [
  { id: "pencil", label: "Pencil", color: "#c79a3b", Icon: Pencil },
  { id: "eraser", label: "Eraser", color: "#e4678a", Icon: Eraser },
  { id: "select", label: "Select", color: "#5d8cff", Icon: MousePointer2 },
];

export const DRAW_BRUSH_INDEX = BRUSHES.findIndex((brush) => brush.id === "pencil");
export const ERASER_BRUSH_INDEX = BRUSHES.findIndex((brush) => brush.id === "eraser");
export const SELECT_BRUSH_INDEX = BRUSHES.findIndex((brush) => brush.id === "select");

export const KEY_OPTIONS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"].map((key) => ({
  label: key,
  value: key,
}));

export const MODE_OPTIONS = [
  "Lydian",
  "Ionian (maj.)",
  "Mixolydian",
  "Dorian",
  "Aeolian (min.)",
  "Phrygian",
  "Locrian",
].map((mode) => ({ label: mode, value: mode }));

export { flatIcon, sharpIcon };

export const INSTRUMENT_OPTIONS = [
  {
    label: "Square",
    value: 0,
    node: (
      <>
        <SvgAssetIcon source={squareWaveIcon} />
        <span>Square</span>
      </>
    ),
    selectedNode: (
      <>
        <SvgAssetIcon source={squareWaveIcon} />
        <span>Square</span>
      </>
    ),
  },
  {
    label: "Triangle",
    value: 1,
    node: (
      <>
        <SvgAssetIcon source={triangleWaveIcon} />
        <span>Triangle</span>
      </>
    ),
    selectedNode: (
      <>
        <SvgAssetIcon source={triangleWaveIcon} />
        <span>Triangle</span>
      </>
    ),
  },
  {
    label: "Sawtooth",
    value: 2,
    node: (
      <>
        <SvgAssetIcon source={sawtoothWaveIcon} />
        <span>Sawtooth</span>
      </>
    ),
    selectedNode: (
      <>
        <SvgAssetIcon source={sawtoothWaveIcon} />
        <span>Sawtooth</span>
      </>
    ),
  },
  {
    label: "Piano",
    value: 3,
    icon: Piano,
    selectedNode: (
      <>
        <Piano size={16} />
        <span>Piano</span>
      </>
    ),
  },
  {
    label: "Voice",
    value: 4,
    icon: Speech,
    selectedNode: (
      <>
        <Speech size={16} />
        <span>Voice</span>
      </>
    ),
  },
];
