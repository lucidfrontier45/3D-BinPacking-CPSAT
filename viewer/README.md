# 3D Bin Packing Viewer

A web viewer for exploring 3D bin packing solutions. Open a packing JSON file to inspect packages and placements in an interactive 3D scene.

## Run locally

```sh
bun install
bun run dev
```

Open the local URL printed by Vite. Use **Open packing file** or drop a JSON file into the page.

## Packing file format

The file can contain one package, an array of packages, or an object with a `packages` array. Each package has a positive `bin_shape` and a `placements` array:

```json
{
  "bin_shape": [10, 8, 6],
  "placements": [
    { "item_id": "item-1", "origin": [0, 0, 0], "shape": [2, 3, 1] }
  ]
}
```

Each vector is `[width, length, height]`. Placement origins start at `[0, 0, 0]` and items must fit inside the bin.

## Controls

- Drag to orbit the scene
- Right-drag to move the view
- Scroll to zoom
