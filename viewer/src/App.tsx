import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import './App.css'

type Vector3Tuple = [number, number, number]

type Placement = {
  item_id: string
  origin: Vector3Tuple
  shape: Vector3Tuple
}

type Package = {
  bin_shape: Vector3Tuple
  placements: Placement[]
}

type SceneProps = {
  packageData: Package
  selectedItem: string | null
  onSelectItem: (itemId: string | null) => void
}

const palette = ['#d97757', '#6f9d85', '#e5ad54', '#6386ad', '#c17d9f', '#8b82bf']

function isTuple(value: unknown, allowZero = false): value is Vector3Tuple {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every(
      (part) =>
        typeof part === 'number' &&
        Number.isFinite(part) &&
        (allowZero ? part >= 0 : part > 0),
    )
  )
}

function parsePackage(value: unknown, index: number): Package {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`Package ${index + 1} must be an object.`)
  }

  const record = value as Record<string, unknown>
  if (!isTuple(record.bin_shape) || !Array.isArray(record.placements)) {
    throw new Error(`Package ${index + 1} needs a 3D bin_shape and a placements array.`)
  }
  const binShape = record.bin_shape

  const placements = record.placements.map((item, itemIndex): Placement => {
    if (typeof item !== 'object' || item === null || Array.isArray(item)) {
      throw new Error(`Package ${index + 1}, placement ${itemIndex + 1} must be an object.`)
    }
    const placement = item as Record<string, unknown>
    if (
      typeof placement.item_id !== 'string' ||
      !isTuple(placement.origin, true) ||
      !isTuple(placement.shape)
    ) {
      throw new Error(
        `Package ${index + 1}, placement ${itemIndex + 1} needs item_id, origin, and shape.`,
      )
    }
    const [x, y, z] = placement.origin
    const [width, length, height] = placement.shape
    const [binWidth, binLength, binHeight] = binShape
    if (
      x < 0 ||
      y < 0 ||
      z < 0 ||
      x + width > binWidth ||
      y + length > binLength ||
      z + height > binHeight
    ) {
      throw new Error(`Placement “${placement.item_id}” extends outside package ${index + 1}.`)
    }
    return {
      item_id: placement.item_id,
      origin: placement.origin,
      shape: placement.shape,
    }
  })

  return { bin_shape: binShape, placements }
}

function parsePackages(value: unknown): Package[] {
  const source =
    Array.isArray(value) ? value : typeof value === 'object' && value !== null && 'packages' in value
      ? (value as { packages: unknown }).packages
      : [value]
  if (!Array.isArray(source) || source.length === 0) {
    throw new Error('The file must contain at least one package.')
  }
  return source.map((packageData, index) => parsePackage(packageData, index))
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function formatVector(value: Vector3Tuple): string {
  return value.map(formatNumber).join(' × ')
}

function ItemScene({ packageData, selectedItem, onSelectItem }: SceneProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const selectRef = useRef(onSelectItem)
  const activeRef = useRef(selectedItem)

  useEffect(() => {
    selectRef.current = onSelectItem
  }, [onSelectItem])

  useEffect(() => {
    activeRef.current = selectedItem
  }, [selectedItem])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f6f5f1')
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 3000)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15
    host.appendChild(renderer.domElement)

    scene.add(new THREE.HemisphereLight(0xffffff, 0x77736b, 2.1))
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.5)
    keyLight.position.set(-1.4, 2.4, 1.8)
    scene.add(keyLight)
    const fillLight = new THREE.DirectionalLight(0xffffff, 0.8)
    fillLight.position.set(1.2, 1.2, -1.5)
    scene.add(fillLight)

    const [binWidth, binLength, binHeight] = packageData.bin_shape
    const maxDimension = Math.max(binWidth, binLength, binHeight)
    const gridSize = maxDimension * 1.5
    const floor = new THREE.GridHelper(gridSize, 20, 0xc9c7c0, 0xe3e1dc)
    floor.position.set(gridSize / 2, -0.015, gridSize / 2)
    scene.add(floor)

    const binGeometry = new THREE.BoxGeometry(binWidth, binHeight, binLength)
    const binEdges = new THREE.EdgesGeometry(binGeometry)
    const binOutline = new THREE.LineSegments(
      binEdges,
      new THREE.LineBasicMaterial({ color: '#77776f', transparent: true, opacity: 0.72 }),
    )
    binOutline.position.set(binWidth / 2, binHeight / 2, binLength / 2)
    scene.add(binOutline)

    const boxMaterials: THREE.MeshStandardMaterial[] = []
    const meshes = new Map<string, THREE.Mesh>()
    packageData.placements.forEach((placement, index) => {
      const [x, y, z] = placement.origin
      const [width, length, height] = placement.shape
      const material = new THREE.MeshStandardMaterial({
        color: palette[index % palette.length],
        roughness: 0.72,
        metalness: 0.02,
        transparent: true,
      })
      boxMaterials.push(material)
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, length), material)
      mesh.position.set(x + width / 2, z + height / 2, y + length / 2)
      mesh.userData.itemId = placement.item_id
      scene.add(mesh)
      meshes.set(placement.item_id, mesh)

      const edge = new THREE.LineSegments(
        new THREE.EdgesGeometry(mesh.geometry),
        new THREE.LineBasicMaterial({ color: '#3a3935', transparent: true, opacity: 0.42 }),
      )
      mesh.add(edge)
    })

    const target = new THREE.Vector3(binWidth / 2, binHeight / 2, binLength / 2)
    const distance = maxDimension * 2.05
    let yaw = Math.PI * 0.22
    let pitch = Math.PI * 0.29
    let zoom = 1
    let dragging = false
    let panning = false
    let movedDuringDrag = false
    let previousPointer = { x: 0, y: 0 }

    const updateCamera = (): void => {
      const horizontal = distance * zoom * Math.cos(pitch)
      camera.position.set(
        target.x + horizontal * Math.sin(yaw),
        target.y + distance * zoom * Math.sin(pitch),
        target.z + horizontal * Math.cos(yaw),
      )
      camera.lookAt(target)
    }
    updateCamera()

    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    const onPointerDown = (event: PointerEvent): void => {
      if (event.button !== 0 && event.button !== 2) return
      event.preventDefault()
      dragging = event.button === 0
      panning = event.button === 2
      movedDuringDrag = false
      previousPointer = { x: event.clientX, y: event.clientY }
      renderer.domElement.setPointerCapture(event.pointerId)
    }
    const onPointerMove = (event: PointerEvent): void => {
      if (!dragging && !panning) return
      const deltaX = event.clientX - previousPointer.x
      const deltaY = event.clientY - previousPointer.y
      if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) movedDuringDrag = true
      if (dragging) {
        yaw -= deltaX * 0.008
        pitch = Math.max(0.12, Math.min(1.35, pitch + deltaY * 0.006))
      } else {
        const bounds = renderer.domElement.getBoundingClientRect()
        const unitsPerPixel =
          (2 * distance * zoom * Math.tan((38 * Math.PI) / 360)) / bounds.height
        const rightX = Math.cos(yaw)
        const rightZ = -Math.sin(yaw)
        const upX = -Math.sin(yaw) * Math.sin(pitch)
        const upY = Math.cos(pitch)
        const upZ = -Math.cos(yaw) * Math.sin(pitch)
        target.set(
          target.x + (-rightX * deltaX + upX * deltaY) * unitsPerPixel,
          target.y + upY * deltaY * unitsPerPixel,
          target.z + (-rightZ * deltaX + upZ * deltaY) * unitsPerPixel,
        )
      }
      previousPointer = { x: event.clientX, y: event.clientY }
      updateCamera()
    }
    const onPointerUp = (event: PointerEvent): void => {
      if (!dragging && !panning) return
      dragging = false
      panning = false
      if (renderer.domElement.hasPointerCapture(event.pointerId)) {
        renderer.domElement.releasePointerCapture(event.pointerId)
      }
    }
    const onClick = (event: MouseEvent): void => {
      if (event.button !== 0) return
      if (movedDuringDrag) {
        movedDuringDrag = false
        return
      }
      const bounds = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1
      pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1
      raycaster.setFromCamera(pointer, camera)
      const hit = raycaster.intersectObjects([...meshes.values()], false)[0]
      selectRef.current(hit ? (hit.object.userData.itemId as string) : null)
    }
    const onContextMenu = (event: MouseEvent): void => event.preventDefault()
    const onWheel = (event: WheelEvent): void => {
      zoom = Math.max(0.55, Math.min(2.8, zoom * (event.deltaY > 0 ? 1.08 : 0.92)))
      updateCamera()
    }
    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    renderer.domElement.addEventListener('pointermove', onPointerMove)
    renderer.domElement.addEventListener('pointerup', onPointerUp)
    renderer.domElement.addEventListener('pointercancel', onPointerUp)
    renderer.domElement.addEventListener('click', onClick)
    renderer.domElement.addEventListener('contextmenu', onContextMenu)
    renderer.domElement.addEventListener('wheel', onWheel, { passive: true })

    const resizeObserver = new ResizeObserver(() => {
      const { width, height } = host.getBoundingClientRect()
      if (!width || !height) return
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height, false)
    })
    resizeObserver.observe(host)
    let animationFrame = 0
    const render = (): void => {
      const active = activeRef.current
      meshes.forEach((mesh, itemId) => {
        const selected = active === null || active === itemId
        const material = mesh.material as THREE.MeshStandardMaterial
        material.opacity = selected ? 1 : 0.13
        material.emissive.set(selected && active ? '#33251b' : '#000000')
        material.emissiveIntensity = selected && active ? 0.32 : 0
      })
      renderer.render(scene, camera)
      animationFrame = window.requestAnimationFrame(render)
    }
    render()

    return () => {
      window.cancelAnimationFrame(animationFrame)
      resizeObserver.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointermove', onPointerMove)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
      renderer.domElement.removeEventListener('pointercancel', onPointerUp)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('contextmenu', onContextMenu)
      renderer.domElement.removeEventListener('wheel', onWheel)
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
          object.geometry.dispose()
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach((material) => material.dispose())
        }
      })
      boxMaterials.forEach((material) => material.dispose())
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [packageData])

  return <div className="scene-host" ref={hostRef} aria-label="Interactive 3D package view" />
}

function App() {
  const [packages, setPackages] = useState<Package[]>([])
  const [activePackage, setActivePackage] = useState(0)
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState('')
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const packageData = packages[activePackage]
  const placements = packageData?.placements ?? []
  const [binWidth = 0, binLength = 0, binHeight = 0] = packageData?.bin_shape ?? []
  const totalVolume = binWidth * binLength * binHeight
  const packedVolume = placements.reduce(
    (volume, item) => volume + item.shape[0] * item.shape[1] * item.shape[2],
    0,
  )
  const utilization = totalVolume ? Math.round((packedVolume / totalVolume) * 100) : 0
  const visiblePlacements = placements.filter((placement) =>
    placement.item_id.toLowerCase().includes(query.trim().toLowerCase()),
  )
  const selectedPlacement = placements.find((placement) => placement.item_id === selectedItem)

  const readFile = async (file: File): Promise<void> => {
    try {
      const parsed = parsePackages(JSON.parse(await file.text()))
      setPackages(parsed)
      setActivePackage(0)
      setSelectedItem(null)
      setQuery('')
      setFileName(file.name)
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not read this JSON file.')
    }
  }

  const onFileInput = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.currentTarget.files?.[0]
    if (file) void readFile(file)
    event.currentTarget.value = ''
  }

  const onDrop = (event: React.DragEvent<HTMLDivElement>): void => {
    event.preventDefault()
    setIsDraggingFile(false)
    const file = event.dataTransfer.files[0]
    if (file) void readFile(file)
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Packview home">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span>packview</span>
        </a>
        <div className="topbar-right">
          {fileName && <span className="loaded-file"><span className="status-dot" />{fileName}</span>}
          <button className="upload-button" onClick={() => fileInputRef.current?.click()}>
            <span aria-hidden="true">↑</span> Open packing file
          </button>
          <input
            ref={fileInputRef}
            className="visually-hidden"
            type="file"
            accept=".json,application/json"
            onChange={onFileInput}
            aria-label="Choose packing JSON file"
          />
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">×</button>
        </div>
      )}

      <section className="summary-row" id="top">
        <div className="page-title">
          <div className="eyebrow"><span className="eyebrow-line" /> PACKING WORKSPACE</div>
          <h1>See how it all fits.</h1>
          <p>Explore your packing solution, one package at a time.</p>
        </div>
        {packages.length > 0 ? (
          <div className="package-control">
            <label htmlFor="package-select">PACKAGE</label>
            <div className="select-wrap">
              <select
                id="package-select"
                value={activePackage}
                onChange={(event) => {
                  setActivePackage(Number(event.target.value))
                  setSelectedItem(null)
                }}
              >
                {packages.map((_, index) => (
                  <option key={index} value={index}>Package {String(index + 1).padStart(2, '0')}</option>
                ))}
              </select>
              <span aria-hidden="true">⌄</span>
            </div>
          </div>
        ) : (
          <button className="upload-quiet" onClick={() => fileInputRef.current?.click()}>
            Load a packing file <span aria-hidden="true">↗</span>
          </button>
        )}
      </section>

      {packageData ? (
        <>
          <section className="stats-row" aria-label="Package statistics">
            <div className="stat-card stat-primary">
              <div className="stat-label">ITEMS IN PACKAGE <span aria-hidden="true">◫</span></div>
              <div className="stat-value">{placements.length}<small> items</small></div>
            </div>
            <div className="stat-card">
              <div className="stat-label">BIN DIMENSIONS <span aria-hidden="true">↗</span></div>
              <div className="stat-value stat-dimensions">{formatVector(packageData.bin_shape)}<small> units</small></div>
            </div>
            <div className="stat-card">
              <div className="stat-label">SPACE UTILIZED <span aria-hidden="true">◔</span></div>
              <div className="stat-value">{utilization}<small>%</small></div>
              <div className="utilization-track"><span style={{ width: `${Math.min(utilization, 100)}%` }} /></div>
            </div>
            <div className="stat-card">
              <div className="stat-label">REMAINING SPACE <span aria-hidden="true">□</span></div>
              <div className="stat-value">{formatNumber(totalVolume - packedVolume)}<small> units³</small></div>
            </div>
          </section>

          <section className="content-grid">
            <div className="viewer-panel">
              <div className="panel-heading">
                <div>
                  <div className="panel-kicker">SPATIAL VIEW</div>
                  <h2>Package overview <span className="count-pill">{String(activePackage + 1).padStart(2, '0')}</span></h2>
                </div>
                <div className="view-legend"><span /> Packed item</div>
              </div>
              <div className="scene-frame">
                <ItemScene
                  key={`${activePackage}-${packages.length}`}
                  packageData={packageData}
                  selectedItem={selectedItem}
                  onSelectItem={setSelectedItem}
                />
                <div className="axis-corner" aria-label="Coordinate axes"><span className="axis-x">X</span><span className="axis-y">Y</span><span className="axis-z">Z</span></div>
                <div className="scene-hint"><span aria-hidden="true">⟳</span> Drag to orbit <b>·</b> Right-drag to move <b>·</b> Scroll to zoom</div>
              </div>
              <div className="scene-footer">
                <span><i className="footer-dot" /> Bin boundary</span>
                <span>{placements.length} placements</span>
              </div>
            </div>

            <aside className="items-panel">
              <div className="items-heading">
                <div className="panel-kicker">CONTENTS</div>
                <h2>Items <span className="count-pill">{placements.length}</span></h2>
                <div className="search-box">
                  <span aria-hidden="true">⌕</span>
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Find an item..."
                    aria-label="Find an item"
                  />
                  <kbd>⌘ K</kbd>
                </div>
              </div>
              <div className="item-list" role="list" aria-label="Package items">
                {visiblePlacements.length > 0 ? visiblePlacements.map((placement) => {
                  const itemSelected = selectedItem === placement.item_id
                  const isMuted = selectedItem !== null && !itemSelected
                  const index = placements.indexOf(placement)
                  return (
                    <button
                      className={`item-row${itemSelected ? ' is-selected' : ''}${isMuted ? ' is-muted' : ''}`}
                      key={placement.item_id}
                      onClick={() => setSelectedItem(itemSelected ? null : placement.item_id)}
                      aria-pressed={itemSelected}
                      role="listitem"
                    >
                      <span className="item-swatch" style={{ '--swatch': palette[index % palette.length] } as React.CSSProperties} />
                      <span className="item-copy"><strong>{placement.item_id}</strong><small>{formatVector(placement.shape)} <span>units</span></small></span>
                      <span className="item-arrow" aria-hidden="true">↗</span>
                    </button>
                  )
                }) : <div className="empty-filter">No items match “{query}”.</div>}
              </div>
              <div className="selection-footer">
                {selectedPlacement ? (
                  <>
                    <div className="selection-topline"><span className="selection-indicator" /> SELECTED ITEM <button onClick={() => setSelectedItem(null)}>Clear</button></div>
                    <strong>{selectedPlacement.item_id}</strong>
                    <span>Origin&nbsp; {formatVector(selectedPlacement.origin)}</span>
                  </>
                ) : (
                  <><span className="selection-indicator idle" /> Select an item to inspect its placement</>
                )}
              </div>
            </aside>
          </section>
          <footer className="page-footer"><span>PACKVIEW <i>·</i> SOLUTION EXPLORER</span><span>Dimensions shown in solver units</span></footer>
        </>
      ) : (
        <section
          className={`empty-workspace${isDraggingFile ? ' is-dragging' : ''}`}
          onDragOver={(event) => { event.preventDefault(); setIsDraggingFile(true) }}
          onDragLeave={() => setIsDraggingFile(false)}
          onDrop={onDrop}
        >
          <div className="empty-art" aria-hidden="true"><span className="cube cube-back" /><span className="cube cube-left" /><span className="cube cube-front" /><span className="cube cube-top" /></div>
          <div className="eyebrow"><span className="eyebrow-line" /> YOUR WORKSPACE IS READY</div>
          <h2>Bring your solution into view.</h2>
          <p>Open the JSON file generated by your packer to explore packages, dimensions, and every placement in 3D.</p>
          <button className="upload-button empty-upload" onClick={() => fileInputRef.current?.click()}><span aria-hidden="true">↑</span> Choose a JSON file</button>
          <span className="drop-hint">or drop a file anywhere in this space</span>
          <div className="format-note"><span className="format-icon">{ }</span><span><strong>Works with your packing output</strong><small>bin_shape · placements · item_id · origin · shape</small></span></div>
        </section>
      )}
    </main>
  )
}

export default App
